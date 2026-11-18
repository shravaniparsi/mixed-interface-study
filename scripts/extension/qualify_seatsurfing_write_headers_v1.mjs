/** Source-scoped observed-header checks for original location JSON writes. */
import assert from 'node:assert/strict';
const metadata = new Set(['accept-language', 'accept-encoding', 'user-agent', 'sec-ch-ua', 'sec-ch-ua-mobile', 'sec-ch-ua-platform', 'sec-fetch-dest', 'sec-fetch-mode', 'sec-fetch-site', 'priority']);
const structural = new Set(['authorization', 'content-type', 'host', 'connection', 'accept', 'content-length', 'origin']);
export function qualifyObservedWriteHeaders({ nativeHeaders, apiHeaders, nativeBody, apiBody, method, path, environment }) {
  assert.equal(environment.CORS_ORIGINS, ''); assert.equal(environment.PUBLIC_SCHEME, 'http');
  assert.equal(environment.RATE_LIMIT, '250'); assert.equal(environment.RATE_LIMIT_PERIOD, '1-M');
  const id = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}';
  assert.ok((method === 'POST' && path === '/location/') || (method === 'PUT' && new RegExp('^/location/' + id + '$', 'i').test(path)) ||
    (method === 'POST' && new RegExp('^/location/' + id + '/attribute/' + id + '$', 'i').test(path)));
  assert.deepEqual(JSON.parse(nativeBody), JSON.parse(apiBody));
  for (const [headers, body] of [[nativeHeaders, nativeBody], [apiHeaders, apiBody]]) {
    for (const [name, value] of Object.entries(headers)) {
      assert.equal(name, name.toLowerCase()); assert.ok(metadata.has(name) || structural.has(name), 'Unmapped observed header: ' + name);
      assert.equal(typeof value, 'string'); assert.ok(value.length <= 16384 && !/[\r\n]/.test(value));
    }
    assert.equal(headers.host, '127.0.0.1:8080'); assert.equal(headers['content-type'], 'application/json');
    assert.match(headers.authorization, /^Bearer \S+$/);
    assert.ok(headers.accept === undefined || headers.accept === '*/*');
    assert.ok(headers.connection === undefined || headers.connection.toLowerCase() === 'keep-alive');
    assert.ok(headers.origin === undefined || headers.origin === 'http://127.0.0.1:8080');
    if (headers['content-length'] !== undefined) assert.equal(headers['content-length'], String(Buffer.byteLength(body)));
    if (headers['sec-fetch-site'] !== undefined) assert.equal(headers['sec-fetch-site'], 'same-origin');
    if (headers['sec-fetch-dest'] !== undefined) assert.equal(headers['sec-fetch-dest'], 'empty');
    if (headers['sec-fetch-mode'] !== undefined) assert.ok(['cors', 'same-origin'].includes(headers['sec-fetch-mode']));
  }
  assert.equal(nativeHeaders.authorization, apiHeaders.authorization);
  const fields = [...new Set([...Object.keys(nativeHeaders), ...Object.keys(apiHeaders)])].sort();
  return { status: 'observed_location_write_headers_follow_source_rules', method, path,
    differences: fields.filter(field => nativeHeaders[field] !== apiHeaders[field]).map(field => ({ field,
      native: nativeHeaders[field] ?? null, apiDiagnostic: apiHeaders[field] ?? null,
      disposition: metadata.has(field) ? 'not_read_by_original_location_write_or_installed_application_middleware' :
        field === 'origin' ? 'same_origin_or_absent_with_empty_original_cors_allowlist' :
        field === 'content-length' ? 'checked_when_observed_diagnostic_absence_not_wire_absence' : 'bounded_structural_header',
    })), apiHeaderCaptureComplete: false, requestBodyWireCaptureComplete: false,
    runtimeTransportCalibrationRequired: true, wholeStudyTransportQualified: false };
}
