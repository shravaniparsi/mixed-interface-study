import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {stopOwnedProcess} from '../scripts/petclinic_cleanup.mjs';
const fake=()=>Object.assign(new EventEmitter(),{pid:17,exitCode:null,signalCode:null});
test('cleanup confirms graceful process exit',async()=>{const p=fake();p.kill=s=>{p.signalCode=s;p.emit('exit');};assert.equal((await stopOwnedProcess(p,{graceMs:5,killMs:5})).confirmed,true);assert.equal(p.listenerCount('exit'),0);});
test('unconfirmed forced kill returns by deadline without claiming cleanup',async()=>{const p=fake(),signals=[];p.kill=s=>signals.push(s);const r=await stopOwnedProcess(p,{graceMs:5,killMs:5});assert.deepEqual(signals,['SIGTERM','SIGKILL']);assert.equal(r.confirmed,false);assert.equal(p.listenerCount('exit'),0);});
test('already-exited owned process is never signalled',async()=>{const p=fake();p.exitCode=0;p.kill=()=>assert.fail();assert.equal((await stopOwnedProcess(p)).already_exited,true);});
