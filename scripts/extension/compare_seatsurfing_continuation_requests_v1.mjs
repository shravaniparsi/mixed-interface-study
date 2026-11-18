/** Complete main/ancillary request comparison; no request execution. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
const origin = 'http://127.0.0.1:8080';
const sha = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
function single(events, kind, id) {
  const matches = events.filter(event => event.kind === kind && event.id === id);
  assert.equal(matches.length, 1, 'Missing or duplicate ' + kind + ' evidence');
  return matches[0];
}
function expectedRequests(plan) {
  assert.equal(plan.scope, 'fresh_editor_scalar_edit_without_map_design_or_file_changes');
  assert.equal(plan.nativeAutomaticReadback, false);
  assert.equal(plan.mapWrite, null); assert.deepEqual(plan.spaceOrImageWrites, []);
  assert.equal(plan.main.method, 'PUT');
  assert.match(plan.main.path, /^\/location\/[0-9a-f-]{36}$/i);
  const requests = [plan.main, ...plan.afterMainSuccess];
  for (const [index, request] of requests.entries()) {
    assert.equal(request.body, JSON.stringify(request.json));
    assert.equal(new URL(request.path, origin).origin, origin);
    if (index) {
      assert.equal(request.method, 'POST');
      assert.match(request.path.slice(plan.main.path.length), /^\/attribute\/[0-9a-f-]{36}$/i);
      assert.ok(request.path.startsWith(plan.main.path));
    }
  }
  return requests;
}
function compareRequest(actual, expected, accessToken) {
  assert.equal(actual.method, expected.method);
  assert.equal(actual.url, origin + expected.path);
  assert.equal(actual.headers.authorization, 'Bearer ' + accessToken);
  assert.equal(actual.headers['content-type'], 'application/json');
  assert.equal(actual.headers.cookie, undefined, 'Cookie-bearing requests remain unqualified');
  assert.deepEqual(JSON.parse(actual.body), expected.json, 'Complete request payload differs');
}

export function qualifyNativeContinuationRequests({ plan, events, afterRequestId, accessToken }) {
  assert.ok(Number.isSafeInteger(afterRequestId) && afterRequestId >= 0);
  assert.ok(Array.isArray(events) && events.length <= 5000);
  assert.equal(events.some(event => ['capture_failure', 'request_failed'].includes(event.kind)), false);
  const expected = expectedRequests(plan);
  const requests = events.filter(event => event.kind === 'request' && event.id > afterRequestId);
  // Original scalar edit has no navigation or automatic reload. Preserve and
  // reject every extra request instead of filtering to the expected endpoint.
  assert.equal(requests.length, expected.length, 'Unexpected or missing continuation request');
  assert.equal(new Set(requests.map(event => event.id)).size, requests.length);
  let mainResponseAt;
  const matched = requests.map((request, index) => {
    const headers = single(events, 'request_headers', request.id).headers;
    const response = single(events, 'response', request.id);
    const finished = single(events, 'finished', request.id);
    compareRequest({ ...request, headers }, expected[index], accessToken);
    assert.ok(Number.isFinite(request.at) && Number.isFinite(response.at) && Number.isFinite(finished.at));
    assert.ok(response.at >= request.at && finished.at >= request.at);
    assert.equal(response.status, 204, 'Original ordinary write must return 204');
    if (index === 0) mainResponseAt = response.at;
    // Response-body capture is asynchronous; request IDs establish dispatch
    // order, while the native main response helper verifies the response gate.
    return { requestId: request.id, request, headers, response, finished };
  });
  return { status: 'native_complete_write_plan_matches', matched, mainResponseObservedAt: mainResponseAt,
    planSha256: sha(plan), networkSha256: sha(events), afterRequestId,
    allObservedRequestsIncluded: true, transportHeadersQualified: false, persistenceEstablished: false, runtimeQualified: false };
}

export function compareContinuationRequests({ native, api, accessToken }) {
  const match = qualifyNativeContinuationRequests({ plan: native.plan, events: native.network.events,
    afterRequestId: native.afterRequestId, accessToken });
  assert.equal(native.network.pendingRequests, 0); assert.equal(native.network.pendingCaptures, 0);
  assert.equal(native.result.observation, 'main_response_observed');
  assert.equal(native.result.completePayloadMatches, true); assert.equal(native.result.response.status, 204);
  assert.equal(api.outcome, 'continuation_observed');
  assert.equal(api.loaded.outcome, 'source_inputs_loaded');
  assert.equal(api.loaded.acquisition, 'independent_api_gets');
  assert.deepEqual(api.plan, native.plan, 'Independently materialized complete plan differs');
  assert.equal(api.execution.outcome, 'all_http_accepted'); assert.equal(api.execution.retryCount, 0);
  const expected = expectedRequests(api.plan);
  assert.equal(api.execution.envelopes.length, expected.length);
  for (const [index, row] of api.execution.envelopes.entries()) {
    assert.equal(row.sequence, index + 1); assert.equal(row.stage, index ? 'attribute' : 'main');
    assert.equal(row.outcome, 'http_accepted'); assert.equal(row.status, 204);
    assert.ok(Number.isFinite(row.completedAt) && row.completedAt >= row.dispatchedAt);
    compareRequest(row, expected[index], accessToken);
  }
  return { status: 'native_and_independent_api_complete_write_plans_match', native: match,
    apiExecutionSha256: sha(api.execution), matchedRequestCount: expected.length,
    transportHeadersQualified: false, actorContinuityEstablished: false,
    startingStateEqualityEstablished: false, persistenceEstablished: false, runtimeQualified: false };
}
