/** PRIVATE JSON-lines browser worker for the future bounded qualification job.
 * No dispatch occurs here. Run only inside the pinned browser container on the
 * registered internal network; every command and result must remain private.
 */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { createReadStream } from 'node:fs';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { createInterface } from 'node:readline';
import { nativeNginxLogin } from './nginx_native_login_v1.mjs';
import { nativeNginxOrdinaryCreate, nativeNginxOrdinaryUpdate } from './nginx_native_access_list_v1.mjs';
import { materializeNginxAccessListUpdate } from './materialize_nginx_access_list_update_v1.mjs';

assert.equal(process.argv.slice(2).length, 3);
const [toolsDirectory, frontendDirectory, evidenceDirectory] = process.argv.slice(2).map((value) => resolve(value));
assert.equal(process.version, 'v20.20.2');
const require = createRequire(resolve(toolsDirectory, 'package.json'));
assert.equal(require('playwright/package.json').version, '1.62.1');
const { chromium } = require('playwright');
const executable = '/ms-playwright/chromium-1234/chrome-linux64/chrome';
const binaryHash = createHash('sha256');
for await (const chunk of createReadStream(executable)) binaryHash.update(chunk);
assert.equal(binaryHash.digest('hex'), '0b20b130e7edd9dd51873be867761295fe0cfad490c2b9a64f95bd3cfc08fa71');
const baseUrl = 'http://172.28.0.2:81';
const schedule = JSON.parse(await readFile(new URL('../../manifests/catalog-nginx-input-schedule-v1.json', import.meta.url), 'utf8'));
const ordinary = schedule.cases.find((entry) => entry.case === 'ordinary');
assert.ok(ordinary && ordinary.independent_continuations.length === 2);
function checkEdit(edit) {
  assert.deepEqual(Object.keys(edit).sort(), ['path', 'value']);
  assert.ok(ordinary.independent_continuations.some((item) => item.path === edit.path && item.value === edit.value));
}
await mkdir(evidenceDirectory, { recursive: false, mode: 0o700 });
const browser = await chromium.launch({ executablePath: executable, headless: true });
assert.equal(browser.version(), '151.0.7922.34');
let context, page, loginResult, savedStorage, loginAt;
let nextEvent = 0;
let fatal = null;
const events = [];
const pending = new Map();
const requests = new WeakMap();
const usedIds = new Set();
const sha = (value) => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const materialize = (readback, edit) => materializeNginxAccessListUpdate({ readback, edit, toolsDirectory: frontendDirectory });

function record(event) {
  if (events.length >= 5000) { fatal = 'Browser observation limit reached'; return; }
  events.push({ at: Date.now(), ...event });
}

async function newContext(storageState) {
  context = await browser.newContext({ locale: 'en-US', timezoneId: 'UTC', storageState });
  context.setDefaultTimeout(15000);
  context.setDefaultNavigationTimeout(30000);
  await context.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.origin === baseUrl) return route.continue();
    // The source uses third-party gravatar images. Record and block them; never
    // contact the third party or treat a missing cosmetic avatar as a defect.
    const cosmetic = ['http:', 'https:'].includes(url.protocol) && url.hostname === 'www.gravatar.com' &&
      url.pathname.startsWith('/avatar/') && request.resourceType() === 'image';
    record({ kind: 'external_blocked', url: url.href, cosmetic });
    if (!cosmetic) fatal = 'Unregistered external browser request';
    return route.abort('blockedbyclient');
  });
  context.on('request', (request) => {
    const id = ++nextEvent;
    requests.set(request, id);
    pending.set(id, { method: request.method(), url: request.url() });
    record({ kind: 'request', id, method: request.method(), url: request.url() });
  });
  context.on('requestfinished', (request) => {
    const id = requests.get(request); pending.delete(id); record({ kind: 'finished', id });
  });
  context.on('requestfailed', (request) => {
    const id = requests.get(request); pending.delete(id);
    record({ kind: 'failed', id, failure: request.failure() });
  });
  page = await context.newPage();
}

async function token() {
  assert.ok(loginResult, 'Original native login required');
  const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('authentications')));
  assert.ok(Array.isArray(stored) && stored.length === 1);
  assert.deepEqual(stored[0], loginResult.response, 'Original token changed or refreshed');
  assert.ok(Date.parse(stored[0].expires) > Date.now() + 120000, 'Insufficient original token lifetime');
  return stored[0].token;
}

async function api(method, path, body) {
  assert.ok(['GET', 'POST', 'PUT'].includes(method));
  assert.match(path, /^\/api\/nginx\/access-lists(?:\/[1-9][0-9]*(?:\?expand=items,clients)?)?$/);
  const bearer = await token();
  const headers = { Authorization: `Bearer ${bearer}` };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const result = await page.evaluate(async ({ path, method, headers, body }) => {
    const response = await fetch(path, { method, headers, body });
    return { status: response.status, headers: Object.fromEntries(response.headers), body: await response.text() };
  }, { path, method, headers, body });
  await token();
  return { request: { method, path, headers, body }, ...result, json: JSON.parse(result.body) };
}

