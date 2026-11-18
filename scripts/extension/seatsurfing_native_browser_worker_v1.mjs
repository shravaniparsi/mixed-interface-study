/** PRIVATE ordinary-control worker. Requires the registered isolated container.
 * Executable preparation only: no qualification run is authorized by this file.
 */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { createReadStream } from 'node:fs';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { createInterface } from 'node:readline';
import { nativeSeatsurfingLogin } from './seatsurfing_native_login_v1.mjs';
import { nativeSeatsurfingOrdinaryCreate, openSeatsurfingLocationEditor, nativeSeatsurfingScalarEdit } from './seatsurfing_native_location_v1.mjs';
import { observeSeatsurfingBrowser, captureSeatsurfingBrowserState } from './seatsurfing_browser_observation_v1.mjs';
import { materializeSeatsurfingLocationUpdate } from './materialize_seatsurfing_location_update_v1.mjs';

assert.equal(process.argv.slice(2).length, 3);
const [toolsDirectory, configurationPath, evidenceDirectory] = process.argv.slice(2).map(x => resolve(x));
assert.equal(process.version, 'v24.18.1');
assert.equal(Intl.DateTimeFormat().resolvedOptions().timeZone, 'UTC');
const require = createRequire(resolve(toolsDirectory, 'package.json'));
assert.equal(require('playwright/package.json').version, '1.62.1');
const { chromium } = require('playwright');
const executablePath = '/ms-playwright/chromium-1234/chrome-linux64/chrome';
const digest = createHash('sha256');
for await (const chunk of createReadStream(executablePath)) digest.update(chunk);
assert.equal(digest.digest('hex'), '0b20b130e7edd9dd51873be867761295fe0cfad490c2b9a64f95bd3cfc08fa71');
const hash = raw => createHash('sha256').update(raw).digest('hex');
const readBounded = async path => {
  const bytes = await readFile(path);
  assert.ok(bytes.length <= 1048576, 'Private configuration/storage observation bound');
  return bytes;
};
const config = JSON.parse(await readBounded(configurationPath));
assert.equal(config.origin, 'http://127.0.0.1:8080');
assert.ok(['native_login', 'verified_restoration'].includes(config.mode));
const origin = config.origin;
const schedule = JSON.parse(await readFile(new URL('../../manifests/catalog-seatsurfing-input-schedule-v1.json', import.meta.url), 'utf8'));
assert.equal(schedule.revision, '9953f452324bab6fb8f7106dd8965cc401aa456c');
const ordinary = schedule.ordinary;
const edits = [{ path: '/announcement', value: 'Edit notice' }, { path: '/description', value: 'Edit description' }];
let storageState, nativeCredentials;
if (config.mode === 'verified_restoration') {
  assert.match(config.storageSha256, /^[a-f0-9]{64}$/);
  const raw = await readBounded(resolve(config.storagePath));
  assert.equal(hash(raw), config.storageSha256);
  storageState = JSON.parse(raw);
  assert.equal(storageState.origins.length, 1);
  assert.equal(storageState.origins[0].origin, origin);
  const local = Object.fromEntries(storageState.origins[0].localStorage.map(x => [x.name, x.value]));
  nativeCredentials = config.nativeCredentials;
  assert.equal(local.accessToken, nativeCredentials.accessToken);
  assert.equal(local.refreshToken, nativeCredentials.refreshToken);
  assert.ok(Number(local.accessTokenExpiry) > Date.now() + 120000);
  // The outer coordinator must verify the joint manifest/database before launch.
  // This worker verifies storage bytes only and never claims joint restoration.
}
await mkdir(evidenceDirectory, { recursive: false, mode: 0o700 });
let evidenceBytes = 0;
async function retain(name, value) {
  assert.match(name, /^[a-z0-9-]+\.json$/);
  const raw = JSON.stringify(value);
  evidenceBytes += Buffer.byteLength(raw);
  assert.ok(evidenceBytes <= 32 * 1024 * 1024, 'Private worker evidence bound');
  await writeFile(resolve(evidenceDirectory, name), raw, { flag: 'wx', mode: 0o600 });
  return { file: name, sha256: hash(raw) };
}
const browser = await chromium.launch({ executablePath, headless: true });
assert.equal(browser.version(), '151.0.7922.34');
const context = await browser.newContext({ locale: 'en-US', timezoneId: 'UTC', storageState });
context.setDefaultTimeout(15000);
context.setDefaultNavigationTimeout(30000);
const observer = observeSeatsurfingBrowser(context, origin);
let boundaryFailure = null;
await context.route('**/*', async route => {
  if (new URL(route.request().url()).origin === origin) return route.continue();
  boundaryFailure = 'Unregistered external browser request';
  return route.abort('blockedbyclient');
});
await context.routeWebSocket('**/*', socket => {
  boundaryFailure = 'Unmapped browser WebSocket';
  socket.close();
});
const page = await context.newPage();
let phase = storageState ? 'authenticated' : 'initial';
let opened, createdId, captured = false;
const usedIds = new Set();
async function quiet() {
  if (boundaryFailure) throw new Error(boundaryFailure);
  const result = await observer.quiet();
  if (boundaryFailure) throw new Error(boundaryFailure);
  return result;
}
async function tokenGuard() {
  assert.ok(nativeCredentials);
  const state = await page.evaluate(() => ({ accessToken: localStorage.getItem('accessToken'), refreshToken: localStorage.getItem('refreshToken'), expiry: Number(localStorage.getItem('accessTokenExpiry')) }));
  assert.equal(state.accessToken, nativeCredentials.accessToken);
  assert.equal(state.refreshToken, nativeCredentials.refreshToken);
  assert.ok(state.expiry > Date.now() + 120000);
}
async function execute(command) {
  switch (command.operation) {
    case 'login': {
      assert.equal(phase, 'initial');
      const result = await nativeSeatsurfingLogin(page, { baseUrl: origin, ...config.login });
      nativeCredentials = { accessToken: result.response.accessToken, refreshToken: result.response.refreshToken };
      await quiet(); await tokenGuard(); phase = 'authenticated';
      return result;
    }
    case 'create': {
      assert.equal(phase, 'authenticated');
      assert.equal(config.mode, 'native_login');
      const result = await nativeSeatsurfingOrdinaryCreate(page, { baseUrl: origin, values: ordinary, expectedJson: ordinary });
      await retain('native-create.json', result);
      assert.equal(result.response?.status, 201);
      assert.equal(result.createdIdValid, true);
      assert.equal(result.completePayloadMatches, true);
      await quiet(); await tokenGuard(); createdId = result.createdId; phase = 'created';
      return result;
    }
    case 'open': {
      assert.ok(['authenticated', 'created'].includes(phase));
      if (createdId) assert.equal(command.id, createdId);
      opened = await openSeatsurfingLocationEditor(page, { baseUrl: origin, id: command.id });
      await quiet(); await tokenGuard(); phase = 'editor';
      return opened;
    }
    case 'capture': {
      assert.equal(phase, 'editor'); assert.equal(captured, false);
      await quiet();
      const result = await captureSeatsurfingBrowserState({ context, page, observer, origin, nativeCredentials });
      await retain('browser-storage.json', result.storage);
      await retain('browser-network.json', result.network.events);
      captured = true;
      return result;
    }
    case 'edit': {
      assert.equal(phase, 'editor');
      assert.ok(edits.some(edit => JSON.stringify(edit) === JSON.stringify(command.edit)));
      assert.deepEqual(command.materialization.readback, opened.readback);
      const plan = materializeSeatsurfingLocationUpdate({ ...command.materialization, edit: command.edit, browserTimezone: 'UTC' });
      await tokenGuard();
      const result = await nativeSeatsurfingScalarEdit(page, { baseUrl: origin, id: opened.readback.id, edit: command.edit, expectedJson: plan.main.json });
      await retain('native-edit.json', { plan, result });
      await quiet(); await tokenGuard(); phase = 'edited';
      return { plan, result, ancillaryEqualityEstablished: false, runtimeQualified: false };
    }
    default: throw new Error('Unregistered ordinary native-browser operation');
  }
}
// An external coordinator also enforces its process deadline. A timeout stops
// this worker; it never dispatches a repeat command or interprets missing data.
const deadline = setTimeout(() => process.exit(124), 9 * 60 * 1000);
process.stdout.write(JSON.stringify({ status: 'ready', mode: config.mode, browserVersion: browser.version(), runtimeQualified: false }) + '\n');
try {
  for await (const line of createInterface({ input: process.stdin, crlfDelay: Infinity })) {
    assert.ok(Buffer.byteLength(line) <= 65536, 'Command observation bound');
    const command = JSON.parse(line);
    assert.match(command.requestId, /^[a-z0-9-]{1,64}$/);
    assert.equal(usedIds.has(command.requestId), false, 'Repeated command ID');
    assert.ok(usedIds.size < 6, 'Ordinary worker command bound');
    usedIds.add(command.requestId);
    const result = await execute(command);
    const artifact = await retain(command.requestId + '-result.json', result);
    process.stdout.write(JSON.stringify({ requestId: command.requestId, status: 'completed', artifact, phase }) + '\n');
  }
} catch (error) {
  await retain('worker-failure.json', { error: { name: error.name, message: error.message }, phase, boundaryFailure, observation: observer.snapshot() });
  process.stdout.write(JSON.stringify({ status: 'failed', phase, retryAuthorized: false }) + '\n');
  process.exitCode = 1;
} finally {
  clearTimeout(deadline);
  await retain('final-network.json', observer.snapshot());
  observer.dispose();
  await browser.close();
}
