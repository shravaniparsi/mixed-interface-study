/** Original ordinary AccessList controls. Runtime qualification still required.
 * Assumes a locally authenticated administrator, English-independent structural
 * selectors, and an existing API-produced ordinary record for the Add button.
 * Never invokes application functions, changes validity, or force-clicks.
 * Returned envelopes include authorization headers: PRIVATE evidence only.
 */
import assert from 'node:assert/strict';

async function one(locator, { visible = true, enabled = true } = {}) {
  if (visible) await locator.waitFor({ state: 'visible' });
  assert.equal(await locator.count(), 1, 'Ambiguous or missing native control');
  if (enabled) assert.equal(await locator.isEnabled(), true, 'Native control disabled');
  return locator;
}

async function modal(page) {
  return one(page.locator('.modal.show').filter({ has: page.locator('form input#name') }));
}

async function tab(dialog, id) {
  await (await one(dialog.locator(`a[role="tab"][href="#${id}"]`))).click();
  return one(dialog.locator(`#${id}`));
}

async function captureOrdinarySubmit(page, dialog, { baseUrl, method, path, json }) {
  const url = new URL(path, baseUrl).href;
  const submit = await one(dialog.locator('button[type="submit"]'));
  const [response] = await Promise.all([
    page.waitForResponse((r) => r.url() === url && r.request().method() === method),
    submit.click(),
  ]);
  const request = response.request();
  const headers = await request.allHeaders();
  assert.equal(headers['content-type'], 'application/json');
  assert.deepEqual(JSON.parse(request.postData()), json, 'Complete original request differs');
  assert.equal(response.status(), method === 'POST' ? 201 : 200);
  const body = await response.json();
  assert.ok(Number.isSafeInteger(body.id) && body.id > 0);
  await dialog.waitFor({ state: 'hidden' });
  return { request: { method, url, headers, body: request.postData() }, response: body };
}

export async function nativeNginxOrdinaryCreate(page, { baseUrl, producer }) {
  assert.equal(producer.items.length, 1);
  assert.equal(producer.clients.length, 1);
  assert.equal(producer.clients[0].directive, 'allow');
  assert.equal(producer.satisfy_any, false);
  assert.equal(producer.pass_auth, false);
  await page.goto(new URL('/access', baseUrl).href, { waitUntil: 'domcontentloaded' });
  // TableWrapper exposes this header button when an ordinary API seed exists.
  await (await one(page.locator('.card-header button.btn-cyan'))).click();
  const dialog = await modal(page);
  await (await one(dialog.locator('input#name'))).fill(producer.name);
  assert.equal(await dialog.locator('input#satisfyAny').isChecked(), false);
  assert.equal(await dialog.locator('input#passAuth').isChecked(), false);
  const auth = await tab(dialog, 'tab-auth');
  await (await one(auth.locator('input[type="text"]'))).fill(producer.items[0].username);
  await (await one(auth.locator('input[type="password"]'))).fill(producer.items[0].password);
  const rules = await tab(dialog, 'tab-rules');
  assert.equal(await rules.locator('select[name="clients[0].directive"]').inputValue(), 'allow');
  await (await one(rules.locator('input[name="clients[0].address"]'))).fill(producer.clients[0].address);
  return captureOrdinarySubmit(page, dialog, { baseUrl, method: 'POST', path: '/api/nginx/access-lists', json: producer });
}

export async function openNginxAccessListEditor(page, { baseUrl, id }) {
  assert.ok(Number.isSafeInteger(id) && id > 0);
  await page.goto(new URL('/access', baseUrl).href, { waitUntil: 'domcontentloaded' });
  // The original table puts the stable record ID in its dropdown header. Names
  // are not unique, and altered names may be missing. Never pick a row by index.
  const identity = page.locator('.dropdown-header').filter({ hasText: new RegExp(`(^|\\D)${id}(\\D|$)`) });
  const row = page.locator('tr').filter({ has: identity });
  await (await one(row.locator('button[data-bs-toggle="dropdown"]'))).click();
  const actions = row.locator('.dropdown-menu > a.dropdown-item');
  assert.equal(await actions.count(), 2, 'Expected original administrator edit/delete actions');
  const readUrl = new URL(`/api/nginx/access-lists/${id}`, baseUrl);
  const [response] = await Promise.all([
    page.waitForResponse((r) => {
      const url = new URL(r.url());
      return url.origin === readUrl.origin && url.pathname === readUrl.pathname && r.request().method() === 'GET';
    }),
    (await one(actions.nth(0))).click(),
  ]);
  assert.equal(response.status(), 200);
  assert.equal(new URL(response.url()).searchParams.get('expand'), 'items,clients');
  const readback = await response.json();
  assert.equal(readback.id, id);
  return { dialog: await modal(page), readback };
}

export async function nativeNginxOrdinaryUpdate(page, { baseUrl, id, edit, materialize }) {
  const { dialog, readback } = await openNginxAccessListEditor(page, { baseUrl, id });
  const expected = materialize(readback, edit);
  assert.equal(expected.method, 'PUT');
  assert.equal(expected.path, `/api/nginx/access-lists/${id}`);
  if (edit.path === '/clients/0/address') {
    const rules = await tab(dialog, 'tab-rules');
    await (await one(rules.locator('input[name="clients[0].address"]'))).fill(edit.value);
  } else if (edit.path === '/items/0/password') {
    const auth = await tab(dialog, 'tab-auth');
    await (await one(auth.locator('input[type="password"]'))).fill(edit.value);
  } else {
    throw new Error('Unscheduled ordinary edit');
  }
  const result = await captureOrdinarySubmit(page, dialog, { baseUrl, ...expected });
  assert.equal(result.response.id, id);
  return { ...result, beforeReadback: readback, expectedRequest: expected };
}
