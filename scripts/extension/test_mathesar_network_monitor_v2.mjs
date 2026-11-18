import { EventEmitter } from 'node:events';
import assert from 'node:assert/strict';
import test from 'node:test';
import { monitorLocalRequests } from './mathesar_network_monitor_v2.mjs';

const url = 'https://api.github.com/repos/centerofci/mathesar/releases/tags/0.12.0';
function request(address = url, method = 'GET', body = null) {
  return { url: () => address, method: () => method,
    postDataBuffer: () => body, failure: () => ({ errorText: 'net::ERR_NAME_NOT_RESOLVED' }) };
}
function fixture() {
  const page = new EventEmitter();
  return { page, monitor: monitorLocalRequests(page) };
}

test('failed exact metadata GET is retained and accepted alongside local RPC', async () => {
  const { page, monitor } = fixture();
  const remote = request();
  page.emit('request', request('http://127.0.0.1:8000/api/rpc/v0/', 'POST', Buffer.from('{}')));
  page.emit('request', remote);
  assert.throws(() => monitor.verifySettled());
  page.emit('requestfailed', remote);
  await monitor.verify();
  assert.equal(monitor.external.length, 1);
  assert.equal(monitor.external[0].failure_text, 'net::ERR_NAME_NOT_RESOLVED');
});

for (const [name, req] of [
  ['query', request(url + '?token=private')],
  ['other tag', request(url.replace('0.12.0', '0.12.1'))],
  ['other endpoint', request(url.replace('/tags/0.12.0', '/latest'))],
  ['POST', request(url, 'POST')],
  ['GET body', request(url, 'GET', Buffer.from('x'))],
  ['other host', request(url.replace('api.github.com', 'example.com'))],
]) {
  test(`reject failed ${name}`, () => {
    const { page, monitor } = fixture();
    page.emit('request', req); page.emit('requestfailed', req);
    assert.throws(() => monitor.verifySettled());
  });
}

test('reject any external HTTP response even if later marked failed', () => {
  const { page, monitor } = fixture(); const req = request();
  page.emit('request', req);
  page.emit('response', { request: () => req, status: () => 503 });
  page.emit('requestfailed', req);
  assert.throws(() => monitor.verifySettled());
});

test('reject completed, unresolved and WebSocket traffic', () => {
  for (const event of ['requestfinished', 'unresolved', 'websocket']) {
    const { page, monitor } = fixture(); const req = request();
    if (event === 'websocket') page.emit('websocket', { url: () => 'ws://127.0.0.1:8000/ws' });
    else { page.emit('request', req); if (event !== 'unresolved') page.emit(event, req); }
    assert.throws(() => monitor.verifySettled());
  }
});

test('browser exceptions remain failures', () => {
  const { page, monitor } = fixture(); page.emit('pageerror', new Error('failure'));
  assert.throws(() => monitor.verifySettled());
});
