import assert from 'node:assert/strict';
import {createCapture} from './capture.mjs';
const saved=[];let resolveLate;
const c=createCapture({bodyTimeoutMs:30,flushTimeoutMs:60,write:r=>saved.push(r)});
c.observe({path:'/complete'},()=>Promise.resolve('ok'));
c.observe({path:'/error'},()=>{throw new Error('closed response');});
c.observe({path:'/never'},()=>new Promise(r=>resolveLate=r));
assert.equal(saved.at(-1).length,3); // An intermediate record exists before awaiting bodies.
const start=Date.now(),rows=await c.close();assert(Date.now()-start<1000);
assert.deepEqual(rows.map(x=>x.capture.status),['complete','error','body_timeout']);
assert.equal(rows[0].capture.body,'ok');assert.match(rows[1].capture.error,/closed response/);
resolveLate('late body');await new Promise(r=>setTimeout(r,10));assert.equal(c.snapshot()[2].capture.status,'body_timeout');
assert.throws(()=>c.observe({},()=>''),/closed/);
const d=createCapture({bodyTimeoutMs:100,flushTimeoutMs:10,write:()=>{}});let late;
d.observe({},()=>new Promise(r=>late=r));const short=await d.close();assert.equal(short[0].capture.status,'flush_timeout');late('late');await new Promise(r=>setTimeout(r,5));assert.equal(d.snapshot()[0].capture.status,'flush_timeout');
let writes=0;const e=createCapture({write:()=>{if(++writes>=3)throw new Error('disk write failed');}});e.observe({},()=>Promise.resolve('ok'));await assert.rejects(()=>e.close(),/disk write failed/);
assert.throws(()=>createCapture({bodyTimeoutMs:0,write:()=>{}}),/timeout/);
console.log(JSON.stringify({status:'passed',cases:['intermediate_checkpoint','completed_body','read_error','never_settling_body','late_body_ignored','closed_observer','flush_deadline','write_error_not_hidden','invalid_timeout'],application_executed:false,scientific_cases:0}));
