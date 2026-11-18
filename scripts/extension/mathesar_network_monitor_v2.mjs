/** Final permitted infrastructure correction: observe failed metadata traffic.
 * No interception, response fabrication, cache change or outbound permission.
 */
const origin = 'http://127.0.0.1:8000';
const releaseUrl = 'https://api.github.com/repos/centerofci/mathesar/releases/tags/0.12.0';

export function monitorLocalRequests(page) {
  const external = [];
  const pageErrors = [];
  const requests = new Map();
  page.on('request', (request) => {
    const url = request.url();
    if (!/^https?:/.test(url) || new URL(url).origin === origin) return;
    const parsed = new URL(url);
    const body = request.postDataBuffer();
    const row = {
      origin: parsed.origin, path: parsed.pathname,
      exact_registered_url: url === releaseUrl,
      method: request.method(), body_bytes: body?.length ?? 0,
      response_status: null, finished: false, failed: false, failure_text: null,
    };
    requests.set(request, row);
    external.push(row);
  });
  page.on('response', (response) => {
    const row = requests.get(response.request());
    if (row) row.response_status = response.status();
  });
  page.on('requestfinished', (request) => {
    const row = requests.get(request);
    if (row) row.finished = true;
  });
  page.on('requestfailed', (request) => {
    const row = requests.get(request);
    if (row) {
      row.failed = true;
      row.failure_text = request.failure()?.errorText ?? null;
    }
  });
  page.on('websocket', (socket) => {
    const parsed = new URL(socket.url());
    // WebSockets were not needed/qualified by v1. Do not silently add one.
    external.push({ origin: parsed.origin, path: parsed.pathname, kind: 'unqualified_websocket' });
  });
  page.on('pageerror', (error) => pageErrors.push(error.name));
  function verifySettled() {
    if (pageErrors.length) throw new Error('Unexpected browser exception');
    for (const row of external) {
      if (row.exact_registered_url !== true || row.method !== 'GET' || row.body_bytes !== 0
        || row.response_status !== null || row.finished !== false || row.failed !== true
        || typeof row.failure_text !== 'string' || !row.failure_text.startsWith('net::ERR_')) {
        throw new Error('External request is not a verified failed registered metadata GET');
      }
    }
  }
  return { external, pageErrors, verifySettled, async verify() {
    const deadline = Date.now() + 5000;
    while ([...requests.values()].some((row) => !row.failed && !row.finished && row.response_status === null)
      && Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
    verifySettled();
  } };
}
