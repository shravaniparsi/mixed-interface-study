import test from 'node:test';
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { observeSeatsurfingBrowser, captureSeatsurfingBrowserState } from '../scripts/extension/seatsurfing_browser_observation_v1.mjs';
const origin='http://fixture.invalid:8080';
const request=(url=origin+'/location/')=>({url:()=>url,method:()=> 'POST',postData:()=>'{"name":"fixture"}',resourceType:()=> 'fetch',allHeaders:async()=>({'content-type':'application/json'}),failure:()=>({errorText:'synthetic'})});
test('finished request waits for asynchronous body capture',async()=>{
  const context=new EventEmitter();const observer=observeSeatsurfingBrowser(context,origin);const req=request();let release;
  const body=new Promise(resolve=>{release=resolve;});
  context.emit('request',req);context.emit('response',{request:()=>req,allHeaders:async()=>({}),status:()=>201,body:()=>body});context.emit('requestfinished',req);
  let completed=false;
  const waiting=observer.quiet({timeoutMs:1000,quietMs:0}).then(result=>{completed=true;return result;});
  await new Promise(resolve=>setTimeout(resolve,25));assert.equal(completed,false);
  release(Buffer.from(''));const result=await waiting;
  assert.ok(result.events.some(x=>x.kind==='response'&&x.bodyCaptured));assert.equal(result.pendingCaptures,0);observer.dispose();
});
test('pending request remains pending after observation expiration',async()=>{
  const context=new EventEmitter();const observer=observeSeatsurfingBrowser(context,origin);context.emit('request',request());
  await assert.rejects(()=>observer.quiet({timeoutMs:20,quietMs:0}),/deadline/);assert.equal(observer.snapshot().pendingIds.length,1);observer.dispose();
});
test('failed request is retained and cannot qualify quiescence',async()=>{
  const context=new EventEmitter();const observer=observeSeatsurfingBrowser(context,origin);const req=request();context.emit('request',req);context.emit('requestfailed',req);
  await assert.rejects(()=>observer.quiet({timeoutMs:50,quietMs:0}),/failed/);assert.ok(observer.snapshot().events.some(x=>x.kind==='request_failed'));observer.dispose();
});
test('external request is evidence of an unsupported path',async()=>{
  const context=new EventEmitter();const observer=observeSeatsurfingBrowser(context,origin);context.emit('request',request('https://foreign.invalid/a'));
  await assert.rejects(()=>observer.quiet({timeoutMs:50,quietMs:0}),/origin/);observer.dispose();
});
test('oversized API response cannot produce a qualified trace',async()=>{
  const context=new EventEmitter();const observer=observeSeatsurfingBrowser(context,origin);const req=request();context.emit('request',req);context.emit('response',{request:()=>req,allHeaders:async()=>({}),status:()=>200,body:async()=>Buffer.alloc(524289)});context.emit('requestfinished',req);
  await assert.rejects(()=>observer.quiet({timeoutMs:100,quietMs:0}),/bound/);observer.dispose();
});

function stateFixture() {
  const credentials={accessToken:'synthetic-access',refreshToken:'synthetic-refresh'};
  const storage={cookies:[],origins:[{origin,localStorage:[{name:'accessToken',value:credentials.accessToken},{name:'refreshToken',value:credentials.refreshToken}]}]};
  const diagnostics={sessionStorage:{},cacheNames:[],...credentials,expiry:Date.now()+600000};
  const page={workers:()=>[],evaluate:async()=>diagnostics};
  const context={pages:()=>[page],serviceWorkers:()=>[],storageState:async opts=>{assert.equal(opts.indexedDB,true);return structuredClone(storage);}};
  return {context,page,observer:{quiet:async()=>({events:[],traceSha256:'synthetic'})},origin,nativeCredentials:credentials,storage,diagnostics};
}
test('stable snapshot retains native bytes but does not assert actor/application readiness',async()=>{
  const x=stateFixture();const result=await captureSeatsurfingBrowserState(x);
  assert.deepEqual(JSON.parse(result.storageBytes),x.storage);assert.equal(result.actorVerified,false);assert.equal(result.applicationOperationsSettled,false);assert.equal(result.containersPaused,false);
});
test('changing snapshot cannot qualify capture',async()=>{
  const x=stateFixture();let calls=0;x.context.storageState=async()=>{const value=structuredClone(x.storage);if(++calls===2)value.origins[0].localStorage.push({name:'changed',value:'yes'});return value;};
  await assert.rejects(()=>captureSeatsurfingBrowserState(x),/storage changed/);
});
test('unmapped session storage prevents capture',async()=>{
  const x=stateFixture();x.diagnostics.sessionStorage={unmapped:'value'};
  await assert.rejects(()=>captureSeatsurfingBrowserState(x),/Session storage/);
});
test('rotated token prevents capture',async()=>{
  const x=stateFixture();x.diagnostics.accessToken='changed';
  await assert.rejects(()=>captureSeatsurfingBrowserState(x),/token changed/);
});

test('expired observation cannot later qualify after pending request finishes',async()=>{
  const context=new EventEmitter();const observer=observeSeatsurfingBrowser(context,origin);const req=request();context.emit('request',req);
  await assert.rejects(()=>observer.quiet({timeoutMs:20,quietMs:0}),/deadline/);
  context.emit('requestfinished',req);
  await assert.rejects(()=>observer.quiet({timeoutMs:100,quietMs:0}),/deadline/);observer.dispose();
});
test('session state appearing during capture cannot qualify',async()=>{
  const x=stateFixture();let calls=0;
  x.page.evaluate=async()=>({...x.diagnostics,sessionStorage:++calls===1?{}:{late:'value'}});
  await assert.rejects(()=>captureSeatsurfingBrowserState(x),/diagnostics changed/);
});
