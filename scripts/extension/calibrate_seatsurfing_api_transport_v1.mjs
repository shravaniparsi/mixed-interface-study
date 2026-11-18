/** Synthetic loopback receiver calibration; never contacts the application. */
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { observeSeatsurfingApiTransport, bindApiTransport } from './seatsurfing_api_transport_v1.mjs';
export async function calibrateApiTransport() {
  const received = [];
  const server = createServer((request, response) => {
    const chunks = []; let bytes = 0;
    request.on('data', chunk => { bytes += chunk.length; if (bytes > 4096) request.destroy(); else chunks.push(chunk); });
    request.on('end', () => {
      received.push({ method: request.method, path: request.url, headers: request.headers, body: Buffer.concat(chunks).toString('utf8') });
      response.writeHead(request.method === 'GET' ? 200 : request.method === 'POST' ? 201 : 204, { 'content-type': 'application/json' });
      response.end(request.method === 'GET' ? '{"synthetic":true}' : undefined);
    });
  });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  const origin = 'http://127.0.0.1:' + server.address().port;
  const observer = observeSeatsurfingApiTransport(origin), envelopes = [];
  let finished = false;
  try {
    for (const [method, path, body] of [['GET', '/read', undefined], ['POST', '/create', '{"synthetic":"ordinary"}'], ['PUT', '/update', '{"synthetic":"café"}']]) {
      const headers = { authorization: 'Bearer synthetic-calibration' };
      if (body !== undefined) headers['content-type'] = 'application/json';
      const request = { method, url: origin + path, headers, ...(body === undefined ? {} : { body }) };
      const response = await fetch(request.url, { method, headers, body, redirect: 'manual', signal: AbortSignal.timeout(5000) });
      await response.text(); envelopes.push({ request, response: { status: response.status } });
    }
    const transport = observer.finish(); finished = true;
    const mapped = bindApiTransport(transport, envelopes); assert.equal(received.length, 3);
    const gaps = mapped.map((row, index) => {
      const actual = received[index], intended = envelopes[index].request;
      assert.equal(actual.method, intended.method); assert.equal(actual.path, new URL(intended.url).pathname);
      assert.equal(actual.body, intended.body ?? '');
      for (const [name, value] of Object.entries(row.headers)) assert.equal(value, actual.headers[name]);
      const unobserved = Object.keys(actual.headers).filter(name => !Object.hasOwn(row.headers, name));
      assert.ok(unobserved.every(name => name === 'content-length'), 'Unmapped receiver-only header');
      if (intended.body !== undefined) assert.equal(actual.headers['content-length'], String(Buffer.byteLength(intended.body)));
      return { method: actual.method, path: actual.path, unobservedHeaderNames: unobserved };
    });
    return { status: 'synthetic_receiver_transport_calibrated', nodeVersion: process.version,
      undiciVersion: process.versions.undici ?? null, received, transport, gaps,
      applicationRequestsExecuted: 0, studyTransportQualified: false };
  } finally {
    if (!finished) observer.finish();
    server.closeAllConnections(); await new Promise(resolve => server.close(resolve));
  }
}
if (process.argv[1]?.endsWith('/calibrate_seatsurfing_api_transport_v1.mjs')) {
  assert.equal(process.version, 'v24.18.1');
  const deadline = setTimeout(() => process.exit(124), 20000);
  try { process.stdout.write(JSON.stringify(await calibrateApiTransport())); }
  catch { process.stderr.write('Synthetic transport calibration failed\n'); process.exitCode = 1; }
  finally { clearTimeout(deadline); }
}
