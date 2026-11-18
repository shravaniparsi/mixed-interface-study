/** Original-control adapter for the registered Mathesar ordinary qualification.
 * Unqualified until its requests and readbacks pass the live ordinary job.
 * Callers retain credentials/storageState privately and enforce network isolation.
 */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { materializeMathesarUserUpdate } from './materialize_mathesar_user_update_v1.mjs';

export const origin = 'http://127.0.0.1:8000';
export const ordinary = Object.freeze({
  full_name: 'Study Control', username: 'studycontrol',
  email: 'studycontrol@example.com', display_language: 'en', is_superuser: false,
});
const edit = Object.freeze({ field: 'full_name', value: 'Study Edited' });

function check(condition, message) {
  if (!condition) throw new Error(message);
}

function equal(actual, expected, message) {
  // Do not include request bodies/passwords in assertion diagnostics.
  try { assert.deepEqual(actual, expected); } catch { throw new Error(message); }
}

function envelope(method, params) {
  return { jsonrpc: '2.0', id: 0, method, params };
}

function publicEnvelope(body) {
  return JSON.parse(JSON.stringify(body, (key, value) => {
    if (/password/i.test(key) && typeof value === 'string') {
      return { private_value_sha256: createHash('sha256').update(value).digest('hex'),
        utf8_bytes: Buffer.byteLength(value) };
    }
    return value;
  }));
}

export function monitorLocalRequests(page) {
  const external = [];
  const pageErrors = [];
  const checkUrl = (url) => {
    if (/^https?:|^wss?:/.test(url) && new URL(url).origin !== origin) {
      // Do not publish query strings which may carry credentials.
      const parsed = new URL(url);
      external.push({ origin: parsed.origin, path: parsed.pathname });
    }
  };
  page.on('request', (request) => checkUrl(request.url()));
  page.on('websocket', (socket) => checkUrl(socket.url()));
  page.on('pageerror', (error) => pageErrors.push(error.name));
  return { external, pageErrors, verify() {
    check(external.length === 0, 'Unexpected external browser request');
    check(pageErrors.length === 0, 'Unexpected browser exception');
  } };
}

async function common(page) {
  const raw = await page.locator('#common-data').textContent();
  const value = JSON.parse(raw);
  check(value.is_authenticated === true && value.user?.username === 'studyadmin'
    && value.user.is_superuser === true, 'Unexpected authenticated actor');
  check(value.per_user_databases_enabled === false, 'Per-user databases enabled');
  check(value.is_sso_login_required === false, 'Unexpected SSO context');
  check(Object.hasOwn(value.supported_languages, 'en'), 'English page context unavailable');
  return value;
}

export async function rpc(page, body) {
  const cookies = await page.context().cookies(origin);
  const token = cookies.find((cookie) => cookie.name === 'csrftoken')?.value;
  check(typeof token === 'string' && token.length > 0, 'Missing original CSRF cookie');
  const response = await page.context().request.post(origin + '/api/rpc/v0/', {
    data: body, headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
    timeout: 30000, maxRedirects: 0,
  });
  const answer = await response.json();
  check(response.status() === 200, 'RPC HTTP response failed');
  check(answer.jsonrpc === '2.0' && answer.id === 0 && Object.hasOwn(answer, 'result')
    && !Object.hasOwn(answer, 'error'), 'RPC application response failed');
  return { status: response.status(), result: answer.result };
}

export async function bootstrap(page, password) {
  await page.goto(origin + '/complete_installation/', { waitUntil: 'domcontentloaded' });
  await page.locator('#id_username').fill('studyadmin');
  await page.locator('#id_password1').fill(password);
  await page.locator('#id_password2').fill(password);
  await page.locator('#one_time_confirmation').uncheck();
  await page.locator('#usage_stats').uncheck();
  const sent = page.waitForRequest((request) => request.method() === 'POST'
    && new URL(request.url()).pathname === '/complete_installation/');
  await page.locator('form.form-card button[type="submit"]').click();
  const request = await sent;
  const form = new URLSearchParams(request.postData());
  check(!form.has('one_time_installation_confirmation') && !form.has('usage_stats'),
    'Telemetry consent appeared in bootstrap request');
  equal(form.get('username'), 'studyadmin', 'Unexpected bootstrap username');
  await page.waitForURL((url) => url.pathname !== '/complete_installation/');
  await page.goto(origin + '/administration/users/', { waitUntil: 'domcontentloaded' });
  const context = await common(page);
  return { actor: context.user, telemetry_flags_submitted: false };
}

async function userForm(page, isNew) {
  const box = page.locator('.form-box').filter({
    has: page.locator('.label-cell').filter({ hasText: /^Display Name$/ }),
  });
  await box.waitFor({ state: 'visible' });
  check(await box.count() === 1, 'Ambiguous original user form');
  const labels = await box.locator('.grid-form > .label-cell').allTextContents();
  equal(labels.map((label) => label.trim()), isNew
    ? ['Display Name', 'Email', 'Username *', 'Password *', 'Display Language *', 'Admin']
    : ['Display Name', 'Email', 'Username *', 'Display Language *', 'Admin'],
  'Original user-form label/order mismatch');
  const cells = box.locator('.grid-form > .input-cell');
  check(await cells.count() === labels.length, 'Original user-form control count mismatch');
  return { box, cells, save: box.getByRole('button', { name: 'Save', exact: true }) };
}

