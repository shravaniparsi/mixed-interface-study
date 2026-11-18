import test from 'node:test';
import assert from 'node:assert/strict';
import { bindApiTransport } from '../scripts/extension/seatsurfing_api_transport_v1.mjs';
import { compareContinuationRequests } from '../scripts/extension/compare_seatsurfing_continuation_requests_v1.mjs';
function fixture(attributes = false) {
  const path = '/location/12345678-1234-1234-1234-123456789abc';
  const request = (method, path, json) => ({ method, path, json, body: JSON.stringify(json) });
  const plan = { scope: 'fresh_editor_scalar_edit_without_map_design_or_file_changes', nativeAutomaticReadback: false,
    mapWrite: null, spaceOrImageWrites: [], main: request('PUT', path, { name: 'Area', description: 'Edit description', announcement: 'Notice' }),
    afterMainSuccess: attributes ? [request('POST', path + '/attribute/12345678-1234-1234-1234-123456789def', { value: 'retained' })] : [] };
  const events = [], envelopes = [];
  const headers = { authorization: 'Bearer token', 'content-type': 'application/json' };
  for (const [index, item] of [plan.main, ...plan.afterMainSuccess].entries()) {
    const id = index + 2, at = 100 + index * 10;
    const row = { method: item.method, url: 'http://127.0.0.1:8080' + item.path, body: item.body };
    events.push({ kind: 'request', id, at, ...row }, { kind: 'request_headers', id, headers: structuredClone(headers), at },
      { kind: 'response', id, status: 204, at: at + 1 }, { kind: 'finished', id, at: at + 2 });
    envelopes.push({ ...row, headers: structuredClone(headers), sequence: index + 1, stage: index ? 'attribute' : 'main', outcome: 'http_accepted', status: 204, dispatchedAt: at, completedAt: at + 2 });
  }
  return { accessToken: 'token', native: { plan, afterRequestId: 1, network: { events, pendingRequests: 0, pendingCaptures: 0 }, result: { observation: 'main_response_observed', completePayloadMatches: true, response: { status: 204 } } },
    api: { outcome: 'continuation_observed', loaded: { outcome: 'source_inputs_loaded', acquisition: 'independent_api_gets', envelopes: [] }, plan: structuredClone(plan), execution: { outcome: 'all_http_accepted', retryCount: 0, envelopes } } };
}
test('complete main and ancillary plans match without claiming full qualification', () => {
  for (const attributes of [false, true]) { const value = fixture(attributes), result = compareContinuationRequests(value); assert.equal(result.matchedRequestCount, attributes ? 2 : 1); assert.equal(result.runtimeQualified, false); }
});
test('extra write or read cannot be hidden by endpoint filtering', () => {
  for (const method of ['POST', 'GET']) { const value = fixture(); value.native.network.events.push({ kind: 'request', id: 3, method, url: 'http://127.0.0.1:8080/other' }); assert.throws(() => compareContinuationRequests(value), /Unexpected/); }
});
test('unrelated complete body difference rejects API comparator', () => {
  const value = fixture(); value.api.execution.envelopes[0].body = JSON.stringify({ ...value.api.plan.main.json, announcement: null }); assert.throws(() => compareContinuationRequests(value), /payload differs/);
});
test('missing ancillary response and wrong status cannot pass', () => {
  const value = fixture(true); value.native.network.events = value.native.network.events.filter(e => !(e.kind === 'finished' && e.id === 3)); assert.throws(() => compareContinuationRequests(value), /finished/);
  const wrong = fixture(); wrong.api.execution.envelopes[0].status = 200; assert.throws(() => compareContinuationRequests(wrong));
});
test('actor token or cookie mismatch fails', () => {
  const value = fixture(); value.api.execution.envelopes[0].headers.authorization = 'Bearer other'; assert.throws(() => compareContinuationRequests(value));
  const cookie = fixture(); cookie.native.network.events.find(e => e.kind === 'request_headers').headers.cookie = 'session=other'; assert.throws(() => compareContinuationRequests(cookie), /Cookie/);
});
test('different independently loaded plan fails even if native result flag claims match', () => {
  const value = fixture(); value.api.plan.main.json.name = 'Other'; assert.throws(() => compareContinuationRequests(value), /materialized/);
});
test('unsettled or failed native observation fails', () => {
  const value = fixture(); value.native.network.pendingCaptures = 1; assert.throws(() => compareContinuationRequests(value));
  const failed = fixture(); failed.native.network.events.push({ kind: 'capture_failure' }); assert.throws(() => compareContinuationRequests(failed));
});

