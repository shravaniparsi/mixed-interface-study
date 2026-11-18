/** Native password login component; NOT runtime-qualified.
 * Returned envelopes and storage contain private fixture credentials/tokens.
 * Starts no browser, changes no app code/storage and performs no API login.
 * Caller must enforce the registered isolated-runtime and process deadline.
 */
import assert from 'node:assert/strict';

export async function nativeSeatsurfingLogin(page, { baseUrl, email, password, organizationId }) {
  for (const value of [email, password, organizationId]) assert.ok(typeof value === 'string' && value.length > 0);
  const base = new URL(baseUrl);
  assert.ok(['http:', 'https:'].includes(base.protocol));
  assert.equal(base.username + base.password, '');
  const loginUrl = new URL('/ui/login/', base);
  loginUrl.searchParams.set('redir', '/ui/admin/locations/');
  const apiUrl = new URL('/auth/login', base).href;
  const deadline = Date.now() + 30000;
  const remaining = () => {
    const timeout = deadline - Date.now();
    assert.ok(timeout > 0, 'Native login observation deadline');
    return timeout;
  };
  let loginRequests = 0;
  const observe = request => {
    if (request.url() === apiUrl && request.method() === 'POST') loginRequests++;
  };
  page.on('request', observe);
  try {
    await page.goto(loginUrl.href, { waitUntil: 'domcontentloaded', timeout: remaining() });
    const form = page.locator('form[name="password-login"]');
    await form.waitFor({ state: 'visible', timeout: remaining() });
    assert.equal(await form.count(), 1);
    const prior = await page.evaluate(() => ({ access: localStorage.getItem('accessToken'), refresh: localStorage.getItem('refreshToken') }));
    assert.equal(prior.access, null);
    assert.equal(prior.refresh, null);
    const emailInput = form.locator('input[type="email"]');
    const passwordInput = form.locator('input[type="password"]');
    const submit = form.locator('button[type="submit"]');
    for (const control of [emailInput, passwordInput, submit]) assert.equal(await control.count(), 1);
    await emailInput.fill(email, { timeout: remaining() });
    await passwordInput.fill(password, { timeout: remaining() });
    assert.equal(await submit.isVisible(), true);
    assert.equal(await submit.isEnabled(), true);
    const [response] = await Promise.all([
      page.waitForResponse(r => r.url() === apiUrl && r.request().method() === 'POST', { timeout: remaining() }),
      submit.click({ timeout: remaining() }),
    ]);
    assert.equal(loginRequests, 1);
    const request = response.request();
    const body = request.postData();
    assert.deepEqual(JSON.parse(body), { email, password, organizationId, code: '' });
    const headers = await request.allHeaders();
    assert.equal(headers['content-type'], 'application/json');
    assert.equal(response.status(), 200);
    const result = await response.json();
    assert.ok(typeof result.accessToken === 'string' && result.accessToken.length > 0);
    assert.ok(typeof result.refreshToken === 'string' && result.refreshToken.length > 0);
    await page.waitForFunction(({ accessToken, refreshToken }) =>
      localStorage.getItem('accessToken') === accessToken &&
      localStorage.getItem('refreshToken') === refreshToken &&
      Number(localStorage.getItem('accessTokenExpiry')) > Date.now(),
    result, { timeout: remaining() });
    await page.waitForURL(new URL('/ui/admin/locations/', base).href, { timeout: remaining(), waitUntil: 'domcontentloaded' });
    assert.equal(loginRequests, 1);
    return { request: { method: 'POST', url: apiUrl, headers, body }, response: result,
      storage: await page.context().storageState(), nativeFormSubmitted: true };
  } finally {
    page.off('request', observe);
  }
}
