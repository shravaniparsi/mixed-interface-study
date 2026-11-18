import test from 'node:test';
import assert from 'node:assert/strict';
import {crawlEditBody, sameState} from '../scripts/extension/maxun_serializer_v1.mjs';
const fixture = () => ({id:'row-1', userId:1,
  recording_meta:{id:'meta-1',type:'crawl',name:'ordinary',url:'http://localhost:8765/',formats:['markdown'],createdAt:'fixed'},
  recording:{workflow:[
    {where:{url:'http://localhost:8765/'},what:[{action:'flag',args:['generated']},{action:'crawl',args:[{mode:'domain',limit:50}],name:'Crawl'}]},
    {where:{url:'about:blank'},what:[{action:'goto',args:['http://localhost:8765/']},{action:'waitForLoadState',args:['networkidle']}]}
  ]}});
test('URL edit preserves full workflow and source object',()=>{
 const before=fixture(), retained=structuredClone(before);
 const body=crawlEditBody(before,'url',' http://localhost:8765/edited ');
 assert.equal(body.targetUrl,'http://localhost:8765/edited');
 assert.deepEqual(body.workflow,before.recording.workflow);
 assert.deepEqual(body,{name:'ordinary',limits:[],credentials:{},targetUrl:'http://localhost:8765/edited',workflow:before.recording.workflow,formats:['markdown']});
 assert.deepEqual(before,retained);
});
test('missing and null unrelated name are not repaired',()=>{
 const missing=fixture();delete missing.recording_meta.name;
 assert.equal(Object.hasOwn(crawlEditBody(missing,'url','http://localhost:8765/edit'),'name'),false);
 missing.recording_meta.name=null;
 assert.equal(crawlEditBody(missing,'url','http://localhost:8765/edit').name,null);
});
test('name edit uses native URL fallback',()=>{
 const source=fixture();source.recording_meta.url=null;
 assert.equal(crawlEditBody(source,'name','changed').targetUrl,'http://localhost:8765/');
});
test('unsupported action cannot silently lose credentials',()=>{
 const source=fixture();source.recording.workflow[0].what.push({action:'type',args:['input','secret']});
 assert.throws(()=>crawlEditBody(source,'name','changed'),/Unqualified action/);
});
test('exact state comparison retains timestamps identities and array ordering',()=>{
 const source=fixture(), other=structuredClone(source);
 assert.equal(sameState(source,other),true);
 other.recording_meta.createdAt='changed';assert.equal(sameState(source,other),false);
 other.recording_meta.createdAt='fixed';other.id='different';assert.equal(sameState(source,other),false);
 other.id='row-1';other.recording.workflow.reverse();assert.equal(sameState(source,other),false);
 assert.equal(sameState({a:1,b:2},{b:2,a:1}),true);
 assert.equal(sameState({a:null},{}),false);
});
