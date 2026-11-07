import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {createResponseCapture} from '../scripts/petclinic_response_capture.mjs';

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => {resolve = yes; reject = no;});
  return {promise, resolve, reject};
}
function fixture(contextId = 'page1') {
  const page = new EventEmitter(), events = [], bodies = new Map();
  let phase = 'producer';
  const capture = createResponseCapture({page, contextId, getPhase: () => phase,
    readResponse: res => bodies.get(res.request()).promise,
    onRequest: meta => events.push({type: 'request', ...meta}),
    onResponse: (meta, res, data) => events.push({type: 'response', ...meta, data}),
    onError: error => events.push({type: 'error', ...error})});
  function admit(path = '/petclinic/api/articles') {
    const req = {url: () => 'http://127.0.0.1:18765' + path, method: () => 'GET',
      failure: () => ({errorText: 'net::ERR_FAILED'})};
    const body = deferred(); bodies.set(req, body); page.emit('request', req);
    return {req, body, respond: () => page.emit('response', {request: () => req})};
  }
  return {page, events, capture, admit, setPhase: x => {phase = x;}};
}
const tick = () => new Promise(resolve => setImmediate(resolve));

test('drain waits for an admitted request whose response has not arrived', async () => {
  const f = fixture(), r = f.admit();
  let closed = false;
  const drain = f.capture.sealAndDrain().then(x => {closed = true; return x;});
  await tick(); assert.equal(closed, false);
  r.respond(); await tick(); assert.equal(closed, false);
  r.body.resolve({ok: true});
  const result = await drain;
  assert.equal(result.complete, true); assert.equal(result.completed, 1);
  assert.equal(f.events.filter(x => x.type === 'response').length, 1);
});

test('requests admitted while draining are included until all bodies settle', async () => {
  const f = fixture(), first = f.admit(); first.respond();
  const drain = f.capture.sealAndDrain();
  const second = f.admit('/petclinic/api/tags'); second.respond();
  let done = false; drain.then(() => {done = true;});
  first.body.resolve({}); await tick(); assert.equal(done, false);
  second.body.resolve({});
  const result = await drain;
  assert.equal(result.admitted, 2); assert.equal(result.completed, 2); assert.equal(result.complete, true);
});

test('response metadata preserves admission phase across asynchronous phase changes', async () => {
  const f = fixture(), r = f.admit(); f.setPhase('oracle'); r.respond(); r.body.resolve({});
  const result = await f.capture.sealAndDrain();
  assert.equal(result.complete, true);
  assert.equal(f.events.at(-1).request_phase, 'producer');
  assert.equal(f.events.at(-1).capture_request_id, 'page1:1');
});

test('body failure is retained even when it happens before drain starts', async () => {
  const f = fixture(), r = f.admit(); r.respond(); r.body.reject(new Error('closed unexpectedly'));
  await tick(); const result = await f.capture.sealAndDrain();
  assert.equal(result.complete, false); assert.equal(result.failures, 1);
  assert.equal(f.events.at(-1).reason, 'response_body_error');
  assert.equal(f.events.at(-1).path, '/petclinic/api/articles');
});

test('network failure settles the request and invalidates capture', async () => {
  const f = fixture(), r = f.admit(); f.page.emit('requestfailed', r.req);
  const result = await f.capture.sealAndDrain();
  assert.equal(result.complete, false); assert.equal(result.failures, 1);
  assert.equal(result.outstanding.length, 0);
  assert.equal(f.events.at(-1).reason, 'request_failed');
});

test('stuck request reaches a bounded deadline with identifiable incomplete evidence', async () => {
  const f = fixture(); f.admit();
  const result = await f.capture.sealAndDrain({timeoutMs: 10});
  assert.equal(result.complete, false); assert.equal(result.timed_out, true);
  assert.equal(result.outstanding[0].capture_request_id, 'page1:1');
  assert.equal(f.events.at(-1).reason, 'drain_timeout');
  for (const name of ['request', 'response', 'requestfailed']) assert.equal(f.page.listenerCount(name), 0);
});

test('late body completion after deadline cannot append evidence or affect another page', async () => {
  const first = fixture('old'), r = first.admit(); r.respond();
  await first.capture.sealAndDrain({timeoutMs: 10});
  const size = first.events.length, second = fixture('new'), next = second.admit(); next.respond();
  r.body.resolve({late: true}); next.body.resolve({current: true});
  const result = await second.capture.sealAndDrain(); await tick();
  assert.equal(first.events.length, size); assert.equal(result.complete, true);
  assert.equal(second.events.at(-1).capture_request_id, 'new:1');
});

test('drain is idempotent and detaches only its own listeners', async () => {
  const f = fixture(); let other = 0;
  f.page.on('request', () => {other++;});
  const one = f.capture.sealAndDrain(), two = f.capture.sealAndDrain();
  assert.equal(one, two); assert.equal((await one).complete, true);
  f.admit(); assert.equal(other, 1); assert.equal(f.events.length, 0);
  assert.equal(f.page.listenerCount('request'), 1);
});

test('non-API assets do not enter capture, and invalid deadlines are rejected', async () => {
  const f = fixture(); f.admit('/assets/app.js');
  assert.throws(() => f.capture.sealAndDrain({timeoutMs: 0}), /Positive/);
  assert.equal((await f.capture.sealAndDrain()).admitted, 0);
});
