import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { parseArgs } from 'node:util';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { openSync, closeSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { spawn } from 'node:child_process';
import { setTimeout as pause } from 'node:timers/promises';

const { values } = parseArgs({ options: {
  help: { type: 'boolean' }, registry: { type: 'string' }, output: { type: 'string' },
  jar: { type: 'string' }, java: { type: 'string' }, 'playwright-module': { type: 'string' },
  'chrome-executable': { type: 'string' }, cases: { type: 'string' },
} });
if (values.help) {
  console.log('Usage: node petclinic_boundary_slice.mjs --registry FILE --output NEW_DIRECTORY --jar FILE [--java PATH] [--playwright-module PATH] [--chrome-executable PATH] [--cases comma,separated,ids]\nRequires unchanged native Angular frontend already serving 127.0.0.1:19766. Owns and restarts a loopback backend on port 9966 per branch. No installations.');
  process.exit(0);
}
for (const required of ['registry', 'output', 'jar']) assert.ok(values[required], '--' + required + ' required');
const out = resolve(values.output);
assert.ok(!existsSync(out), 'output directory must be new');
await mkdir(out, { recursive: true });
const registryBytes = await readFile(values.registry);
const registry = JSON.parse(registryBytes);
const sha = value => createHash('sha256').update(value).digest('hex');
const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
const stateHash = value => sha(JSON.stringify(canonical(value)));
const api = 'http://127.0.0.1:9966/petclinic/api';
const frontend = 'http://127.0.0.1:19766';
const java = values.java || process.env.PETCLINIC_JAVA || 'java';
const require = createRequire(import.meta.url);
const { chromium } = require(values['playwright-module'] || process.env.PETCLINIC_PLAYWRIGHT_MODULE || 'playwright');
const chrome = values['chrome-executable'] || process.env.PETCLINIC_CHROME_EXECUTABLE;
const chosen = values.cases ? values.cases.split(',') : registry.candidates.map(c => c.id);
assert.ok(chosen.every(id => registry.candidates.some(c => c.id === id)), 'unknown case');
const candidates = chosen.map(id => registry.candidates.find(c => c.id === id));
const summary = { subject: 'petclinic', kind: 'development_boundary_slice', started_at: new Date().toISOString(), registry_sha256: sha(registryBytes), runner_sha256: sha(await readFile(new URL(import.meta.url))), jar_sha256: sha(await readFile(values.jar)), backend_commit: registry.backend_commit, frontend_commit: registry.frontend_commit, runtime: { node: process.version, java, java_options: ['-Xmx256m'], jar: resolve(values.jar), frontend, api, playwright: require((values['playwright-module'] || process.env.PETCLINIC_PLAYWRIGHT_MODULE || 'playwright') + '/package.json').version }, independent_process_reset_per_branch: true, source_modified: false, branches: [], pairs: [], cash_spent_usd: 0 };
await writeFile(out + '/registered-candidates.json', registryBytes);
await writeFile(out + '/executed_boundary_slice.mjs', await readFile(new URL(import.meta.url)));
let backend, browser;

async function stopBackend() {
  if (!backend) return;
  const processToStop = backend;
  backend = undefined;
  if (processToStop.exitCode !== null || processToStop.signalCode !== null) return;
  const exited = new Promise(done => processToStop.once('exit', done));
  processToStop.kill('SIGTERM');
  await Promise.race([exited, pause(5000)]);
  if (processToStop.exitCode === null && processToStop.signalCode === null) {
    processToStop.kill('SIGKILL');
    await exited;
  }
}
async function startBackend(name) {
  try {
    await fetch('http://127.0.0.1:9966/petclinic/actuator/health', { signal: AbortSignal.timeout(500), redirect: 'manual' });
    throw new Error('port 9966 already serves a process; refusing to replace it');
  } catch (error) {
    if (String(error).includes('refusing')) throw error;
  }
  const fd = openSync(out + '/' + name + '-backend.log', 'wx');
  backend = spawn(java, ['-Xmx256m', '-jar', resolve(values.jar), '--server.address=127.0.0.1', '--spring.jpa.show-sql=false'], { stdio: ['ignore', fd, fd] });
  closeSync(fd);
  const started = Date.now();
  while (Date.now() - started < 30000) {
    if (backend.exitCode !== null) throw new Error('backend exited during startup: ' + backend.exitCode);
    try {
      const response = await fetch('http://127.0.0.1:9966/petclinic/actuator/health', { signal: AbortSignal.timeout(500), redirect: 'manual' });
      if (response.status === 200 && (await response.json()).status === 'UP') return (Date.now() - started) / 1000;
    } catch {}
    await pause(100);
  }
  throw new Error('backend startup timeout');
}
async function execute(candidate, oracle) {
  const name = candidate.id + '-' + oracle;
  const result = { candidate_id: candidate.id, template: candidate.template, oracle, started_at: new Date().toISOString(), status: 'running', trace: [], blocked_external_requests: [], page_errors: [], actor: 'anonymous native default' };
  let context, page;
  const pending = [];
  async function call(method, path, payload, phase) {
    const started = Date.now();
    const response = await fetch(api + path, { method, body: payload === undefined ? undefined : JSON.stringify(payload), headers: { 'Content-Type': 'application/json' }, redirect: 'manual', signal: AbortSignal.timeout(10000) });
    const raw = await response.text();
    let body; try { body = JSON.parse(raw); } catch { body = raw || null; }
    result.trace.push({ source: 'direct_api', phase, method, path, request: payload ?? null, status: response.status, response: body, seconds: (Date.now() - started) / 1000 });
    return { status: response.status, body };
  }
  async function mustCreate(path, body) {
    const response = await call('POST', path, body, 'prefix_setup');
    assert.equal(response.status, 201, 'valid prefix setup rejected');
    return response.body;
  }
  try {
    result.backend_start_seconds = await startBackend(name);
    result.backend_pid = backend.pid;
    const initial = await call('GET', '/owners', undefined, 'reset_verification');
    assert.equal(initial.status, 200);
    assert.equal(initial.body.length, 10);
    result.initial_state_sha256 = stateHash(initial.body);
    assert.equal(result.initial_state_sha256, 'b3c3071604bd547f72384673b183f160d4f7bf43034d3638bf73b325ba5a143a');
    let owner, pet, target, prefix;
    if (candidate.template === 'owner_address_edit') {
      prefix = await call('POST', '/owners', candidate.payload, 'candidate_prefix');
      if (prefix.status === 201) owner = target = prefix.body;
    } else {
      owner = await mustCreate('/owners', registry.fixtures.owner);
      if (candidate.template === 'pet_rename') {
        prefix = await call('POST', '/owners/' + owner.id + '/pets', candidate.payload, 'candidate_prefix');
        if (prefix.status === 201) {
          pet = target = prefix.body;
          await mustCreate('/owners/' + owner.id + '/pets/' + pet.id + '/visits', registry.fixtures.visit);
        }
      } else {
        pet = await mustCreate('/owners/' + owner.id + '/pets', registry.fixtures.pet);
        prefix = await call('POST', '/owners/' + owner.id + '/pets/' + pet.id + '/visits', candidate.payload, 'candidate_prefix');
        if (prefix.status === 201) target = prefix.body;
      }
    }
    result.prefix_status = prefix.status;
    result.prefix_response = prefix.body;
    const graph = await call('GET', '/owners', undefined, 'post_prefix_state');
    assert.equal(graph.status, 200);
    result.post_prefix_state_sha256 = stateHash(graph.body);
    result.post_prefix_graph = graph.body;
    if (prefix.status !== 201) {
      result.status = 'prefix_rejected';
      result.continuation_reachable = false;
      return result;
    }
    result.continuation_reachable = true;
    const kind = candidate.template === 'owner_address_edit' ? 'owners' : candidate.template === 'pet_rename' ? 'pets' : 'visits';
    const path = '/' + kind + '/' + target.id;
    const before = await call('GET', path, undefined, 'continuation_read');
    assert.equal(before.status, 200);
    result.before = before.body;
    const change = kind === 'owners' ? { address: '2 Pilot Lane' } : kind === 'pets' ? { name: 'Renamedpet' } : { date: '2026-11-07' };
    const expected = { ...before.body, ...change };
    let continuationStatus;
    if (oracle === 'api_semantic') {
      let payload;
      if (kind === 'owners') payload = { id: target.id, ...Object.fromEntries(['firstName', 'lastName', 'address', 'city', 'telephone'].map(k => [k, expected[k]])) };
      else if (kind === 'pets') payload = { id: target.id, name: expected.name, birthDate: expected.birthDate, type: expected.type };
      else {
        const petRead = await call('GET', '/pets/' + pet.id, undefined, 'continuation_read');
        assert.equal(petRead.status, 200);
        payload = { id: target.id, pet: petRead.body, date: expected.date, description: expected.description };
      }
      const update = await call('PUT', path, payload, 'continuation_edit');
      continuationStatus = update.status;
      result.continuation_http_status = continuationStatus;
    } else {
      context = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: 'en-US', timezoneId: 'America/Los_Angeles', serviceWorkers: 'block' });
      await context.route('**/*', route => {
        const url = new URL(route.request().url());
        if (['http:', 'https:'].includes(url.protocol) && !(url.protocol === 'http:' && ['127.0.0.1', 'localhost'].includes(url.hostname) && ['9966', '19766'].includes(url.port))) {
          result.blocked_external_requests.push(url.href);
          return route.abort('blockedbyclient');
        }
        return route.continue();
      });
      page = await context.newPage();
      page.setDefaultTimeout(10000);
      page.on('pageerror', error => result.page_errors.push(String(error)));
      page.on('response', response => {
        const url = new URL(response.url());
        if (url.port !== '9966') return;
        pending.push((async () => {
          const request = response.request();
          let body; try { body = await response.json(); } catch { body = await response.text().catch(() => ''); }
          result.trace.push({ source: 'ui_network', phase: 'continuation', method: request.method(), path: url.pathname, request: request.postDataJSON(), status: response.status(), response: body });
        })());
      });
      const freshRead = page.waitForResponse(r => r.request().method() === 'GET' && new URL(r.url()).pathname === '/petclinic/api' + path);
      await page.goto(frontend + path + '/edit');
      assert.equal((await freshRead).status(), 200);
      result.fresh_ui_read_observed = true;
      result.loaded_ui_fields = {};
      let button;
      if (kind === 'owners') {
        await page.waitForFunction(value => document.querySelector('#telephone')?.value === value, before.body.telephone);
        for (const [label, key] of [['First Name', 'firstName'], ['Last Name', 'lastName'], ['Address', 'address'], ['City', 'city'], ['Telephone', 'telephone']]) {
          result.loaded_ui_fields[key] = await page.getByLabel(label, { exact: true }).inputValue();
          assert.equal(result.loaded_ui_fields[key], before.body[key]);
        }
        await page.getByLabel('Address', { exact: true }).fill(change.address);
        button = page.getByRole('button', { name: 'Update Owner', exact: true });
      } else if (kind === 'pets') {
        await page.waitForFunction(value => document.querySelector('#name')?.value === value, before.body.name);
        for (const id of ['name', 'birthDate', 'typeId', 'owner_name']) result.loaded_ui_fields[id] = await page.locator('#' + id).inputValue();
        assert.equal(result.loaded_ui_fields.name, before.body.name);
        assert.equal(result.loaded_ui_fields.typeId, String(before.body.type.id));
        await page.getByLabel('Name', { exact: true }).fill(change.name);
        button = page.getByRole('button', { name: 'Update Pet', exact: true });
      } else {
        await page.waitForFunction(value => document.querySelector('#description')?.value === value, before.body.description);
        for (const id of ['date', 'description']) result.loaded_ui_fields[id] = await page.locator('#' + id).inputValue();
        assert.equal(result.loaded_ui_fields.description, before.body.description);
        assert.equal(result.loaded_ui_fields.date, before.body.date.replaceAll('-', '/'));
        // The native VisitsModule explicitly declares YYYY/MM/DD, independently of browser locale.
        await page.getByLabel('Date', { exact: true }).fill(change.date.replaceAll('-', '/'));
        await page.getByLabel('Date', { exact: true }).press('Tab');
        assert.equal(await page.getByLabel('Date', { exact: true }).inputValue(), change.date.replaceAll('-', '/'));
        button = page.getByRole('button', { name: 'Update Visit', exact: true });
      }
      result.ui_edit_intended = change;
      result.ui_submit_disabled = await button.isDisabled();
      if (!result.ui_submit_disabled) {
        const pendingUpdate = page.waitForResponse(r => r.request().method() === 'PUT' && new URL(r.url()).pathname === '/petclinic/api' + path);
        await button.click();
        continuationStatus = (await pendingUpdate).status();
        result.continuation_http_status = continuationStatus;
        await page.waitForURL('**/owners/' + owner.id);
      }
      result.ui_page_text = await page.locator('body').innerText();
      await page.screenshot({ path: out + '/' + name + '.png', fullPage: true });
    }
    const after = await call('GET', path, undefined, 'continuation_readback');
    assert.equal(after.status, 200);
    result.after = after.body;
    const afterGraph = await call('GET', '/owners', undefined, 'relationship_readback');
    assert.equal(afterGraph.status, 200);
    result.final_graph = afterGraph.body;
    result.final_state_sha256 = stateHash(afterGraph.body);
    if (result.ui_submit_disabled) {
      assert.deepEqual(after.body, before.body, 'blocked UI must leave entity unchanged');
      assert.deepEqual(afterGraph.body, graph.body, 'blocked UI must leave relationships unchanged');
      result.status = 'ui_blocked';
    } else {
      assert.equal(continuationStatus, 204, 'native mapped update returns 204');
      assert.deepEqual(after.body, expected, 'same intended edit and all untouched entity fields preserved');
      const expectedGraph = structuredClone(graph.body);
      const expectedOwner = expectedGraph.find(o => o.id === owner.id);
      if (kind === 'owners') Object.assign(expectedOwner, change);
      else {
        const expectedPet = expectedOwner.pets.find(p => p.id === pet.id);
        if (kind === 'pets') Object.assign(expectedPet, change);
        else Object.assign(expectedPet.visits.find(v => v.id === target.id), change);
      }
      assert.deepEqual(afterGraph.body, expectedGraph, 'all owner/pet/visit links and untouched fields preserved');
      result.status = 'continuation_passed';
    }
  } catch (error) {
    result.status = 'runner_or_assertion_failure';
    result.error = String(error.stack || error);
    if (page) {
      result.ui_page_text = await page.locator('body').innerText().catch(() => 'unavailable');
      await page.screenshot({ path: out + '/' + name + '-failure.png', fullPage: true }).catch(() => {});
    }
  } finally {
    await Promise.allSettled(pending);
    await context?.close();
    await stopBackend();
    result.finished_at = new Date().toISOString();
    await writeFile(out + '/' + name + '.json', JSON.stringify(result, null, 2) + '\n');
    summary.branches.push({ candidate_id: candidate.id, oracle, status: result.status, prefix_status: result.prefix_status, result: name + '.json', error: result.error });
    console.log(JSON.stringify(summary.branches.at(-1)));
  }
  return result;
}
try {
  browser = await chromium.launch({ headless: true, ...(chrome ? { executablePath: chrome } : { channel: 'chrome' }), args: ['--disable-background-networking'] });
  summary.runtime.chrome = browser.version();
  for (const candidate of candidates) {
    const apiResult = await execute(candidate, 'api_semantic');
    const uiResult = await execute(candidate, 'fresh_ui');
    const pair = { candidate_id: candidate.id, template: candidate.template, initial_state_equal: apiResult.initial_state_sha256 === uiResult.initial_state_sha256 && Boolean(apiResult.initial_state_sha256), post_prefix_state_equal: apiResult.post_prefix_state_sha256 === uiResult.post_prefix_state_sha256 && Boolean(apiResult.post_prefix_state_sha256), api_status: apiResult.status, ui_status: uiResult.status, final_state_equal: apiResult.final_state_sha256 === uiResult.final_state_sha256 && Boolean(apiResult.final_state_sha256) };
    summary.pairs.push(pair);
    await writeFile(out + '/summary.json', JSON.stringify(summary, null, 2) + '\n');
    if (apiResult.status === 'runner_or_assertion_failure' || uiResult.status === 'runner_or_assertion_failure' || !pair.initial_state_equal || !pair.post_prefix_state_equal) {
      summary.stopped_after_harness_or_pair_failure = candidate.id;
      break;
    }
  }
} finally {
  await stopBackend();
  await browser?.close();
  summary.finished_at = new Date().toISOString();
  summary.backend_stopped = true;
  await writeFile(out + '/summary.json', JSON.stringify(summary, null, 2) + '\n');
}
if (summary.stopped_after_harness_or_pair_failure) process.exitCode = 1;
