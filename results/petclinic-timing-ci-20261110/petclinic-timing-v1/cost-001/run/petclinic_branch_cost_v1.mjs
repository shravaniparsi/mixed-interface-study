/** Monotonic attempted-branch cost; common setup and summary writes are outside. */
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {performance} from 'node:perf_hooks';
export const SCOPE='petclinic_branch_reset_through_raw_validation_and_owned_cleanup_v1';
export const monotonicSeconds=()=>performance.now()/1000;
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const finite=value=>typeof value==='number'&&Number.isFinite(value)&&value>=0;

export function beginBranch(identity,clock=monotonicSeconds){
  assert.equal(typeof identity.candidate_id,'string');assert.ok(identity.candidate_id.length);
  assert.ok(['api_semantic','fresh_ui'].includes(identity.oracle));
  const start=clock();assert.ok(finite(start),'Invalid start clock');
  return {schema_version:1,scope:SCOPE,candidate_id:identity.candidate_id,oracle:identity.oracle,
    started_monotonic_s:start,finished_monotonic_s:null,observed_elapsed_s:null,branch_total_s:null,
    raw_sha256:null,measurement_status:'incomplete_interval',incomplete_reason:'end_not_observed'};
}

export function finishBranch(start,rawBytes,clock=monotonicSeconds){
  validateCost(start);
  assert.equal(start.incomplete_reason,'end_not_observed','Interval already ended');
  const raw=JSON.parse(rawBytes.toString());
  assert.equal(raw.candidate_id,start.candidate_id);assert.equal(raw.oracle,start.oracle);
  assert.equal(typeof raw.status,'string');assert.ok(raw.status.length&&raw.status!=='running','Branch status unfinished');
  const hash=sha(rawBytes); // Evidence read, identity validation and hashing are inside the interval.
  const end=clock();assert.ok(finite(end)&&end>=start.started_monotonic_s,'Invalid end clock');
  const elapsed=end-start.started_monotonic_s;const complete=raw.backend_cleanup?.confirmed===true&&raw.context_cleanup_confirmed===true;
  return {...start,finished_monotonic_s:end,observed_elapsed_s:elapsed,branch_total_s:complete?elapsed:null,
    raw_sha256:hash,measurement_status:complete?'complete_interval':'incomplete_interval',
    incomplete_reason:complete?null:'owned_cleanup_unconfirmed'};
}

export function validateCost(record,rawBytes){
  const keys=['schema_version','scope','candidate_id','oracle','started_monotonic_s','finished_monotonic_s',
    'observed_elapsed_s','branch_total_s','raw_sha256','measurement_status','incomplete_reason'];
  assert.deepEqual(Object.keys(record).sort(),keys.sort(),'Timing fields differ');
  assert.equal(record.schema_version,1);assert.equal(record.scope,SCOPE);
  assert.equal(typeof record.candidate_id,'string');assert.ok(record.candidate_id.length);
  assert.ok(['api_semantic','fresh_ui'].includes(record.oracle));assert.ok(finite(record.started_monotonic_s));
  if(record.finished_monotonic_s===null){
    assert.equal(record.measurement_status,'incomplete_interval');assert.equal(record.incomplete_reason,'end_not_observed');
    for(const key of ['observed_elapsed_s','branch_total_s','raw_sha256'])assert.equal(record[key],null);
    return record;
  }
  assert.ok(finite(record.finished_monotonic_s)&&record.finished_monotonic_s>=record.started_monotonic_s);
  const elapsed=record.finished_monotonic_s-record.started_monotonic_s;
  assert.equal(record.observed_elapsed_s,elapsed);
  assert.ok(rawBytes,'Final interval requires raw evidence');const raw=JSON.parse(rawBytes.toString());
  assert.equal(record.raw_sha256,sha(rawBytes));assert.equal(record.candidate_id,raw.candidate_id);assert.equal(record.oracle,raw.oracle);
  assert.equal(typeof raw.status,'string');assert.ok(raw.status.length&&raw.status!=='running');
  if(record.measurement_status==='complete_interval'){
    assert.equal(record.incomplete_reason,null);assert.equal(raw.backend_cleanup?.confirmed,true);assert.equal(raw.context_cleanup_confirmed,true);assert.equal(record.branch_total_s,elapsed);
  }else{
    assert.equal(record.measurement_status,'incomplete_interval');assert.equal(record.incomplete_reason,'owned_cleanup_unconfirmed');
    assert.ok(raw.backend_cleanup?.confirmed!==true||raw.context_cleanup_confirmed!==true);assert.equal(record.branch_total_s,null);
  }
  return record;
}
