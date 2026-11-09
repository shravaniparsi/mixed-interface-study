import test from 'node:test';
import assert from 'node:assert/strict';
import {profileIdentityExpected,authorPath,projectIdentitySnapshot,identitySnapshot} from '../scripts/realworld_identity_v1.mjs';

const before={username:'pilotresearch',email:'pilot@example.test',bio:null,image:null};
const renamed={...before,username:'u'.repeat(61)};
const fixtures=['first','second'];
function evidence(user=renamed){
  return [{path:'/api/user',status:200,data:{user:{...user,token:'excluded'}}},
    {path:authorPath(user.username),status:200,data:{articlesCount:2,articles:fixtures.map(slug=>({slug,title:slug,description:'description',body:'body',tagList:['x'],author:{username:user.username}}))}},
    {path:'/api/tags',status:200,data:{tags:['x']}},
    ...fixtures.map(slug=>({path:`/api/articles/${slug}/comments`,status:200,data:{comments:[]}}))];
}
test('accepted username representation preserves length and whitespace without setting acceptance policy',()=>{
  for(const username of ['u'.repeat(60),'u'.repeat(61),'  renamed  ','a/b?x&y'])assert.deepEqual(profileIdentityExpected(before,{username}),{...before,username});
});
test('optional fields retain existing representation rules',()=>{
  assert.deepEqual(profileIdentityExpected({...before,bio:'old'},{username:'new',bio:''}),{...before,username:'new'});
  assert.deepEqual(profileIdentityExpected(before,{}),before);
});
test('null and empty accepted usernames remain explicitly outside this contract',()=>{
  for(const username of [null,'',123,{},[]])assert.throws(()=>profileIdentityExpected(before,{username}));
});
test('email changes, credential writes, and incomplete baseline cannot inherit username scope',()=>{
  for(const patch of [{email:'other@example.test'},{password:'secret'},{bio:7},[]])assert.throws(()=>profileIdentityExpected(before,patch));
  assert.throws(()=>profileIdentityExpected({username:'old',email:before.email},{}));
});
test('rename snapshot retains every fixture article and omits authentication token',()=>{
  const state=projectIdentitySnapshot(evidence(),renamed,fixtures);
  assert.deepEqual(state.user,renamed);assert.equal(state.articles.length,2);assert.equal(Object.hasOwn(state.user,'token'),false);
});
test('stale username query cannot substitute for renamed author query',()=>{
  const reads=evidence();reads[1].path=authorPath(before.username);
  assert.throws(()=>projectIdentitySnapshot(reads,renamed,fixtures));
});
test('observed principal cannot silently replace the expected principal',()=>{
  for(const change of [{username:'intruder'},{email:'intruder@example.test'}]){
    const reads=evidence();Object.assign(reads[0].data.user,change);
    assert.throws(()=>projectIdentitySnapshot(reads,renamed,fixtures));
  }
});
test('empty, partial, duplicate, and foreign article collections fail closed',()=>{
  for(const mutate of [x=>{x.articles=[];x.articlesCount=0;},x=>{x.articles.pop();},x=>{x.articles[1]=x.articles[0];},x=>{x.articles[1].slug='foreign';}]){
    const reads=evidence();mutate(reads[1].data);assert.throws(()=>projectIdentitySnapshot(reads,renamed,fixtures));
  }
});
test('stale nested article author remains visible as an invalid identity snapshot',()=>{
  const reads=evidence();reads[1].data.articles[0].author.username=before.username;
  assert.throws(()=>projectIdentitySnapshot(reads,renamed,fixtures));
});
test('unreadable, duplicate, and extra probes cannot form a complete snapshot',()=>{
  for(const mutate of [x=>{x[3].status=500;},x=>x.push(x[3]),x=>x.push({path:'/api/extra',status:200,data:{}})]){
    const reads=evidence();mutate(reads);assert.throws(()=>projectIdentitySnapshot(reads,renamed,fixtures));
  }
});
test('malformed comment collections and article fields are rejected',()=>{
  for(const mutate of [x=>{x[3].data.comments=[{id:1,body:'x',author:{username:'other'}},{id:1,body:'y',author:{username:'other'}}];},x=>{delete x[1].data.articles[0].body;}]){
    const reads=evidence();mutate(reads);assert.throws(()=>projectIdentitySnapshot(reads,renamed,fixtures));
  }
});
test('collection ordering does not change projected identity state',()=>{
  const a=evidence(),b=evidence();b.reverse();b.find(r=>r.path===authorPath(renamed.username)).data.articles.reverse();
  assert.deepEqual(projectIdentitySnapshot(a,renamed,fixtures),projectIdentitySnapshot(b,renamed,[...fixtures].reverse()));
});
test('network snapshot uses encoded author binding and independently pinned article references',async()=>{
  const user={...renamed,username:'a/b?x&y'},reads=evidence(user),seen=[];
  const result=await identitySnapshot(async(method,path)=>{seen.push([method,path]);return reads.find(r=>r.path===path);},user,fixtures);
  assert.equal(result.readable,true);assert.equal(seen[1][1],'/api/articles?author=a%2Fb%3Fx%26y');assert.equal(seen.length,5);
});
test('zero author results retain reference probes and stay unreadable',async()=>{
  const reads=evidence();reads[1].data={articles:[],articlesCount:0};const seen=[];
  const result=await identitySnapshot(async(method,path)=>{seen.push(path);return reads.find(r=>r.path===path);},renamed,fixtures);
  assert.equal(result.readable,false);assert.equal(result.reads.length,5);assert.ok(seen.includes('/api/articles/second/comments'));
});
test('transport failures preserve attempted successful probes and do not report complete state',async()=>{
  const reads=evidence();let count=0;
  const result=await identitySnapshot(async()=>{if(count===2)throw new Error('offline');return reads[count++];},renamed,fixtures);
  assert.equal(result.readable,false);assert.equal(result.reads.length,2);assert.equal(result.error,'offline');
});
test('invalid fixture bindings fail before requests',async()=>{
  for(const refs of [[],['first','first'],[null]])await assert.rejects(identitySnapshot(()=>{throw new Error('must not request');},renamed,refs),/fixture/);
});
