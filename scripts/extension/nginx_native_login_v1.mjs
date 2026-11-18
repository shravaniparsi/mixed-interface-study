/** Original native form login. All returned envelopes/storage are PRIVATE:
 * they contain the isolated user's password and bearer token. No browser starts
 * here. Server-side identity/role and restored-state checks remain separate.
 */
import assert from 'node:assert/strict';

export async function nativeNginxLogin(page, { baseUrl, identity, secret }) {
  assert.equal(typeof identity, 'string');
  assert.equal(typeof secret, 'string');
  const tokenUrl = new URL('/api/tokens', baseUrl).href;
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });
  const email = page.locator('input[name="email"][type="email"]');
  await email.waitFor({ state: 'visible' });
  assert.equal(await email.count(), 1);
  const prior = await page.evaluate(() => localStorage.getItem('authentications'));
  assert.ok(prior === null || (Array.isArray(JSON.parse(prior)) && JSON.parse(prior).length === 0));
  const password = page.locator('input[name="password"][type="password"]');
  assert.equal(await password.count(), 1);
  await email.fill(identity);
  await password.fill(secret);
  const form = page.locator('form').filter({ has: email });
  assert.equal(await form.count(), 1);
  const submit = form.locator('button[type="submit"]');
  assert.equal(await submit.count(), 1);
  assert.equal(await submit.isVisible(), true);
  assert.equal(await submit.isEnabled(), true);
  const [response] = await Promise.all([
    page.waitForResponse((r) => r.url() === tokenUrl && r.request().method() === 'POST'),
    submit.click(),
  ]);
  const request = response.request();
  const headers = await request.allHeaders();
  assert.equal(headers['content-type'], 'application/json');
  assert.deepEqual(JSON.parse(request.postData()), { identity, secret });
  assert.equal(response.status(), 200);
  const result = await response.json();
  assert.deepEqual(Object.keys(result).sort(), ['expires', 'token']);
  assert.equal(typeof result.token, 'string');
  assert.ok(result.token.length > 0);
  assert.equal(typeof result.expires, 'string');
  assert.ok(Number.isFinite(Date.parse(result.expires)));
  // Observe the original AuthContext/AuthStore update; never set a token.
  await page.waitForFunction(({ token, expires }) => {
    const raw = localStorage.getItem('authentications');
    if (raw === null) return false;
    const stored = JSON.parse(raw);
    return Array.isArray(stored) && stored.length === 1 &&
      stored[0].token === token && stored[0].expires === expires;
  }, result);
  return { request: { method: 'POST', url: tokenUrl, headers, body: request.postData() },
    response: result, storage: await page.context().storageState() };
}
