/** Passive PRIVATE Undici diagnostics; never modifies or dispatches a request. */
import assert from 'node:assert/strict';
import diagnostics from 'node:diagnostics_channel';
export function observeSeatsurfingApiTransport(origin = 'http://127.0.0.1:8080') {
  const rows = [], identities = new WeakMap(), subscriptions = [];
  let failure = null, bytes = 0, disposed = false;
  function subscribe(name, fn) {
    const listener = message => {
      if (failure || disposed) return;
      try { fn(message); } catch (error) { failure = error.message; }
    };
    diagnostics.channel(name).subscribe(listener); subscriptions.push([name, listener]);
  }
  const rowFor = request => { const row = identities.get(request); assert.ok(row, 'Missing transport request creation'); return row; };
  subscribe('undici:request:create', ({ request }) => {
    assert.ok(rows.length < 128, 'Transport request bound'); assert.equal(identities.has(request), false);
    assert.equal(String(request.origin), origin, 'Unregistered transport origin');
    const row = { sequence: rows.length + 1, method: request.method, url: origin + request.path, createdAt: Date.now() };
    rows.push(row); identities.set(request, row);
  });
  subscribe('undici:client:sendHeaders', ({ request, headers }) => {
    const row = rowFor(request); assert.equal(row.rawHeaders, undefined, 'Repeated wire dispatch');
    assert.equal(typeof headers, 'string'); bytes += Buffer.byteLength(headers);
    assert.ok(Buffer.byteLength(headers) <= 16384 && bytes <= 1048576, 'Transport header bound');
    row.rawHeaders = headers; row.sentAt = Date.now();
  });
  subscribe('undici:request:bodySent', ({ request }) => { const row = rowFor(request); assert.equal(row.bodySent, undefined); row.bodySent = true; });
  subscribe('undici:request:headers', ({ request, response }) => { const row = rowFor(request); assert.equal(row.status, undefined); row.status = response.statusCode; });
  subscribe('undici:request:trailers', ({ request }) => { const row = rowFor(request); assert.equal(row.completedAt, undefined); row.completedAt = Date.now(); });
  subscribe('undici:request:error', ({ request, error }) => { rowFor(request).errorType = error.name; throw new Error('Transport request failed'); });
  return { finish() {
    assert.equal(disposed, false); disposed = true;
    for (const [name, listener] of subscriptions) diagnostics.channel(name).unsubscribe(listener);
    return structuredClone({ rows, failure, headerBytes: bytes, observation: 'passive_undici_diagnostics', runtimeQualified: false });
  } };
}

export function bindApiTransport(transport, envelopes) {
  assert.equal(transport.failure, null);
  assert.ok(envelopes.length > 0); assert.equal(transport.rows.length, envelopes.length, 'Missing or additional actual API requests');
  return transport.rows.map((row, index) => {
    const envelope = envelopes[index], request = envelope.request ?? envelope, response = envelope.response ?? envelope;
    assert.equal(row.sequence, index + 1); assert.equal(row.method, request.method); assert.equal(row.url, request.url);
    assert.equal(row.status, response.status); assert.equal(row.bodySent, true);
    assert.ok(Number.isFinite(row.completedAt) && row.completedAt >= row.sentAt);
    const lines = row.rawHeaders.split('\r\n');
    const url = new URL(row.url); assert.equal(lines.shift(), row.method + ' ' + url.pathname + url.search + ' HTTP/1.1');
    const headers = {};
    for (const line of lines) {
      if (!line) continue;
      const split = line.indexOf(':'); assert.ok(split > 0, 'Malformed transmitted header');
      const name = line.slice(0, split).toLowerCase(), value = line.slice(split + 1).trim();
      assert.equal(Object.hasOwn(headers, name), false, 'Duplicate transmitted header'); headers[name] = value;
    }
    assert.equal(headers.host, url.host);
    for (const [name, value] of Object.entries(request.headers)) assert.equal(headers[name.toLowerCase()], value);
    assert.equal(headers.cookie, undefined, 'Cookie transport is unqualified');
    assert.equal(headers['transfer-encoding'], undefined, 'Chunked request transport is unqualified');
    if (request.body !== undefined && headers['content-length'] !== undefined) assert.equal(headers['content-length'], String(Buffer.byteLength(request.body)));
    return { ...row, headers, suppliedHeadersMatch: true, headerCaptureCompletenessEstablished: false,
      contentLengthObserved: headers['content-length'] !== undefined, bodyBytesIndependentlyObserved: false };
  });
}
