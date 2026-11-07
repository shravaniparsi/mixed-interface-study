import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { parseArgs } from 'node:util';
import { resolve } from 'node:path';
import assert from 'node:assert/strict';
const require = createRequire(import.meta.url);
const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: { help: { type: 'boolean', short: 'h' }, frontend: { type: 'string' }, api: { type: 'string' }, output: { type: 'string' }, 'playwright-module': { type: 'string' }, 'chrome-executable': { type: 'string' } },
});
if (values.help) {
  console.log(`Usage: node petclinic_route_smoke.mjs ui|api [options]
  --frontend URL          default http://127.0.0.1:19766
  --api URL               default http://127.0.0.1:9966/petclinic/api
  --output DIRECTORY      default results/petclinic-reproduction
  --playwright-module P   installed package name or absolute module path
  --chrome-executable P   optional browser executable; otherwise Chrome channel
Environment alternatives: PETCLINIC_FRONTEND, PETCLINIC_API_URL,
PETCLINIC_RESULTS, PETCLINIC_PLAYWRIGHT_MODULE, PETCLINIC_CHROME_EXECUTABLE.
Requires a freshly restarted native H2 backend before each route.
Only loopback HTTP URLs are accepted. This script does not start or reset servers.`);
  process.exit(0);
}
assert.equal(positionals.length, 1, 'supply one mode: ui or api');
const mode = positionals[0];
assert.ok(['ui', 'api'].includes(mode), 'mode must be ui or api');
const out = resolve(values.output || process.env.PETCLINIC_RESULTS || 'results/petclinic-reproduction');
for (const suffix of ['-route.json', '-final.png', '-failure.png']) {
  assert.ok(!existsSync(out + '/' + mode + suffix), 'choose a new output directory; existing route evidence is not overwritten');
}
const frontend = (values.frontend || process.env.PETCLINIC_FRONTEND || 'http://127.0.0.1:19766').replace(/\/$/, '');
const api = (values.api || process.env.PETCLINIC_API_URL || 'http://127.0.0.1:9966/petclinic/api').replace(/\/$/, '');
const frontendUrl = new URL(frontend);
const apiUrl = new URL(api);
for (const url of [frontendUrl, apiUrl]) {
  assert.ok(url.protocol === 'http:' && ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname), 'only loopback HTTP URLs are permitted');
  assert.ok(!url.username && !url.password && !url.search && !url.hash, 'URLs must omit credentials, queries and fragments');
}
const allowedPorts = new Set([frontendUrl.port || '80', apiUrl.port || '80']);
const apiPath = apiUrl.pathname.replace(/\/$/, '');
const playwrightModule = values['playwright-module'] || process.env.PETCLINIC_PLAYWRIGHT_MODULE || 'playwright';
const chromeExecutable = values['chrome-executable'] || process.env.PETCLINIC_CHROME_EXECUTABLE;
const { chromium } = require(playwrightModule);
await mkdir(out, { recursive: true });
const fields = { firstName: 'Alice', lastName: 'Research', address: '1 Pilot Lane', city: 'Testville', telephone: '5550100001' };
const result = { kind: 'paired_route_feasibility', mode, workflow: 'owner_create_then_meaningful_ui_edit', status: 'running', started_at: new Date().toISOString(), actor: 'anonymous native default', backend_commit: '5180cc9bd0163393c4e628bedc1bc4c27cfaab1b', frontend_commit: 'fba8956cbdd04e09973f81eb39379955a825bfc3', inputs: fields, trace: [], blocked_external_requests: [], console_errors: [], application_source_modified: false };
let browser, context, page;
const captures = [];
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(k => [k, canonical(value[k])]));
  return value;
}
async function apiCall(method, path, data) {
  const response = await context.request.fetch(api + path, { method, data, maxRedirects: 0 });
  const text = await response.text();
  let body; try { body = JSON.parse(text); } catch { body = text; }
  result.trace.push({ source: 'direct_api', method, path, request: data ?? null, status: response.status(), response: body });
  return { response, body };
}
try {
  browser = await chromium.launch({ headless: true, ...(chromeExecutable ? { executablePath: chromeExecutable } : { channel: 'chrome' }), args: ['--disable-background-networking'] });
  result.runtime = { frontend, api, playwright_module: playwrightModule, chrome_executable: chromeExecutable || 'Chrome channel', output: out };
  result.browser_version = browser.version();
  context = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: 'en-US', timezoneId: 'America/Los_Angeles', serviceWorkers: 'block' });
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (['http:', 'https:'].includes(url.protocol) && !(url.protocol === 'http:' && ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname) && allowedPorts.has(url.port || '80'))) {
      result.blocked_external_requests.push(url.href);
      return route.abort('blockedbyclient');
    }
    return route.continue();
  });
  page = await context.newPage();
  page.on('pageerror', error => result.console_errors.push(String(error)));
  page.on('response', response => {
    if ((new URL(response.url()).port || '80') !== (apiUrl.port || '80')) return;
    captures.push((async () => {
      const request = response.request();
      let body; try { body = await response.json(); } catch { body = await response.text().catch(() => ''); }
      result.trace.push({ source: 'ui_network', method: request.method(), url: request.url(), request: request.postData(), status: response.status(), response: body });
    })());
  });
  const initial = await apiCall('GET', '/owners');
  assert.equal(initial.response.status(), 200);
  assert.equal(initial.body.length, 10, 'fresh H2 seed required before each route');
  result.initial_state_sha256 = createHash('sha256').update(JSON.stringify(canonical(initial.body))).digest('hex');
  let owner;
  if (mode === 'ui') {
    await page.goto(frontend + '/owners/add');
    for (const [label, key] of [['First Name', 'firstName'], ['Last Name', 'lastName'], ['Address', 'address'], ['City', 'city'], ['Telephone', 'telephone']]) {
      await page.getByLabel(label, { exact: true }).fill(fields[key]);
    }
    const pending = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname === apiPath + '/owners');
    await page.getByRole('button', { name: 'Add Owner', exact: true }).click();
    const response = await pending;
    assert.equal(response.status(), 201);
    owner = await response.json();
    await page.waitForURL('**/owners');
  } else {
    const created = await apiCall('POST', '/owners', { id: null, ...fields });
    assert.equal(created.response.status(), 201);
    owner = created.body;
  }
  result.created = owner;
  await page.goto(frontend + '/owners/' + owner.id);
  await page.getByRole('heading', { name: 'Owner Information', exact: true }).waitFor();
  await page.getByRole('button', { name: 'Edit Owner', exact: true }).click();
  await page.getByRole('heading', { name: 'Edit Owner', exact: true }).waitFor();
  await page.waitForFunction(expected => document.querySelector('#telephone')?.value === expected, fields.telephone);
  result.loaded_fields = {};
  for (const [label, key] of [['First Name', 'firstName'], ['Last Name', 'lastName'], ['Address', 'address'], ['City', 'city'], ['Telephone', 'telephone']]) {
    result.loaded_fields[key] = await page.getByLabel(label, { exact: true }).inputValue();
    assert.equal(result.loaded_fields[key], fields[key]);
  }
  await page.getByLabel('Address', { exact: true }).fill('2 Pilot Lane');
  const pendingUpdate = page.waitForResponse(r => r.request().method() === 'PUT' && new URL(r.url()).pathname === apiPath + '/owners/' + owner.id);
  await page.getByRole('button', { name: 'Update Owner', exact: true }).click();
  const updated = await pendingUpdate;
  assert.equal(updated.status(), 204);
  await page.getByRole('heading', { name: 'Owner Information', exact: true }).waitFor();
  const persisted = await apiCall('GET', '/owners/' + owner.id);
  assert.equal(persisted.response.status(), 200);
  for (const [key, value] of Object.entries({ ...fields, address: '2 Pilot Lane' })) assert.equal(persisted.body[key], value);
  assert.deepEqual(persisted.body.pets, []);
  result.final_state = persisted.body;
  await page.getByText('2 Pilot Lane', { exact: true }).waitFor();
  await page.screenshot({ path: out + '/' + mode + '-final.png', fullPage: true });
  result.assertions = ['fresh initial owner count10', 'creation HTTP201', 'all fields readable through native UI', 'meaningful address edit through native UI HTTP204', 'persisted values and empty relationships verified', 'updated address visible in UI'];
  result.status = 'passed';
} catch (error) {
  result.status = 'failed';
  result.error = String(error.stack || error);
  if (page) {
    result.page_url = page.url();
    result.page_text = await page.locator('body').innerText().catch(() => 'unavailable');
    await page.screenshot({ path: out + '/' + mode + '-failure.png', fullPage: true }).catch(() => {});
  }
} finally {
  await Promise.allSettled(captures);
  await context?.close();
  await browser?.close();
  result.finished_at = new Date().toISOString();
  await writeFile(out + '/' + mode + '-route.json', JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify({ mode, status: result.status, error: result.error, trace_count: result.trace.length, output: out + '/' + mode + '-route.json' }));
}
if (result.status !== 'passed') process.exitCode = 1;