test('offline files compare both native branches and bind exact artifact hashes', async () => {
  const { mkdtemp, writeFile, readFile, rm, stat } = await import('node:fs/promises');
  const { tmpdir } = await import('node:os');
  const { join } = await import('node:path');
  const { spawnSync } = await import('node:child_process');
  const { createHash } = await import('node:crypto');
  const directory = await mkdtemp(join(tmpdir(), 'seatsurfing-request-files-'));
  try {
    for (const mismatch of ['none', 'payload', 'transport']) {
      const x = fixture(true);
      const native = structuredClone(x.native);
      if (mismatch === 'payload') native.network.events.find(e => e.kind === 'request').body = '{}';
      const objects = { warm: x.native, native, api: { status: 'api_operation_observed', operation: 'ordinary_continue', result: x.api }, storage: { cookies: [], origins: [{ origin: 'http://127.0.0.1:8080', localStorage: [{ name: 'accessToken', value: 'token' }] }] } };
      const rows = x.api.execution.envelopes.map((request, index) => ({ sequence: index + 1, method: request.method, url: request.url,
        rawHeaders: request.method + ' ' + new URL(request.url).pathname + ' HTTP/1.1\r\nhost: 127.0.0.1:8080\r\nauthorization: Bearer token\r\ncontent-type: application/json\r\nuser-agent: synthetic-api\r\n',
        createdAt: 1, sentAt: 2, bodySent: true, completedAt: 3, status: 204 }));
      objects.api.transport = { failure: null, rows };
      objects.api.transmittedRequests = bindApiTransport(objects.api.transport, x.api.execution.envelopes);
      if (mismatch === 'transport') objects.api.transmittedRequests[0].headers.authorization = 'Bearer changed';
      const paths = [], hashes = {};
      for (const [name, object] of Object.entries(objects)) {
        const path = join(directory, name + '-' + mismatch + '.json'), raw = JSON.stringify(object);
        await writeFile(path, raw, { mode: 0o600 }); paths.push(path); hashes[name] = createHash('sha256').update(raw).digest('hex');
      }
      const output = join(directory, 'result-' + mismatch + '.json');
      const run = spawnSync(process.execPath, [new URL('../scripts/extension/compare_seatsurfing_request_files_v1.mjs', import.meta.url).pathname, ...paths, output], { timeout: 20000 });
      assert.equal(run.status, mismatch !== 'none' ? 1 : 0); assert.equal(run.stdout.length + run.stderr.length, 0);
      const result = JSON.parse(await readFile(output, 'utf8'));
      assert.deepEqual(result.inputHashes, hashes); assert.equal(result.runtimeQualified, false);
      assert.equal(result.status, mismatch !== 'none' ? 'request_comparison_unavailable' : 'both_native_write_plans_match_independent_api');
      if (mismatch === 'none') {
        assert.equal(result.apiTransportBound, true); assert.equal(result.apiTransportCaptureComplete, false);
        const difference = result.headerDifferences.warm[0].differences.find(row => row.field === 'user-agent');
        assert.equal(difference.apiDiagnostic, 'synthetic-api'); assert.equal(difference.sourceRelevanceQualified, false);
      }
      assert.equal((await stat(output)).mode & 0o777, 0o600);
    }
  } finally { await rm(directory, { recursive: true }); }
});
