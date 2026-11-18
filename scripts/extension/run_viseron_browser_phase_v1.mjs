import fs from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { parseArgs } from 'node:util';
import assert from 'node:assert/strict';
import { nativeCreate, nativeEdit, verifyOrdinaryReadback, verifyContinuationReadback } from './viseron_native_controls_v1.mjs';
import { materializeViseronUserUpdate } from './materialize_viseron_user_update_v1.mjs';

const { values: args } = parseArgs({ options: { phase: { type: 'string' }, out: { type: 'string' }, private: { type: 'string' } } });
assert(['producer', 'warm', 'seed', 'native', 'api'].includes(args.phase));
const origin = 'http://127.0.0.1:8888';
const schedule = JSON.parse(await fs.readFile(new URL('../../manifests/catalog-viseron-input-schedule-v1.json', import.meta.url), 'utf8'));
const ordinary = schedule.cases[0];
const hash = (value) => createHash('sha256').update(typeof value === 'string' ? value : JSON.stringify(value)).digest('hex');
const report = { phase: args.phase, status: 'failed', external_requests: [], page_errors: [], token_refreshes: 0 };
const privateRequests = [];
let browser;

function isLocal(raw) {
  const url = new URL(raw);
  return ['http:', 'ws:'].includes(url.protocol) && url.hostname === '127.0.0.1' && url.port === '8888';
}
function publicRequest(request) {
  const headers = request.headers;
  return { method: request.method, path: request.path, body: request.body,
    headers: Object.fromEntries(Object.entries(headers).map(([key, value]) => [key,
      ['authorization', 'cookie', 'x-xsrftoken'].includes(key) ? { sha256: hash(value) } : value])) };
}
async function request(page, method, path, body) {
  return page.evaluate(async ({ method, path, body }) => {
    const tokens = JSON.parse(localStorage.getItem('tokens'));
    if (!tokens || typeof tokens.header !== 'string' || typeof tokens.payload !== 'string'
      || !(Date.parse(tokens.expires_at) - Date.now() > 120000)) throw new Error('Missing or near-expired original token');
    const headers = { 'Content-Type': 'application/json', Accept: 'application/json, text/plain, */*',
      'X-Requested-With': 'XMLHttpRequest', 'X-Client-UTC-Offset': '0',
      Authorization: `Bearer ${tokens.header}.${tokens.payload}` };
    const xsrf = document.cookie.split('; ').find((x) => x.startsWith('_xsrf='));
    if (xsrf) headers['X-Xsrftoken'] = decodeURIComponent(xsrf.substring(6));
    const response = await fetch('/api/v1' + path, { method, credentials: 'same-origin', headers,
      ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
    return { status: response.status, body: await response.json() };
  }, { method, path, body });
}
async function userByName(page, username) {
  const list = await request(page, 'GET', '/auth/users');
  assert.equal(list.status, 200);
  const matches = list.body.users.filter((x) => x.username === username);
  assert.equal(matches.length, 1);
  const response = await request(page, 'GET', '/auth/user/' + matches[0].id);
  assert.equal(response.status, 200);
  assert.deepEqual(response.body, matches[0]);
  return response.body;
}
async function bootstrap(page) {
  await page.goto(origin + '/#/onboarding', { waitUntil: 'domcontentloaded' });
  const actor = schedule.ordinary_actor;
  await page.getByLabel('Display Name', { exact: true }).fill(actor.name);
  await page.getByLabel('Username', { exact: true }).fill(actor.username);
  await page.getByLabel('Password', { exact: true }).fill(actor.password);
  await page.getByLabel('Confirm Password', { exact: true }).fill(actor.password);
  const button = page.getByRole('button', { name: 'SIGN UP', exact: true });
  assert.equal(await button.isEnabled(), true);
  const responsePromise = page.waitForResponse((r) => r.request().method() === 'POST' && new URL(r.url()).pathname === '/api/v1/onboarding');
  await button.click();
  const response = await responsePromise;
  assert.equal(response.status(), 200);
  assert.deepEqual(response.request().postDataJSON(), { client_id: origin + '/', ...actor });
  await page.waitForFunction(() => localStorage.getItem('tokens') !== null);
  await page.goto(origin + '/#/settings/users', { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: 'add', exact: true }).waitFor({ state: 'visible' });
  const stored = await userByName(page, actor.username);
  assert.equal(stored.role, 'admin');
  assert.equal(stored.enabled, true);
  return stored;
}

try {
  assert.equal(process.version, 'v20.20.2');
  const require = createRequire(import.meta.url);
  const modulePath = process.env.PLAYWRIGHT_MODULE_PATH;
  const { chromium } = require(modulePath);
  assert.equal(require(modulePath + '/package.json').version, '1.62.1');
  const executable = '/ms-playwright/chromium-1234/chrome-linux64/chrome';
  report.executable_sha256 = createHash('sha256').update(await fs.readFile(executable)).digest('hex');
  assert.equal(report.executable_sha256, '0b20b130e7edd9dd51873be867761295fe0cfad490c2b9a64f95bd3cfc08fa71');
  browser = await chromium.launch({ headless: true, executablePath: executable, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  report.browser_version = browser.version();
  assert.equal(report.browser_version, '151.0.7922.34');
  const resumed = ['native', 'api'].includes(args.phase);
  const storage = resumed ? JSON.parse(await fs.readFile(args.private + '/seed-storage.json', 'utf8')) : undefined;
  const context = await browser.newContext({ locale: 'en-US', timezoneId: 'UTC', viewport: { width: 1280, height: 960 }, ...(storage ? { storageState: storage } : {}) });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  page.setDefaultNavigationTimeout(30000);
  page.on('request', (req) => {
    if (!isLocal(req.url())) report.external_requests.push({ url_sha256: hash(req.url()), method: req.method() });
    if (new URL(req.url()).pathname === '/api/v1/auth/token') report.token_refreshes += 1;
  });
  page.on('websocket', (ws) => {
    if (!isLocal(ws.url())) report.external_requests.push({ websocket_url_sha256: hash(ws.url()) });
  });
  page.on('pageerror', (error) => report.page_errors.push({ name: error.name, message_sha256: hash(error.message) }));
  let actor, target;
  if (!resumed) {
    actor = await bootstrap(page);
    if (args.phase === 'producer') {
      privateRequests.push(await nativeCreate(page, origin, ordinary.producer_body));
    } else {
      const created = await request(page, 'POST', '/auth/create', ordinary.producer_body);
      assert.equal(created.status, 200);
      assert.deepEqual(created.body, { success: true });
    }
    target = await userByName(page, ordinary.producer_body.username);
    verifyOrdinaryReadback(target, ordinary.producer_body);
    report.producer = { actor, target, body: { ...ordinary.producer_body, password: '<public-synthetic-fixture>' }, mode: args.phase === 'producer' ? 'native' : 'api' };
    if (args.phase === 'seed') {
      await fs.writeFile(args.private + '/seed-storage.json', JSON.stringify(await context.storageState()), { mode: 0o600, flag: 'wx' });
      await fs.writeFile(args.private + '/seed-user.json', JSON.stringify({ actor, target }), { mode: 0o600, flag: 'wx' });
    }
  } else {
    const seed = JSON.parse(await fs.readFile(args.private + '/seed-user.json', 'utf8'));
    await page.goto(origin + '/#/settings/users', { waitUntil: 'domcontentloaded' });
    await page.getByRole('button', { name: 'add', exact: true }).waitFor({ state: 'visible' });
    actor = await userByName(page, schedule.ordinary_actor.username);
    target = await userByName(page, ordinary.producer_body.username);
    assert.deepEqual({ actor, target }, seed);
    report.restored_storage_sha256 = hash(storage);
  }
  if (['warm', 'native', 'api'].includes(args.phase)) {
    const materialized = materializeViseronUserUpdate(target, ordinary.unrelated_edit);
    let observed;
    if (args.phase !== 'api') {
      const native = await nativeEdit(page, origin, target, ordinary.unrelated_edit);
      observed = native.observed;
      report.actionability = native.actionability;
    } else {
      const responsePromise = page.waitForResponse((r) => r.request().method() === 'PUT' && new URL(r.url()).pathname === '/api/v1' + materialized.api_relative_path);
      const result = await request(page, 'PUT', materialized.api_relative_path, materialized.body);
      assert.equal(result.status, 200);
      assert.deepEqual(result.body, { success: true });
      const response = await responsePromise;
      const req = response.request();
      observed = { method: req.method(), path: new URL(req.url()).pathname, body: req.postDataJSON(), headers: await req.allHeaders() };
      assert.deepEqual(observed.body, materialized.body);
    }
    privateRequests.push(observed);
    const result = await request(page, 'GET', '/auth/user/' + target.id);
    assert.equal(result.status, 200);
    verifyContinuationReadback(target, result.body, ordinary.unrelated_edit);
    report.continuation = { actor, before: target, after: result.body, request: publicRequest(observed) };
  }
  assert.equal(report.token_refreshes, 0);
  // Network containment is proved by Docker inspection, not failed browser events.
  // Retain attempted external URLs as hashes; do not infer successful connections.
  assert.deepEqual(report.page_errors, []);
  await context.close();
  report.status = 'ordinary_phase_passed';
} catch (error) {
  await fs.writeFile(`${args.private}/${args.phase}-error.txt`, String(error.stack ?? error), { mode: 0o600 });
  report.error_type = error.name;
  report.error_message_sha256 = hash(error.message);
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  await fs.writeFile(`${args.private}/${args.phase}-requests.json`, JSON.stringify(privateRequests), { mode: 0o600 });
  await fs.writeFile(`${args.out}/${args.phase}-browser.json`, JSON.stringify(report, null, 2) + '\n', { flag: 'wx' });
}
