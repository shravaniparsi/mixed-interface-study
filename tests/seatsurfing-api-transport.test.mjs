import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { observeSeatsurfingApiTransport, bindApiTransport } from '../scripts/extension/seatsurfing_api_transport_v1.mjs';
test('passive headers match a real synthetic loopback fetch without changing it', async () => {
  let received;
  const server = createServer((request, response) => { received = request.headers; request.resume(); request.on('end', () => { response.writeHead(204); response.end(); }); });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  const origin = 'http://127.0.0.1:' + server.address().port;
  const observer = observeSeatsurfingApiTransport(origin);
  try {
    const request = { method: 'POST', url: origin + '/synthetic', headers: { authorization: 'Bearer synthetic', 'content-type': 'application/json' }, body: '{"fixture":true}' };
    const response = await fetch(request.url, { method: request.method, headers: request.headers, body: request.body, redirect: 'manual' }); await response.text();
    const transport = observer.finish(); const matched = bindApiTransport(transport, [{ request, response: { status: 204 } }]);
    for (const [name, value] of Object.entries(matched[0].headers)) assert.equal(value, received[name]);
    const absent = Object.keys(received).filter(name => !Object.hasOwn(matched[0].headers, name));
    assert.ok(absent.every(name => name === 'content-length'));
    assert.equal(received['content-length'], String(Buffer.byteLength(request.body)));
    assert.equal(matched[0].headerCaptureCompletenessEstablished, false);
    assert.equal(matched[0].bodyBytesIndependentlyObserved, false);
    const changed = structuredClone(transport); changed.rows[0].rawHeaders = changed.rows[0].rawHeaders.replace('Bearer synthetic', 'Bearer other');
    assert.throws(() => bindApiTransport(changed, [{ request, response: { status: 204 } }]));
    assert.throws(() => bindApiTransport(transport, []));
  } finally { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); }
});
test('missing diagnostic events cannot qualify declared requests', () => {
  const observer = observeSeatsurfingApiTransport(); const trace = observer.finish();
  assert.throws(() => bindApiTransport(trace, [{ method: 'GET', url: 'http://127.0.0.1:8080/user/me' }]), /Missing/);
});

test('receiver calibration covers GET POST PUT and UTF-8 body framing', async () => {
  const { calibrateApiTransport } = await import('../scripts/extension/calibrate_seatsurfing_api_transport_v1.mjs');
  const result = await calibrateApiTransport();
  assert.equal(result.status, 'synthetic_receiver_transport_calibrated');
  assert.deepEqual(result.received.map(row => row.method), ['GET', 'POST', 'PUT']);
  assert.equal(result.received[2].body, '{"synthetic":"café"}');
  assert.equal(result.applicationRequestsExecuted, 0); assert.equal(result.studyTransportQualified, false);
});
