/** One frozen ordinary API create; private evidence, no persistence claim. */
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const schedule = JSON.parse(await readFile(new URL('../../manifests/catalog-seatsurfing-input-schedule-v1.json', import.meta.url), 'utf8'));
assert.equal(schedule.revision, '9953f452324bab6fb8f7106dd8965cc401aa456c');
export async function createSeatsurfingOrdinaryApi({ credentials, timeoutMs = 30000, fetchImpl = globalThis.fetch }) {
  assert.ok(Number.isInteger(timeoutMs) && timeoutMs > 0 && timeoutMs <= 30000);
  assert.ok(typeof credentials.accessToken === 'string' && credentials.accessToken.length > 0);
  assert.ok(credentials.accessTokenExpiryMs > Date.now() + timeoutMs + 120000);
  const request = { method: 'POST', url: 'http://127.0.0.1:8080/location/',
    headers: { 'content-type': 'application/json', authorization: 'Bearer ' + credentials.accessToken },
    body: JSON.stringify(schedule.ordinary) };
  const envelope = { request, dispatchedAt: Date.now() };
  const controller = new AbortController();
  let timer, expired = false;
  const timeout = new Promise(resolve => {
    timer = setTimeout(() => { expired = true; controller.abort(); resolve({ outcome: 'observation_deadline' }); }, timeoutMs);
  });
  async function execute() {
    try {
      const response = await fetchImpl(request.url, { method: request.method, headers: request.headers,
        body: request.body, redirect: 'manual', signal: controller.signal });
      envelope.response = { status: response.status, headers: Object.fromEntries(response.headers.entries()) };
      const chunks = []; let bytes = 0;
      if (response.body) {
        const reader = response.body.getReader();
        try {
          while (true) {
            const part = await reader.read(); if (part.done) break;
            bytes += part.value.byteLength;
            if (bytes > 524288) { await reader.cancel(); throw new Error('Create response exceeds observation bound'); }
            chunks.push(Buffer.from(part.value));
          }
        } finally { reader.releaseLock(); }
      }
      envelope.response.body = Buffer.concat(chunks).toString('utf8');
      envelope.response.bodySha256 = createHash('sha256').update(envelope.response.body).digest('hex');
      envelope.completedAt = Date.now();
      if (response.status !== 201) return { outcome: 'ordinary_create_not_201' };
      const createdId = response.headers.get('x-object-id');
      if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(createdId ?? '')) return { outcome: 'ordinary_create_missing_identity' };
      return { outcome: 'ordinary_create_http_observed', createdId };
    } catch (error) {
      return { outcome: expired ? 'observation_deadline' : 'transport_or_observation_failure', error: { name: error.name, message: error.message } };
    }
  }
  try {
    const result = await Promise.race([execute(), timeout]);
    return structuredClone({ ...result, envelope, retryCount: 0, automaticReadbackPerformed: false,
      persistenceEstablished: false, runtimeQualified: false });
  } finally { clearTimeout(timer); controller.abort(); }
}

export function bindSeatsurfingOrdinaryProducers({ native, api, accessToken }) {
  assert.equal(native.observation, 'main_response_observed');
  assert.equal(native.completePayloadMatches, true);
  assert.equal(native.createdIdValid, true);
  assert.equal(api.outcome, 'ordinary_create_http_observed');
  assert.equal(native.response.status, 201); assert.equal(api.envelope.response.status, 201);
  assert.equal(api.retryCount, 0);
  for (const request of [native.request, api.envelope.request]) {
    assert.equal(request.method, 'POST'); assert.equal(request.url, 'http://127.0.0.1:8080/location/');
    assert.equal(request.headers.authorization, 'Bearer ' + accessToken);
    assert.equal(request.headers['content-type'], 'application/json');
    assert.deepEqual(JSON.parse(request.body), schedule.ordinary);
  }
  for (const id of [native.createdId, api.createdId]) assert.match(id, /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
  assert.equal(native.response.headers['x-object-id'], native.createdId);
  assert.equal(api.envelope.response.headers['x-object-id'], api.createdId);
  assert.notEqual(native.createdId, api.createdId);
  return { nativeId: native.createdId, apiId: api.createdId, completeOrdinaryPayloadsMatch: true,
    sameBearerToken: true, otherHeadersQualified: false, persistenceEstablished: false, runtimeQualified: false };
}
