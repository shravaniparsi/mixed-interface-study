// Page-local request lifetimes, including responses not yet received at teardown.
// No Playwright dependency: EventEmitter/deferred-promise tests exercise races.
export function createResponseCapture({page, contextId, getPhase, readResponse,
  onRequest, onResponse, onError}) {
  const active = new Map();
  let admitted = 0, completed = 0, failures = 0, closed = false, draining = false;
  let timer, resolveDrain, drainPromise, finalRecord;

  function detach() {
    page.off('request', request);
    page.off('response', response);
    page.off('requestfailed', requestFailed);
  }
  function finish(timedOut = false) {
    if (closed) return;
    closed = true;
    clearTimeout(timer);
    detach();
    const outstanding = [...active.values()].map(r => ({...r.meta}));
    if (timedOut) {
      for (const record of active.values()) {
        failures++;
        onError({...record.meta, reason: 'drain_timeout', message: 'Response capture drain deadline exceeded'});
      }
    }
    active.clear();
    finalRecord = {context_id: contextId, admitted, completed, failures,
      timed_out: timedOut, outstanding, complete: failures === 0 && outstanding.length === 0};
    resolveDrain(finalRecord);
  }
  function settle(req, record, error) {
    if (closed || active.get(req) !== record) return;
    if (error) {
      failures++;
      onError({...record.meta, ...error});
    } else completed++;
    active.delete(req);
    if (draining && active.size === 0) finish();
  }
  function request(req) {
    if (closed || !new URL(req.url()).pathname.startsWith('/api/')) return;
    const record = {reading: false, meta: {capture_request_id: `${contextId}:${++admitted}`,
      context_id: contextId, method: req.method(), path: new URL(req.url()).pathname,
      request_phase: getPhase()}};
    active.set(req, record);
    onRequest(record.meta, req);
  }
  function response(res) {
    const req = res.request(), record = active.get(req);
    if (closed || !record || record.reading) return;
    record.reading = true;
    // The request was admitted before awaiting its body. Late response events
    // during drain remain attached to that same page and request-phase metadata.
    void (async () => {
      try {
        const data = await readResponse(res);
        if (closed || active.get(req) !== record) return;
        onResponse(record.meta, res, data);
        settle(req, record);
      } catch (error) {
        settle(req, record, {reason: 'response_body_error', message: error.message});
      }
    })();
  }
  function requestFailed(req) {
    const record = active.get(req);
    if (record) settle(req, record, {reason: 'request_failed',
      message: req.failure()?.errorText || 'API request failed'});
  }
  page.on('request', request);
  page.on('response', response);
  page.on('requestfailed', requestFailed);
  return {
    sealAndDrain({timeoutMs = 5000} = {}) {
      if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) throw new Error('Positive drain timeout required');
      if (drainPromise) return drainPromise;
      drainPromise = new Promise(resolve => {resolveDrain = resolve;});
      draining = true;
      // Continue admitting requests while draining. At zero outstanding work,
      // detach synchronously; callers close this context immediately afterward.
      if (active.size === 0) finish();
      else timer = setTimeout(() => finish(true), timeoutMs);
      return drainPromise;
    },
  };
}