async function nativeSubmit(page, save, expected) {
  await save.waitFor({ state: 'visible', timeout: 5000 });
  await page.waitForFunction((button) => !button.disabled,
    await save.elementHandle(), { timeout: 5000 });
  const actionability = {
    visible: await save.isVisible(), enabled: await save.isEnabled(), clicked: false,
  };
  check(actionability.visible && actionability.enabled, 'Original Save is not actionable');
  const responsePromise = page.waitForResponse((response) => {
    if (response.request().method() !== 'POST'
      || new URL(response.url()).pathname !== '/api/rpc/v0/') return false;
    try { return response.request().postDataJSON()?.method === expected.method; }
    catch { return false; }
  }, { timeout: 30000 });
  await save.click();
  actionability.clicked = true;
  const response = await responsePromise;
  const actual = response.request().postDataJSON();
  try { equal(actual, expected, 'Native emitted request differs from source materialization'); }
  catch (error) {
    error.evidence = { emitted_request: publicEnvelope(actual), expected_request: publicEnvelope(expected),
      actionability, http_status: response.status() };
    throw error;
  }
  const answer = await response.json();
  check(response.status() === 200 && answer.id === 0 && answer.jsonrpc === '2.0'
    && Object.hasOwn(answer, 'result') && !Object.hasOwn(answer, 'error'),
  'Native RPC application response failed');
  const captured = publicEnvelope(actual);
  return { actionability, status: response.status(), result: answer.result,
    emitted_request: captured, complete_request_match: true };
}

export async function createOrdinary(page, password, native) {
  await page.goto(origin + '/administration/users/new/', { waitUntil: 'domcontentloaded' });
  const context = await common(page);
  const body = envelope('users.add', { user_def: { ...ordinary, password } });
  let response;
  if (native) {
    const { cells, save } = await userForm(page, true);
    await cells.nth(0).locator('input').fill(ordinary.full_name);
    await cells.nth(1).locator('input').fill(ordinary.email);
    await cells.nth(2).locator('input').fill(ordinary.username);
    await cells.nth(3).locator('input').fill(password);
    // Preserve the original English/non-admin defaults. The complete emitted
    // request must prove those defaults; do not force a different control state.
    response = await nativeSubmit(page, save, body);
  } else response = await rpc(page, body);
  check(Number.isSafeInteger(response.result?.id) && response.result.id > 0,
    'Producer returned no stable user identity');
  const target = (await rpc(page, envelope('users.get', { user_id: response.result.id }))).result;
  equal(target, { ...ordinary, id: response.result.id }, 'Ordinary persisted user differs');
  await page.goto(origin + `/administration/users/${target.id}/`, { waitUntil: 'domcontentloaded' });
  const { cells } = await userForm(page, false);
  equal(await cells.nth(0).locator('input').inputValue(), target.full_name, 'Editor display-name readback mismatch');
  equal(await cells.nth(1).locator('input').inputValue(), target.email, 'Editor email readback mismatch');
  equal(await cells.nth(2).locator('input').inputValue(), target.username, 'Editor username readback mismatch');
  return { actor: context.user, target, native_producer: native,
    status: response.status, actionability: response.actionability ?? null,
    emitted_request: response.emitted_request ?? null,
    complete_request_match: response.complete_request_match ?? null };
}

export async function continueOrdinary(page, userId, native) {
  await page.goto(origin + `/administration/users/${userId}/`, { waitUntil: 'domcontentloaded' });
  const context = await common(page);
  const before = (await rpc(page, envelope('users.get', { user_id: userId }))).result;
  const body = materializeMathesarUserUpdate(before, Object.keys(context.supported_languages), edit);
  let response;
  if (native) {
    const { cells, save } = await userForm(page, false);
    equal(await cells.nth(0).locator('input').inputValue(), before.full_name ?? '',
      'Native starting display name mismatch');
    equal(await cells.nth(1).locator('input').inputValue(), before.email ?? '',
      'Native starting email mismatch');
    equal(await cells.nth(2).locator('input').inputValue(), before.username ?? '',
      'Native starting username mismatch');
    await cells.nth(0).locator('input').fill(edit.value);
    response = await nativeSubmit(page, save, body);
  } else response = await rpc(page, body);
  const after = (await rpc(page, envelope('users.get', { user_id: userId }))).result;
  equal(after, { ...before, full_name: edit.value }, 'Persisted continuation outcome mismatch');
  return { actor: context.user, before, after, request: body,
    native_continuation: native, status: response.status,
    emitted_request: response.emitted_request ?? null,
    complete_request_match: response.complete_request_match ?? null,
    actionability: response.actionability ?? null };
}
