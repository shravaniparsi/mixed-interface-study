/** Offline source-scoped write transport gate; no application requests. */
import assert from 'node:assert/strict';
import { bindApiTransport } from './seatsurfing_api_transport_v1.mjs';
import { qualifyObservedWriteHeaders } from './qualify_seatsurfing_write_headers_v1.mjs';
export function verifyWriteTransport(bundle) {
  const { calibration, environment, rateBudgets, comparisons, producerNative, producerApi, continuationApi } = bundle;
  assert.equal(calibration.status, 'synthetic_receiver_transport_calibrated'); assert.equal(calibration.nodeVersion, 'v24.18.1');
  assert.ok(typeof calibration.undiciVersion === 'string' && calibration.undiciVersion.length > 0);
  assert.equal(calibration.applicationRequestsExecuted, 0); assert.equal(calibration.received.length, 3);
  assert.deepEqual(calibration.received.map(row => row.method), ['GET', 'POST', 'PUT']);
  assert.ok(calibration.gaps.length === 3 && calibration.gaps.every(row => row.unobservedHeaderNames.every(name => name === 'content-length')));
  assert.equal(calibration.transport.failure, null); assert.equal(calibration.transport.rows.length, 3);
  const examples = [['GET', '/read', undefined, 200], ['POST', '/create', '{"synthetic":"ordinary"}', 201], ['PUT', '/update', '{"synthetic":"café"}', 204]];
  const calibrationEnvelopes = examples.map(([method, path, body, status], index) => {
    const url = new URL(calibration.transport.rows[index].url); assert.equal(url.hostname, '127.0.0.1'); assert.equal(url.protocol, 'http:'); assert.equal(url.pathname, path);
    const headers = { authorization: 'Bearer synthetic-calibration', ...(body === undefined ? {} : { 'content-type': 'application/json' }) };
    return { request: { method, url: url.href, headers, ...(body === undefined ? {} : { body }) }, response: { status } };
  });
  const calibrated = bindApiTransport(calibration.transport, calibrationEnvelopes);
  calibrated.forEach((row, index) => {
    const actual = calibration.received[index], intended = calibrationEnvelopes[index].request;
    assert.equal(actual.method, intended.method); assert.equal(actual.path, new URL(intended.url).pathname); assert.equal(actual.body, intended.body ?? '');
    for (const [name, value] of Object.entries(row.headers)) assert.equal(actual.headers[name], value);
    const missing = Object.keys(actual.headers).filter(name => !Object.hasOwn(row.headers, name));
    assert.ok(missing.every(name => name === 'content-length')); assert.deepEqual(missing, calibration.gaps[index].unobservedHeaderNames);
    if (intended.body !== undefined) assert.equal(actual.headers['content-length'], String(Buffer.byteLength(intended.body)));
  });
  assert.equal(rateBudgets.status, 'ordinary_fixture_stopped_rate_budget_verified');
  for (const branch of ['warm', 'native', 'api']) {
    const budget = rateBudgets.budgets[branch]; assert.equal(budget.status, 'observed_requests_below_original_rate_limit');
    assert.ok(budget.whole_process_authenticated_requests <= 200); assert.equal(budget.original_limit, 250); assert.equal(budget.original_period, '1-M');
  }
  assert.equal(comparisons.status, 'both_native_write_plans_match_independent_api'); assert.equal(comparisons.apiTransportBound, true);
  assert.equal(producerApi.operation, 'ordinary_create'); assert.equal(producerApi.status, 'api_operation_observed');
  const producerRows = bindApiTransport(producerApi.transport, [producerApi.result.envelope]); assert.deepEqual(producerRows, producerApi.transmittedRequests);
  const production = qualifyObservedWriteHeaders({ nativeHeaders: producerNative.request.headers, apiHeaders: producerRows[0].headers,
    nativeBody: producerNative.request.body, apiBody: producerApi.result.envelope.request.body, method: 'POST', path: '/location/', environment });
  assert.equal(continuationApi.status, 'api_operation_observed'); assert.equal(continuationApi.operation, 'ordinary_continue');
  const result = continuationApi.result;
  const all = bindApiTransport(continuationApi.transport, [...result.loaded.envelopes, ...result.execution.envelopes]);
  assert.deepEqual(all, continuationApi.transmittedRequests); const writes = all.slice(result.loaded.envelopes.length);
  const branches = {};
  for (const branch of ['warm', 'restoredNative']) {
    const native = comparisons[branch].native.matched; assert.equal(native.length, writes.length);
    branches[branch] = native.map((row, index) => {
      assert.equal(row.request.url, writes[index].url); assert.equal(row.request.method, writes[index].method);
      return qualifyObservedWriteHeaders({ nativeHeaders: row.headers, apiHeaders: writes[index].headers,
        nativeBody: row.request.body, apiBody: result.execution.envelopes[index].body,
        method: row.request.method, path: new URL(row.request.url).pathname, environment });
    });
  }
  return { status: 'observed_write_transport_checks_pass', production, branches,
    calibrationNodeVersion: calibration.nodeVersion, calibrationUndiciVersion: calibration.undiciVersion,
    apiHeaderCaptureComplete: false, sourceScope: 'original_location_json_writes',
    allClientInventoryRequired: true, applicationQualified: false };
}
