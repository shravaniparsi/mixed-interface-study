import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { reconstructSeatsurfingLoader } from '../scripts/extension/reconstruct_seatsurfing_loader_v1.mjs';
const id='00000000-0000-4000-8000-000000000001';
const sha=x=>createHash('sha256').update(x).digest('hex');
function fixture({groupsPermission=30,settings=[{name:'feature_groups',value:'1'}]}={}) {
  const origin='http://127.0.0.1:8080',events=[];
  const values=[['/user/me',{permissions:{groups:groupsPermission}}],['/setting/',settings],['/location/'+id,{id,name:'fixture',mapType:''}],
    ...(groupsPermission>=10?[['/group/',[{id:'00000000-0000-4000-8000-000000000002'}]]]:[]),
    ['/location/'+id+'/space/',[{id:'00000000-0000-4000-8000-000000000003'}]],['/location/'+id+'/map',{data:'',width:0,height:0}],['/space-attribute/',[]],['/location/'+id+'/attribute',[]],['/setting/timezones',['UTC']]];
  values.forEach(([path,value],i)=>{const requestId=i+1,body=JSON.stringify(value);events.push({kind:'request',id:requestId,method:'GET',url:origin+path},{kind:'request_headers',id:requestId,headers:{authorization:'Bearer synthetic'}},{kind:'response',id:requestId,status:200,bodyCaptured:true,body,bodySha256:sha(body)},{kind:'finished',id:requestId});});
  return {events,afterRequestId:0,id,accessToken:'synthetic',origin};
}
test('complete native loader supplies source-derived inputs and retains original responses',()=>{
  const result=reconstructSeatsurfingLoader(fixture());assert.equal(result.materialization.featureGroups,true);assert.deepEqual(result.materialization.spaces[0].attributes,[]);assert.equal(result.consumed.length,9);assert.equal(result.runtimeQualified,false);
});
test('original denied group-read branch supplies empty groups',()=>{
  const result=reconstructSeatsurfingLoader(fixture({groupsPermission:0}));assert.deepEqual(result.materialization.groups,[]);assert.equal(result.consumed.length,8);
});
test('original settings order and default are preserved',()=>{
  assert.equal(reconstructSeatsurfingLoader(fixture({settings:[]})).materialization.featureGroups,false);
  assert.equal(reconstructSeatsurfingLoader(fixture({settings:[{name:'feature_groups',value:'1'},{name:'feature_groups',value:'0'}]})).materialization.featureGroups,false);
});
test('a request before editor loading cannot substitute for fresh evidence',()=>{
  const x=fixture();x.afterRequestId=1;assert.throws(()=>reconstructSeatsurfingLoader(x),/Missing or ambiguous/);
});
test('missing settings body prevents reconstruction',()=>{
  const x=fixture();x.events=x.events.filter(e=>!(e.id===2&&e.kind==='response'));assert.throws(()=>reconstructSeatsurfingLoader(x));
});
test('different bearer or altered response cannot supply loader inputs',()=>{
  const x=fixture();x.events[1].headers.authorization='Bearer another';assert.throws(()=>reconstructSeatsurfingLoader(x));
  const y=fixture();y.events.find(e=>e.kind==='response').body+=' ';assert.throws(()=>reconstructSeatsurfingLoader(y));
});
test('duplicate loader requests remain ambiguous',()=>{
  const x=fixture();x.events.push({kind:'request',id:99,method:'GET',url:x.origin+'/group/'});assert.throws(()=>reconstructSeatsurfingLoader(x),/ambiguous/);
});
