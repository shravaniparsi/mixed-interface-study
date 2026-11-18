/** Bounded request-plan executor. All returned envelopes are PRIVATE evidence.
 * Not runtime-qualified. Caller supplies verified restored identity/credentials,
 * isolated network and a separately enforced worker/process deadline.
 */
import assert from 'node:assert/strict';

export async function executeSeatsurfingLocationPlan({ plan, baseUrl, credentials, timeoutMs = 30000, fetchImpl = globalThis.fetch }) {
  assert.ok(Number.isInteger(timeoutMs) && timeoutMs > 0 && timeoutMs <= 30000);
  const base = new URL(baseUrl);
  assert.ok(['http:', 'https:'].includes(base.protocol));
  assert.equal(base.username + base.password + base.search + base.hash, '');
  assert.ok(base.pathname === '/' || base.pathname === '');
  assert.equal(plan.scope, 'fresh_editor_scalar_edit_without_map_design_or_file_changes');
  assert.equal(plan.main.method, 'PUT');
  assert.match(plan.main.path, /^\/location\/[0-9a-f-]{36}$/i);
  assert.equal(plan.nativeAutomaticReadback, false);
  assert.equal(plan.nativeSavedStateWaitsForAttributeCompletion, false);
  assert.equal(plan.mapWrite, null);
  assert.deepEqual(plan.spaceOrImageWrites, []);
  assert.ok(Array.isArray(plan.afterMainSuccess));
  assert.equal(plan.attributeDispatch, 'start_in_readback_order_without_awaiting_completion_between_dispatches');
  for (const item of [plan.main, ...plan.afterMainSuccess]) {
    assert.equal(item.body, JSON.stringify(item.json));
    assert.equal(new URL(item.path, base).origin, base.origin);
  }
  for (const item of plan.afterMainSuccess) {
    assert.equal(item.method, 'POST');
    assert.ok(item.path.startsWith(plan.main.path + '/attribute/'));
    assert.match(item.path.slice((plan.main.path + '/attribute/').length), /^[0-9a-f-]{36}$/i);
  }
  const started = Date.now();
  const deadline = started + timeoutMs;
  assert.ok(typeof credentials.accessToken === 'string' && credentials.accessToken.length > 0);
  assert.ok(Number.isFinite(credentials.accessTokenExpiryMs) && credentials.accessTokenExpiryMs > deadline + 1000,
    'Credential lifetime does not cover operation; no request dispatched');
  const controller = new AbortController();
  const envelopes = [];
  let expired = false;
  let timer;
  const timeout = new Promise(resolve => {
    timer = setTimeout(() => {
      expired = true;
      controller.abort();
      resolve({ outcome: 'observation_deadline', envelopes });
    }, timeoutMs);
  });
  const dispatch = async (item, stage) => {
    if (expired) return { outcome: 'not_dispatched_deadline' };
    const row = { sequence: envelopes.length + 1, stage, method: item.method,
      url: new URL(item.path, base).href, body: item.body,
      headers: { 'content-type': 'application/json', authorization: 'Bearer ' + credentials.accessToken },
      dispatchedAt: Date.now(), outcome: 'pending' };
    envelopes.push(row);
    try {
      const response = await fetchImpl(row.url, { method: row.method, headers: row.headers,
        body: row.body, redirect: 'manual', signal: controller.signal });
      row.status = response.status;
      row.responseHeaders = Object.fromEntries(response.headers.entries());
      const parts = [];
      let count = 0;
      if (response.body) {
        const reader = response.body.getReader();
        try {
          while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            count += value.byteLength;
            if (count > 524288) {
              await reader.cancel();
              throw new Error('Response exceeds 512 KiB observation bound');
            }
            parts.push(Buffer.from(value));
          }
        } finally { reader.releaseLock(); }
      }
      row.responseBody = Buffer.concat(parts).toString('utf8');
      row.outcome = response.status >= 200 && response.status < 300 ? 'http_accepted' :
        response.status >= 300 && response.status < 400 ? 'unsupported_redirect' : 'http_rejected';
    } catch (error) {
      row.outcome = expired ? 'observation_deadline' : 'transport_or_observation_failure';
      row.error = { name: error.name, message: error.message };
    }
    row.completedAt = Date.now();
    return row;
  };
  const operation = async () => {
    const main = await dispatch(plan.main, 'main');
    if (main.outcome !== 'http_accepted') return { outcome: 'main_not_accepted', envelopes };
    if (expired) return { outcome: 'observation_deadline', envelopes };
    // Start all attribute calls in source order. Waiting here is evidence
    // collection, not a claim that the original saved flag awaited them.
    const attributes = await Promise.all(plan.afterMainSuccess.map(item => dispatch(item, 'attribute')));
    return { outcome: attributes.every(row => row.outcome === 'http_accepted') ? 'all_http_accepted' : 'partial_or_unavailable', envelopes };
  };
  try {
    const result = await Promise.race([operation(), timeout]);
    return structuredClone({ ...result, elapsedMs: Date.now() - started,
      applicationPersistenceQualified: false, nativeSavedStateWaitsForAttributes: false,
      retryCount: 0, automaticReadbackPerformed: false });
  } finally {
    clearTimeout(timer);
    controller.abort();
  }
}
