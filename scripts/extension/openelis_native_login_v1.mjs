/** Original form login only; caller supplies a registered isolated deployment.
 * Returned request/session/storage objects are private evidence and may contain
 * credentials, CSRF values and session cookies. No browser is launched here.
 */
import assert from 'node:assert/strict';

export async function nativeOpenElisLogin(page, { frontendUrl, backendBaseUrl, loginName, password }) {
  const loginUrl = backendBaseUrl + '/ValidateLogin?apiCall=true';
  const sessionUrl = backendBaseUrl + '/session';
  assert.equal(typeof loginName, 'string');
  assert.equal(typeof password, 'string');
  await page.goto(frontendUrl, { waitUntil: 'domcontentloaded' });
  const user = page.locator('#loginName');
  await user.waitFor({ state: 'visible' });
  assert.equal(await user.count(), 1);
  await user.fill(loginName);
  await page.locator('#password').fill(password);
  const submit = page.locator('[data-cy="loginButton"]');
  assert.equal(await submit.count(), 1);
  assert.equal(await submit.isVisible(), true);
  assert.equal(await submit.isEnabled(), true);
  const responsePromise = page.waitForResponse((r) => r.url() === loginUrl && r.request().method() === 'POST');
  const navigated = page.waitForEvent('framenavigated', { predicate: (frame) =>
    frame === page.mainFrame() && frame.url() === new URL('/', frontendUrl).href });
  await Promise.all([navigated, submit.click()]);
  const response = await responsePromise;
  const request = response.request();
  const headers = await request.allHeaders();
  assert.equal(headers['content-type'], 'application/x-www-form-urlencoded');
  const fields = [...new URLSearchParams(request.postData()).entries()].sort(([a], [b]) => a.localeCompare(b));
  assert.deepEqual(fields, [['loginName', loginName], ['password', password]]);
  assert.equal(response.status(), 200);
  assert.deepEqual(await response.json(), { success: true });
  // Original login redirects by assigning window.location.href; verify the
  // authenticated session after that navigation, without changing token type.
  await page.waitForLoadState('domcontentloaded');
  const sessionResponse = await page.context().request.get(sessionUrl);
  assert.equal(sessionResponse.status(), 200);
  const session = await sessionResponse.json();
  assert.equal(session.authenticated, true);
  assert.equal(session.loginName, loginName);
  return { request: { method: 'POST', url: loginUrl, headers, body: request.postData() },
    session, storage: await page.context().storageState() };
}
