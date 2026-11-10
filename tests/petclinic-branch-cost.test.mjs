import test from 'node:test';
import assert from 'node:assert/strict';
import {beginBranch,finishBranch,validateCost} from '../scripts/petclinic_branch_cost_v1.mjs';
const identity={candidate_id:'owner-test',oracle:'fresh_ui'};
const raw=(status='continuation_passed',confirmed=true)=>Buffer.from(JSON.stringify({...identity,status,backend_cleanup:{confirmed},context_cleanup_confirmed:true}));

test('elapsed attempted cost includes semantic failures when owned cleanup completes',()=>{
  for(const status of ['continuation_passed','prefix_rejected','ui_blocked','runner_or_assertion_failure']){
    const start=beginBranch(identity,()=>10);const bytes=raw(status);const end=finishBranch(start,bytes,()=>17.5);
    assert.equal(end.branch_total_s,7.5);assert.equal(end.measurement_status,'complete_interval');
    assert.deepEqual(validateCost(end,bytes),end);assert.equal(start.finished_monotonic_s,null);
    assert.throws(()=>finishBranch(end,bytes,()=>20));
  }
});
test('missing end and unconfirmed cleanup never yield completed branch totals',()=>{
  const start=beginBranch(identity,()=>2);assert.equal(validateCost(start).branch_total_s,null);
  const bytes=raw('runner_or_assertion_failure',false);const end=finishBranch(start,bytes,()=>6);
  assert.equal(end.observed_elapsed_s,4);assert.equal(end.branch_total_s,null);assert.equal(end.incomplete_reason,'owned_cleanup_unconfirmed');
  validateCost(end,bytes);
  const promoted={...end,measurement_status:'complete_interval',incomplete_reason:null,branch_total_s:4};
  assert.throws(()=>validateCost(promoted,bytes));
});
test('changed evidence, identity, duration and nonfinite clocks are rejected',()=>{
  const start=beginBranch(identity,()=>5);const bytes=raw();const end=finishBranch(start,bytes,()=>8);
  assert.throws(()=>validateCost(end,raw('ui_blocked')));
  assert.throws(()=>finishBranch(start,Buffer.from(JSON.stringify({candidate_id:'foreign',oracle:'fresh_ui',status:'done'})),()=>8));
  for(const clock of [NaN,Infinity,-1])assert.throws(()=>beginBranch(identity,()=>clock));
  for(const clock of [NaN,Infinity,4])assert.throws(()=>finishBranch(start,bytes,()=>clock));
  assert.throws(()=>validateCost({...end,branch_total_s:2},bytes));
  assert.throws(()=>validateCost({...end,raw_sha256:'0'.repeat(64)},bytes));
  assert.throws(()=>finishBranch(start,raw('running'),()=>8));
  assert.throws(()=>validateCost(end));
});

test('failed context cleanup prevents complete cost even with backend exit',()=>{
  const start=beginBranch(identity,()=>1);const bytes=Buffer.from(JSON.stringify({...identity,status:'runner_or_assertion_failure',backend_cleanup:{confirmed:true},context_cleanup_confirmed:false}));
  const end=finishBranch(start,bytes,()=>3);assert.equal(end.branch_total_s,null);validateCost(end,bytes);
});
