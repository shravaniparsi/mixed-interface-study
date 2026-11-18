/** PRIVATE browser observation. This module starts no browser or application.
 * Quiescence is bounded network observation, not proof of application/DB idleness.
 */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
const hash = raw => createHash('sha256').update(raw).digest('hex');

export function observeSeatsurfingBrowser(context, origin) {
  assert.equal(new URL(origin).origin, origin);
  const events = [];
  const pending = new Set();
  const captures = new Set();
  const ids = new WeakMap();
  let next = 0, bytes = 0, failure = null, lastActivity = Date.now();
  function record(event) {
    lastActivity = Date.now();
    const row = { at: lastActivity, ...event };
    bytes += Buffer.byteLength(JSON.stringify(row));
    if (events.length >= 5000 || bytes > 16 * 1024 * 1024) {
      failure = 'Private network evidence bound exceeded';
      return;
    }
    events.push(row);
  }
  function collect(fn) {
    const task = Promise.resolve().then(fn).catch(error => {
      failure = error.message;
      record({ kind: 'capture_failure', message: error.message });
    });
    captures.add(task);
    task.finally(() => captures.delete(task));
  }
  const onRequest = request => {
    const id = ++next; ids.set(request, id); pending.add(id);
    const url = new URL(request.url());
    if (url.origin !== origin) failure = 'Unexpected browser request origin';
    const body = request.postData();
    if (body !== null && Buffer.byteLength(body) > 65536) failure = 'Request body observation bound exceeded';
    record({ kind: 'request', id, method: request.method(), url: request.url(),
      resourceType: request.resourceType(), body: body !== null && Buffer.byteLength(body) <= 65536 ? body : null });
    collect(async () => record({ kind: 'request_headers', id, headers: await request.allHeaders() }));
  };
  const onResponse = response => collect(async () => {
    const request = response.request(); const id = ids.get(request);
    assert.ok(id, 'Response without observed request');
    const headers = await response.allHeaders();
    const row = { kind: 'response', id, status: response.status(), headers, bodyCaptured: false };
    if (['xhr', 'fetch'].includes(request.resourceType())) {
      const body = await response.body();
      assert.ok(body.length <= 524288, 'API response observation bound exceeded');
      Object.assign(row, { body: body.toString('utf8'), bodySha256: hash(body), bodyCaptured: true });
    }
    record(row);
  });
  const onFinished = request => { const id = ids.get(request); pending.delete(id); record({ kind: 'finished', id }); };
  const onFailed = request => { const id = ids.get(request); pending.delete(id); record({ kind: 'request_failed', id, failure: request.failure() }); failure = 'Browser request failed'; };
  context.on('request', onRequest); context.on('response', onResponse);
  context.on('requestfinished', onFinished); context.on('requestfailed', onFailed);
  return {
    async quiet({ timeoutMs = 10000, quietMs = 500 } = {}) {
      assert.ok(timeoutMs > 0 && timeoutMs <= 30000 && quietMs >= 0 && quietMs < timeoutMs);
      const end = Date.now() + timeoutMs;
      while (Date.now() < end) {
        if (failure) throw new Error(failure);
        if (!pending.size && !captures.size && Date.now() - lastActivity >= quietMs) {
          const raw = Buffer.from(JSON.stringify(events));
          return { events: structuredClone(events), traceSha256: hash(raw), traceEncoding: 'UTF8_JSON_stringify_events',
            pendingRequests: 0, pendingCaptures: 0, quietMs, observedAt: Date.now(), applicationIdlenessEstablished: false };
        }
        await new Promise(resolve => setTimeout(resolve, 10));
      }
      failure = 'Network observation deadline; pending activity retained, no retry authorized';
      throw new Error(failure);
    },
    snapshot() { return structuredClone({ events, pendingIds: [...pending], pendingCaptures: captures.size, failure }); },
    dispose() {
      context.off('request', onRequest); context.off('response', onResponse);
      context.off('requestfinished', onFinished); context.off('requestfailed', onFailed);
    },
  };
}

export async function captureSeatsurfingBrowserState({ context, page, observer, origin, nativeCredentials, minimumLifetimeMs = 120000 }) {
  assert.ok(Number.isSafeInteger(minimumLifetimeMs) && minimumLifetimeMs >= 120000);
  assert.equal(context.pages().length, 1, 'Unmapped additional browser pages');
  assert.equal(context.serviceWorkers().length, 0, 'Unmapped service-worker state');
  assert.equal(page.workers().length, 0, 'Unmapped dedicated-worker state');
  await observer.quiet();
  const readDiagnostics = () => page.evaluate(async () => ({
    sessionStorage: Object.fromEntries(Object.entries(sessionStorage)),
    cacheNames: 'caches' in globalThis ? await caches.keys() : [],
    accessToken: localStorage.getItem('accessToken'),
    refreshToken: localStorage.getItem('refreshToken'),
    expiry: Number(localStorage.getItem('accessTokenExpiry')),
  }));
  const diagnostics = await readDiagnostics();
  assert.deepEqual(diagnostics.sessionStorage, {}, 'Session storage requires a qualified restoration mapping');
  assert.deepEqual(diagnostics.cacheNames, [], 'Cache Storage requires a qualified restoration mapping');
  assert.equal(diagnostics.accessToken, nativeCredentials.accessToken, 'Original access token changed');
  assert.equal(diagnostics.refreshToken, nativeCredentials.refreshToken, 'Original refresh token changed');
  assert.ok(Number.isFinite(diagnostics.expiry) && diagnostics.expiry > Date.now() + minimumLifetimeMs);
  const storage = await context.storageState({ indexedDB: true });
  assert.equal(storage.origins.length, 1);
  assert.equal(storage.origins[0].origin, origin);
  const captured = Object.fromEntries(storage.origins[0].localStorage.map(x => [x.name, x.value]));
  assert.equal(captured.accessToken, diagnostics.accessToken);
  assert.equal(captured.refreshToken, diagnostics.refreshToken);
  const network = await observer.quiet();
  const finalStorage = await context.storageState({ indexedDB: true });
  assert.deepEqual(finalStorage, storage, 'Browser storage changed during observation window');
  assert.deepEqual(await readDiagnostics(), diagnostics, 'Browser diagnostics changed during observation window');
  assert.ok(diagnostics.expiry > Date.now() + minimumLifetimeMs, 'Credential lifetime fell below checkpoint minimum');
  assert.equal(context.pages().length, 1);
  assert.equal(context.serviceWorkers().length, 0);
  assert.equal(page.workers().length, 0);
  const raw = JSON.stringify(storage);
  return { storage, storageBytes: raw, storageSha256: hash(raw), diagnostics, network,
    nativeStorageCapture: true, browserRequestsSettled: true,
    actorVerified: false, applicationOperationsSettled: false, containersPaused: false,
    runtimeQualified: false };
}
