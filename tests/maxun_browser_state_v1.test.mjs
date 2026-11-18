import test from 'node:test';
import assert from 'node:assert/strict';
import {restoreBrowserState, captureBrowserState} from '../scripts/extension/maxun_browser_state_v1.mjs';

function mock(drift=false) {
 const events=[];
 const storage={cookies:[],origins:[{origin:'http://localhost:5173',localStorage:[{name:'user',value:'fixture'}]}]};
 const fixture={origin:'http://localhost:5173',session:{selected:'value'},storage};
 let session={},url='about:blank';
 const page={url:()=>url,route:async()=>events.push('route'),unroute:async()=>events.push('unroute'),
   goto:async target=>{url=target;events.push('goto');},
   evaluate:async(fn,arg)=>{if(arg!==undefined){session=structuredClone(arg);events.push('restore-session');return;}events.push('capture-session');return session;}};
 const context={newPage:async()=>page,pages:()=>[page],serviceWorkers:()=>[],
   storageState:async()=>drift?{cookies:[],origins:[]}:structuredClone(storage),close:async()=>events.push('close')};
 const browser={newContext:async options=>{assert.deepEqual(options.storageState,storage);assert.equal(options.serviceWorkers,'block');return context;}};
 return {events,fixture,page,context,browser};
}

test('session restoration is one bootstrap operation, with route removed before comparison',async()=>{
 const m=mock();const result=await restoreBrowserState(m.browser,m.fixture,{locale:'en-US'});
 assert.equal(result.page,m.page);
 assert.deepEqual(m.events,['route','goto','restore-session','unroute','capture-session']);
 assert.equal(result.restored.runtimeQualified,false);
});
test('state mismatch closes context instead of reporting success',async()=>{
 const m=mock(true);
 await assert.rejects(restoreBrowserState(m.browser,m.fixture,{}),/cookies\/localStorage changed/);
 assert.equal(m.events.at(-1),'close');
});
test('additional tabs are explicitly unavailable',async()=>{
 const m=mock();await m.page.goto(m.fixture.origin);
 m.context.pages=()=>[m.page,m.page];
 await assert.rejects(captureBrowserState(m.context,m.page,m.fixture.origin),/additional browser tab/);
});