async function idle() {
  await page.waitForLoadState('networkidle', { timeout: 15000 });
  assert.equal(pending.size, 0, 'Browser requests remain pending');
  await token();
  assert.ok(Date.now() - loginAt < 240000, 'Outside conservative original refresh window');
  if (fatal) throw new Error(fatal);
  const observation = { events: [...events], pending: [...pending], observedAt: Date.now(), loginAt,
    tokenSha256: sha(loginResult.response), tokenUnchanged: true };
  const observationSha256 = sha(observation);
  await writeFile(resolve(evidenceDirectory, `observation-${observationSha256}.json`), JSON.stringify(observation), { flag: 'wx', mode: 0o600 });
  return { browser_requests_settled: true, token_unchanged: true,
    refresh_outside_checkpoint_interval: true, observation_sha256: observationSha256,
    observed_at_ms: observation.observedAt };
}

async function execute(command) {
  switch (command.operation) {
    case 'login':
      assert.equal(loginResult, undefined, 'Only one native login per worker');
      loginAt = Date.now();
      loginResult = await nativeNginxLogin(page, { baseUrl, identity: command.identity, secret: command.secret });
      return loginResult;
    case 'api_create': {
      assert.deepEqual(command.producer, ordinary.producer_body);
      const result = await api('POST', '/api/nginx/access-lists', JSON.stringify(command.producer));
      assert.equal(result.status, 201);
      assert.ok(Number.isSafeInteger(result.json.id) && result.json.id > 0);
      return result;
    }
    case 'native_create':
      assert.deepEqual(command.producer, ordinary.producer_body);
      await token();
      return nativeNginxOrdinaryCreate(page, { baseUrl, producer: command.producer });
    case 'read':
      assert.ok(Number.isSafeInteger(command.id) && command.id > 0);
      return api('GET', `/api/nginx/access-lists/${command.id}?expand=items,clients`);
    case 'native_update':
      checkEdit(command.edit);
      await token();
      return nativeNginxOrdinaryUpdate(page, { baseUrl, id: command.id, edit: command.edit, materialize });
    case 'api_update': {
      checkEdit(command.edit);
      assert.ok(Number.isSafeInteger(command.id) && command.id > 0);
      const before = await api('GET', `/api/nginx/access-lists/${command.id}?expand=items,clients`);
      assert.equal(before.status, 200); assert.equal(before.json.id, command.id);
      const expected = materialize(before.json, command.edit);
      const result = await api('PUT', expected.path, expected.body);
      assert.equal(result.status, 200); assert.equal(result.json.id, command.id);
      return { before, expected, result };
    }
    case 'quiescence': return idle();
    case 'save_storage':
      assert.equal(savedStorage, undefined, 'Checkpoint browser state is immutable');
      await idle(); savedStorage = await context.storageState();
      return { storage: savedStorage, sha256: sha(savedStorage) };
    case 'restore_storage':
      assert.ok(savedStorage); await token();
      await context.close();
      assert.equal(pending.size, 0);
      await newContext(savedStorage);
      await page.goto(`${baseUrl}/access`, { waitUntil: 'domcontentloaded' });
      await token(); return { restoredStorageSha256: sha(savedStorage) };
    default: throw new Error('Unregistered ordinary browser operation');
  }
}

await newContext();
process.stdout.write(JSON.stringify({ status: 'ready', browserVersion: browser.version() }) + '\n');
try {
  for await (const line of createInterface({ input: process.stdin, crlfDelay: Infinity })) {
    assert.ok(Buffer.byteLength(line) <= 65536, 'Command byte bound');
    const command = JSON.parse(line);
    assert.match(command.requestId, /^[a-z0-9-]{1,64}$/);
    assert.equal(usedIds.has(command.requestId), false, 'No repeated command IDs/retries');
    usedIds.add(command.requestId);
    let envelope;
    try {
      if (fatal) throw new Error(fatal);
      const result = await execute(command);
      if (fatal) throw new Error(fatal);
      envelope = { requestId: command.requestId, status: 'completed', result };
    } catch (error) {
      envelope = { requestId: command.requestId, status: 'failed', error: { name: error.name, message: error.message } };
      fatal = 'Prior ordinary command failed; no further operations permitted';
    }
    await writeFile(resolve(evidenceDirectory, `${command.requestId}.json`), JSON.stringify(envelope), { flag: 'wx', mode: 0o600 });
    process.stdout.write(JSON.stringify(envelope) + '\n');
    if (envelope.status === 'failed') break;
  }
} finally {
  await writeFile(resolve(evidenceDirectory, 'events.json'), JSON.stringify(events), { flag: 'wx', mode: 0o600 });
  await browser.close();
}
