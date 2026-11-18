/** Source-aware API continuation; independent fresh loading, no UI interaction. */
import assert from 'node:assert/strict';
import { loadSeatsurfingApiState } from './load_seatsurfing_api_state_v1.mjs';
import { materializeSeatsurfingLocationUpdate } from './materialize_seatsurfing_location_update_v1.mjs';
import { executeSeatsurfingLocationPlan } from './execute_seatsurfing_location_plan_v1.mjs';
export async function runSeatsurfingApiContinuation({ id, credentials, edit, fetchImpl = globalThis.fetch }) {
  assert.equal(Intl.DateTimeFormat().resolvedOptions().timeZone, 'UTC', 'Require registered UTC runtime before loading');
  const edits = [{path:'/description',value:'Edit description'},{path:'/announcement',value:'Edit notice'}];
  assert.ok(edits.some(value=>JSON.stringify(value)===JSON.stringify(edit)), 'Edit not in frozen schedule');
  const loaded = await loadSeatsurfingApiState({ id, credentials, fetchImpl });
  if (loaded.outcome !== 'source_inputs_loaded') return {outcome:'loading_unavailable',loaded,runtimeQualified:false};
  const plan = materializeSeatsurfingLocationUpdate({...loaded.materialization,edit});
  const execution = await executeSeatsurfingLocationPlan({plan,baseUrl:'http://127.0.0.1:8080',credentials,fetchImpl});
  return {outcome:'continuation_observed',loaded,plan,execution, runtimeQualified:false,
    completeNativeEqualityEstablished:false,applicationPersistenceQualified:false};
}
