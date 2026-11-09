import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateJob} from '../scripts/petclinic_job_binding.mjs';
const controls=readFileSync(new URL('../manifests/petclinic-terminal-controls-v2.json',import.meta.url));
const registry=readFileSync(new URL('../manifests/petclinic-candidates-v1.json',import.meta.url));
const jobs=JSON.parse(controls).allowed_jobs;
test('all frozen initial and followup jobs validate',()=>{for(const j of jobs)assert.deepEqual(validateJob(j,registry,controls),j);});
test('reordered, foreign, extra-field and reset-disabled jobs fail',()=>{
  const variants=[j=>j.branches.reverse(),j=>j.pair_id='foreign',j=>j.extra=true,j=>j.branches[0].fresh_reset_required=false];
  for(const mutate of variants){const j=structuredClone(jobs[0]);mutate(j);assert.throws(()=>validateJob(j,registry,controls));}
});
test('changed registry and controls fail',()=>{
  assert.throws(()=>validateJob(jobs[0],Buffer.concat([registry,Buffer.from(' ')]),controls));
  assert.throws(()=>validateJob(jobs[0],registry,Buffer.concat([controls,Buffer.from(' ')])));
});
