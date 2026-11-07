import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {registryFromBytes,selectCases,bindConsumer,expectedProducer,expectedForm,decodeNativeEntries,allowedRequest,JOB_PATH} from '../scripts/quartz_generated_case.mjs';
import {stopOwned,childExitedCleanly} from '../scripts/run_quartz_registry.mjs';

const stored={jobKeyDTO:{group:'RESEARCH',name:'pilot-job'},jobClassName:'actual.ReturnedClass',description:null,durable:true,requestsRecovery:true,
  jobDataMap:{' padded ':{nested:[7,true,null]},'':'blank key',key:'first',' key ':'second'},triggerKeys:[]};

test('consumer binds returned class, recovery flag, map and identity without baseline repair',()=>{
  const bound=bindConsumer(stored,'requested edit');assert.equal(bound.path,JOB_PATH);
  assert.deepEqual(bound.command,{jobClass:'actual.ReturnedClass',description:'requested edit',durable:true,requestsRecovery:true,jobDataMap:stored.jobDataMap});
  bound.command.jobDataMap[' padded '].nested[0]=99;assert.equal(stored.jobDataMap[' padded '].nested[0],7,'binding must be detached');
});
test('unexpected producer identity is rejected rather than guessed or sent to another resource',()=>{
  for(const key of [{group:'OTHER',name:'pilot-job'},{group:'RESEARCH',name:'different'},{group:'RESEARCH',name:'../pilot-job'}])assert.throws(()=>bindConsumer({...stored,jobKeyDTO:key},'edit'),/identity differs/);
  assert.throws(()=>bindConsumer({...stored,jobDataMap:null},'edit'),/map is not an object/);
});
test('source-declared defaults and native display projection do not trim data-map keys',()=>{
  const input={jobClass:'eligible.Class',durable:true,requestsRecovery:false};
  const expected=expectedProducer(input);assert.equal(expected.description,null);assert.deepEqual(expected.jobDataMap,{});
  assert.equal(expectedForm(stored).description,'');assert.deepEqual(expectedForm(stored).jobDataMap,stored.jobDataMap);
  const literal={...input,description:'Café 東京 🌱',jobDataMap:{'   ':null,' key ':7}};
  assert.equal(expectedProducer(literal).description,literal.description);assert.deepEqual(expectedProducer(literal).jobDataMap,literal.jobDataMap);
});
test('native typed-entry reading preserves raw keys and scalar/nested values',()=>{
  const actual=decodeNativeEntries([{key:' padded ',type:'string',value:'text'},{key:'',type:'null',value:''},{key:'key',type:'number',value:'7'},
    {key:' key ',type:'boolean',value:'true'},{key:'nested',type:'json',value:'{"child":[1,true,null,{"leaf":"text"}]}'}]);
  assert.deepEqual(actual,{' padded ':'text','':null,key:7,' key ':true,nested:{child:[1,true,null,{leaf:'text'}]}});
  assert.throws(()=>decodeNativeEntries([{key:'a',type:'string',value:'one'},{key:'a',type:'string',value:'two'}]),/Duplicate raw UI key/);
  assert.throws(()=>decodeNativeEntries([{key:'a',type:'boolean',value:'TRUE'}]));
});
test('write allowlist excludes scheduler starts, triggers and unrelated resource writes',()=>{
  assert.ok(allowedRequest('POST',JOB_PATH));assert.ok(allowedRequest('PUT',JOB_PATH));assert.ok(allowedRequest('POST','/quartz-manager/auth/login'));
  for(const [method,path] of [['POST',JOB_PATH+'/trigger'],['POST','/quartz-manager/scheduler/start'],['POST','/quartz-manager/scheduler/resume'],['POST','/quartz-manager/triggers/g/n'],['DELETE',JOB_PATH],['PUT','/quartz-manager/jobs/OTHER/job']])assert.equal(allowedRequest(method,path),false);
});
test('pinned corpus defaults to only four controls; all is explicit',async()=>{
  const bytes=await readFile(new URL('../manifests/quartz-job-generated-pool-v2.json',import.meta.url));const registry=registryFromBytes(bytes);
  assert.equal(selectCases(registry).length,4);assert.deepEqual(new Set(selectCases(registry).map(c=>c.operations.map(o=>o.interface).join('/'))),new Set(['ui/ui','api/ui','ui/api','api/api']));
  assert.equal(selectCases(registry,'all').length,44);assert.throws(()=>selectCases(registry,'invalid'));
  assert.throws(()=>registryFromBytes(Buffer.concat([bytes,Buffer.from('\n')])),/Registry bytes differ/);
});
test('owned process cleanup handles graceful and forced exits without killing other processes',async()=>{
  for(const ignore of [false,true]){
    const source=(ignore?'process.on("SIGTERM",()=>{});':'')+'console.log("ready");setInterval(()=>{},1000)';
    const child=spawn(process.execPath,['-e',source],{detached:true,stdio:['ignore','pipe','pipe']});await once(child.stdout,'data');
    const result=await stopOwned(child,100);assert.equal(result.graceful,!ignore);assert.notEqual(child.signalCode,null);assert.throws(()=>process.kill(child.pid,0),/ESRCH/);
  }
});
test('saved passing evidence cannot override a nonzero, signalled or unconfirmed child exit',()=>{
  assert.ok(childExitedCleanly({code:0,signal:null}));
  for(const result of [{code:1,signal:null},{code:null,signal:'SIGTERM'},{code:0,exit_unconfirmed:true},{code:0,spawn_error:'failed'}])assert.equal(childExitedCleanly(result),false);
});
