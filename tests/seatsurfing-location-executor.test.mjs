import test from 'node:test';
import assert from 'node:assert/strict';
import { executeSeatsurfingLocationPlan as execute } from '../scripts/extension/execute_seatsurfing_location_plan_v1.mjs';
const id = '11111111-1111-4111-8111-111111111111';
const attr = '22222222-2222-4222-8222-222222222222';
const item = (method, path, json) => ({ method, path, json, body: JSON.stringify(json) });
function options() {
  return { baseUrl: 'http://fixture.invalid', timeoutMs: 1000, credentials: { accessToken: 'synthetic', accessTokenExpiryMs: Date.now() + 60000 }, plan: { scope: 'fresh_editor_scalar_edit_without_map_design_or_file_changes', main: item('PUT', '/location/' + id, {name:'ordinary'}), afterMainSuccess: [item('POST','/location/' + id + '/attribute/' + attr,{value:'one'}),item('POST','/location/' + id + '/attribute/' + attr,{value:'two'})], attributeDispatch:'start_in_readback_order_without_awaiting_completion_between_dispatches', nativeAutomaticReadback:false, nativeSavedStateWaitsForAttributeCompletion:false, mapWrite:null, spaceOrImageWrites:[] } };
}
test('main success gates concurrent attribute dispatch; partial failures retained', async () => {
  const calls=[]; let release;
  const pending = new Promise(resolve => { release=resolve; });
  const x=options(); x.fetchImpl=async (url, opts) => {
    calls.push(JSON.parse(opts.body));
    if(opts.method==='PUT') return new Response(null,{status:204});
    if(JSON.parse(opts.body).value==='one') return pending;
    release(new Response('failed',{status:400}));
    return new Response(null,{status:204});
  };
  const result=await execute(x);
  assert.deepEqual(calls,[{name:'ordinary'},{value:'one'},{value:'two'}]);
  assert.equal(result.outcome,'partial_or_unavailable');
  assert.deepEqual(result.envelopes.map(x=>x.status),[204,400,204]);
  assert.equal(result.retryCount,0);
});
test('main rejection sends no ancillary writes', async () => {
  let calls=0; const x=options(); x.fetchImpl=async()=>{calls++;return new Response('reject',{status:400});};
  const result=await execute(x); assert.equal(calls,1);assert.equal(result.outcome,'main_not_accepted');
});
test('short-lived credentials fail before all network activity', async()=>{
  let calls=0;const x=options();x.credentials.accessTokenExpiryMs=Date.now();x.fetchImpl=async()=>{calls++;};
  await assert.rejects(()=>execute(x),/Credential lifetime/);assert.equal(calls,0);
});
test('stalled observation times out without resending',async()=>{
  let calls=0;const x=options();x.timeoutMs=20;x.fetchImpl=()=>{calls++;return new Promise(()=>{});};
  const result=await execute(x);assert.equal(result.outcome,'observation_deadline');assert.equal(calls,1);assert.equal(result.envelopes.length,1);
});
test('oversized response is unavailable and does not trigger ancillary writes',async()=>{
  let calls=0;const x=options();x.fetchImpl=async()=>{calls++;return new Response('x'.repeat(524289),{status:200});};
  const result=await execute(x);assert.equal(calls,1);assert.equal(result.envelopes[0].outcome,'transport_or_observation_failure');
});
test('redirect is retained without following it',async()=>{
  let calls=0;const x=options();x.fetchImpl=async(url,opts)=>{calls++;assert.equal(opts.redirect,'manual');return new Response(null,{status:307,headers:{location:'https://elsewhere.invalid'}});};
  const result=await execute(x);assert.equal(calls,1);assert.equal(result.envelopes[0].outcome,'unsupported_redirect');
});
