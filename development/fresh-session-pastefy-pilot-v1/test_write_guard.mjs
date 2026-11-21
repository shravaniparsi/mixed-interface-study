import assert from 'node:assert/strict';
import {installWriteGuard} from './write_guard.mjs';
let handler;const records=[];
await installWriteGuard({route:async(pattern,fn)=>{assert.equal(pattern,'**/*');handler=fn;}},records);
for(const method of ['POST','PUT','PATCH','DELETE']){
 let aborted=0;const request={method:()=>method,url:()=> 'http://external.invalid/unexpected',postData:()=>'{"title":"ordinary"}'};
 await handler({request:()=>request,abort:async reason=>{assert.equal(reason,'blockedbyclient');aborted++;},fallback:()=>{throw Error('write escaped');},fetch:()=>{throw Error('write forwarded');},fulfill:()=>{throw Error('response fabricated');}});
 assert.equal(aborted,1);
}
assert.equal(records.length,4);
for(const method of ['GET','HEAD','OPTIONS']){
 let passed=0;await handler({request:()=>({method:()=>method}),fallback:async()=>{passed++;},abort:()=>{throw Error('read blocked');}});assert.equal(passed,1);
}
assert.equal(records.length,4);console.log('write guard: four mutation methods blocked; three read methods delegated');
