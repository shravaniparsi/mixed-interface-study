import test from 'node:test';
import assert from 'node:assert/strict';
import { createSeatsurfingOrdinaryApi, bindSeatsurfingOrdinaryProducers } from '../scripts/extension/create_seatsurfing_ordinary_api_v1.mjs';
const credentials = () => ({ accessToken: 'test-token', accessTokenExpiryMs: Date.now() + 900000 });
const id = '12345678-1234-1234-1234-123456789abc';
const second = '12345678-1234-1234-1234-123456789def';
async function success() { return createSeatsurfingOrdinaryApi({ credentials: credentials(), fetchImpl: async () => new Response('', { status: 201, headers: { 'x-object-id': id } }) }); }
function native(api) { return { observation: 'main_response_observed', completePayloadMatches: true, createdIdValid: true, createdId: second, response: { status: 201, headers: { 'x-object-id': second } }, request: structuredClone(api.envelope.request) }; }
test('ordinary create sends exactly one frozen JSON request and no readback', async () => {
  let calls = 0;
  const result = await createSeatsurfingOrdinaryApi({ credentials: credentials(), fetchImpl: async (url, init) => {
    calls++; assert.equal(url, 'http://127.0.0.1:8080/location/'); assert.equal(init.method, 'POST'); assert.equal(init.redirect, 'manual');
    const body = JSON.parse(init.body); assert.equal(Object.keys(body).length, 12); assert.equal(body.description, 'Study description');
    return new Response('', { status: 201, headers: { 'x-object-id': id } });
  } });
  assert.equal(calls, 1); assert.equal(result.createdId, id); assert.equal(result.persistenceEstablished, false);
});
test('expired credentials rejected before dispatch', async () => {
  await assert.rejects(createSeatsurfingOrdinaryApi({ credentials: { accessToken: 'token', accessTokenExpiryMs: 1 }, fetchImpl: () => assert.fail('dispatch') }));
});
test('redirect and missing identity never establish create success', async () => {
  for (const status of [201, 302, 400]) {
    const result = await createSeatsurfingOrdinaryApi({ credentials: credentials(), fetchImpl: async () => new Response('', { status }) });
    assert.notEqual(result.outcome, 'ordinary_create_http_observed');
  }
});
test('deadline retains immutable partial evidence without resend', async () => {
  let calls = 0, release;
  const delayed = new Promise(resolve => { release = resolve; });
  const result = await createSeatsurfingOrdinaryApi({ credentials: credentials(), timeoutMs: 5, fetchImpl: async () => { calls++; return delayed; } });
  const retained = JSON.stringify(result); release(new Response('', { status: 201, headers: { 'x-object-id': id } }));
  await new Promise(resolve => setTimeout(resolve, 10));
  assert.equal(calls, 1); assert.equal(result.outcome, 'observation_deadline'); assert.equal(JSON.stringify(result), retained);
});
test('response size bound makes observation unavailable', async () => {
  const result = await createSeatsurfingOrdinaryApi({ credentials: credentials(), fetchImpl: async () => new Response('x'.repeat(524289), { status: 201, headers: { 'x-object-id': id } }) });
  assert.equal(result.outcome, 'transport_or_observation_failure');
});
test('complete payload and same bearer binding retain distinct producer identities', async () => {
  const api = await success(); const n = native(api);
  const result = bindSeatsurfingOrdinaryProducers({ native: n, api, accessToken: 'test-token' });
  assert.equal(result.nativeId, second); assert.equal(result.apiId, id); assert.equal(result.otherHeadersQualified, false);
  for (const mutate of [x => { x.request.body = '{}'; }, x => { x.request.headers.authorization = 'other'; }, x => { x.createdId = id; }, x => { x.response.status = 200; }]) {
    const changed = structuredClone(n); mutate(changed);
    assert.throws(() => bindSeatsurfingOrdinaryProducers({ native: changed, api, accessToken: 'test-token' }));
  }
});
