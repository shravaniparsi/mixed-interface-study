import test from 'node:test';
import assert from 'node:assert/strict';
import { qualifyObservedWriteHeaders } from '../scripts/extension/qualify_seatsurfing_write_headers_v1.mjs';
function fixture() {
  const common = { host: '127.0.0.1:8080', authorization: 'Bearer token', 'content-type': 'application/json', accept: '*/*' };
  return { nativeHeaders: { ...common, origin: 'http://127.0.0.1:8080', 'user-agent': 'synthetic-browser', 'accept-language': 'en-US', 'sec-fetch-site': 'same-origin', 'content-length': '2' },
    apiHeaders: { ...common, 'user-agent': 'synthetic-node', 'accept-language': '*' }, nativeBody: '{}', apiBody: '{}',
    method: 'PUT', path: '/location/12345678-1234-1234-1234-123456789abc',
    environment: { CORS_ORIGINS: '', PUBLIC_SCHEME: 'http', RATE_LIMIT: '250', RATE_LIMIT_PERIOD: '1-M' } };
}
test('source-scoped metadata differences retained without complete transport claim', () => {
  const result = qualifyObservedWriteHeaders(fixture()); assert.equal(result.wholeStudyTransportQualified, false);
  assert.ok(result.differences.some(row => row.field === 'user-agent')); assert.equal(result.runtimeTransportCalibrationRequired, true);
});
test('cookies forwarding method overrides and unknown headers rejected', () => {
  for (const name of ['cookie', 'x-forwarded-for', 'x-http-method-override', 'content-encoding', 'transfer-encoding', 'x-unknown']) {
    const x = fixture(); x.apiHeaders[name] = 'unexpected'; assert.throws(() => qualifyObservedWriteHeaders(x), /Unmapped/);
  }
});
test('cross-origin host or original token differences rejected', () => {
  for (const [field, value] of [['host', 'other'], ['origin', 'http://other'], ['authorization', 'Bearer other'], ['sec-fetch-site', 'cross-site']]) {
    const x = fixture(); x.apiHeaders[field] = value; assert.throws(() => qualifyObservedWriteHeaders(x));
  }
});
test('body length and complete JSON differences rejected', () => {
  const x = fixture(); x.nativeHeaders['content-length'] = '9'; assert.throws(() => qualifyObservedWriteHeaders(x));
  const y = fixture(); y.apiBody = '{"extra":true}'; assert.throws(() => qualifyObservedWriteHeaders(y));
});
test('scope cannot expand to other routes or altered CORS configuration', () => {
  const x = fixture(); x.path = '/user/me'; assert.throws(() => qualifyObservedWriteHeaders(x));
  const y = fixture(); y.environment.CORS_ORIGINS = '*'; assert.throws(() => qualifyObservedWriteHeaders(y));
});
