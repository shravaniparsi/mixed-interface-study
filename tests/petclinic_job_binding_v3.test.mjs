import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateJob} from '../scripts/petclinic_job_binding_v3.mjs';
const controls=readFileSync(new URL('../manifests/petclinic-expanded-batches-v3.json',import.meta.url));
const registry=readFileSync(new URL('../manifests/petclinic-candidates-v1.json',import.meta.url));
const batches=JSON.parse(controls).batches;
test('v3 binds every initial and followup job to its frozen batch',()=>{for(const [name,b] of Object.entries(batches))for(const j of b.allowed_jobs)assert.deepEqual(validateJob(j,registry,controls,name),j);});
test('v3 rejects foreign batches and altered jobs',()=>{
 const job=batches.pets.allowed_jobs[0];assert.throws(()=>validateJob(job,registry,controls,'visits'));assert.throws(()=>validateJob(job,registry,controls,'foreign'));
 for(const change of [j=>j.branches.reverse(),j=>j.branches[0].fresh_reset_required=false,j=>j.extra=true]){const j=structuredClone(job);change(j);assert.throws(()=>validateJob(j,registry,controls,'pets'));}
});
test('v3 rejects changed registry and batch contract bytes',()=>{
 const j=batches.pets.allowed_jobs[0];assert.throws(()=>validateJob(j,Buffer.concat([registry,Buffer.from(' ')]),controls,'pets'));assert.throws(()=>validateJob(j,registry,Buffer.concat([controls,Buffer.from(' ')]),'pets'));
});
