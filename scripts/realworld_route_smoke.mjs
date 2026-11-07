#!/usr/bin/env node
/**
 * Paired RealWorld article-create/body-edit smoke workflow.
 *
 * Prerequisites: root-managed clean database with the synthetic user fixture,
 * backend on 18765, Vue frontend on 18766, bundled Playwright and local Chrome.
 * This script does not reset or modify the database directly. It is a control
 * workflow, not a defect-discovery experiment or performance comparison.
 *
 * node realworld_route_smoke.mjs --route api-ui --output result.json
 * Optional: --case-id ID --api-base URL --ui-base URL --screenshot failure.jpg
 * Environment: REALWORLD_API_BASE, REALWORLD_UI_BASE, REALWORLD_EMAIL,
 * REALWORLD_PASSWORD, REALWORLD_USERNAME, PLAYWRIGHT_MODULE_PATH,
 * CHROME_EXECUTABLE, SMOKE_TIMEOUT_MS.
 */

import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { performance } from 'node:perf_hooks';

const args = process.argv.slice(2);
const options = {};
for (let i = 0; i < args.length; i += 1) {
  const key = args[i];
  if (!key.startsWith('--') || !args[i + 1] || args[i + 1].startsWith('--')) {
    throw new Error('Use --route ui-ui|api-ui|ui-api|api-api and optional named arguments.');
  }
  options[key.slice(2)] = args[++i];
}

const routeName = options.route || process.env.SMOKE_ROUTE || 'ui-ui';
const [createRoute, editRoute] = routeName.split('-');
if (!['ui-ui', 'api-ui', 'ui-api', 'api-api'].includes(routeName)) {
  throw new Error('Unsupported route; expected ui-ui, api-ui, ui-api or api-api.');
}
const apiBase = (options['api-base'] || process.env.REALWORLD_API_BASE || 'http://127.0.0.1:18765').replace(/\/$/, '');
const uiBase = (options['ui-base'] || process.env.REALWORLD_UI_BASE || 'http://127.0.0.1:18766').replace(/\/$/, '');
const timeoutMs = Number(process.env.SMOKE_TIMEOUT_MS || '30000');
if (!Number.isFinite(timeoutMs) || timeoutMs < 1000) throw new Error('SMOKE_TIMEOUT_MS must be at least 1000.');
const credentials = {
  email: process.env.REALWORLD_EMAIL || 'pilot@example.com',
  password: process.env.REALWORLD_PASSWORD || 'Pilot-Research-123!',
};
const username = process.env.REALWORLD_USERNAME || 'pilotresearch';
const caseId = options['case-id'] || 'realworld_article_create_body_edit';
const input = {
  title: 'Pilot workflow article',
  description: 'Paired UI and API workflow control',
  body: 'Pilot body before the meaningful edit.',
  tagList: ['pilot'],
};
const editedBody = 'Pilot body after a meaningful edit.';
const started = performance.now();
const secrets = new Set([credentials.password]);
let phase = 'configuration';
let browser;
let page;
let apiToken;
let nextRequestId = 0;
const pendingResponses = new Set();
const requestIds = new WeakMap();
const blockedResources = new Set();

function isLoopback(hostname) {
  return ['localhost', '127.0.0.1', '[::1]', '::1'].includes(hostname);
}
for (const value of [apiBase, uiBase]) {
  const u = new URL(value);
  if (u.protocol !== 'http:' || !isLoopback(u.hostname) || u.username || u.password) {
    throw new Error('The smoke runner accepts only plain HTTP loopback application URLs.');
  }
}
const allowedPorts = new Set([new URL(apiBase).port || '80', new URL(uiBase).port || '80']);
function allowedNetworkUrl(value) {
  const u = new URL(value);
  return ['http:', 'ws:'].includes(u.protocol) && isLoopback(u.hostname) && allowedPorts.has(u.port || '80');
}
function scrubString(value) {
  let text = String(value);
  for (const secret of secrets) if (secret) text = text.split(secret).join('[REDACTED]');
  return text.replace(/\/(?:Users|home)\/[^\s"'<>]+/g, '[REDACTED_LOCAL_PATH]');
}
function redact(value, key = '') {
  if (/password|token|authorization|cookie|secret/i.test(key)) return '[REDACTED]';
  if (Array.isArray(value)) return value.map(x => redact(x));
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, redact(v, k)]));
  }
  return typeof value === 'string' ? scrubString(value) : value;
}
function safeUrl(value) {
  try {
    const u = new URL(value);
    for (const key of [...u.searchParams.keys()]) {
      if (/password|token|authorization|cookie|secret/i.test(key)) u.searchParams.set(key, '[REDACTED]');
    }
    return scrubString(u.toString());
  } catch {
    return scrubString(value);
  }
}
const result = {
  schema_version: 1,
  kind: 'paired_workflow_smoke_control',
  case_id: caseId,
  route: routeName,
  started_at: new Date().toISOString(),
  outcome: 'running',
  actor: { username, email: credentials.email },
  applications: { api_base: apiBase, ui_base: uiBase },
  logical_input: { create: input, edit: { body: editedBody } },
  normalization: {
    tagList: 'Compared as an unordered set of tag strings.',
    omitted_comparison_fields: ['slug', 'createdAt', 'updatedAt', 'favoritesCount', 'favorited'],
    justification: 'The control checks title, description, body, tags and author; generated IDs, timestamps and social counters do not define this create/edit intent.',
  },
  environment: {
    browser_context: 'Fresh isolated context; no user profile reused.',
    network: 'Only loopback HTTP/WebSocket requests to the configured two application ports are allowed; external fonts, CSS and images are blocked.',
    database_reset: 'Required before invocation and owned by the orchestrator.',
    ui_authentication: 'Native login form in every route, including the common final UI read check.',
    api_authentication: 'Native /api/users/login endpoint with the same synthetic actor.',
  },
  trace: [],
  checks: [],
};
function event(type, data = {}) {
  result.trace.push({ sequence: result.trace.length + 1, elapsed_ms: Math.round(performance.now() - started), phase, type, ...redact(data) });
}
function parsedBody(text) {
  if (!text) return null;
  if (text.length > 65536) return { omitted: 'body_over_64k', characters: text.length };
  try { return JSON.parse(text); } catch { return { omitted: 'non_json_body', characters: text.length }; }
}
function selectedHeaders(headers) {
  return Object.fromEntries(Object.entries(headers).filter(([key]) =>
    ['content-type', 'authorization', 'origin', 'cookie', 'set-cookie'].includes(key.toLowerCase())));
}
function apiPath(value) {
  try { return new URL(value).pathname.startsWith('/api/'); } catch { return false; }
}
async function apiCall(method, path, body, expectedStatus = 200) {
  const url = new URL(path, `${apiBase}/`).toString();
  if (!allowedNetworkUrl(url)) throw new Error('API request outside configured loopback ports');
  const headers = { 'content-type': 'application/json' };
  if (apiToken) headers.authorization = `Token ${apiToken}`;
  const id = `api-${++nextRequestId}`;
  event('request', { id, source: 'api', method, url: safeUrl(url), headers, body: body ?? null });
  const response = await fetch(url, {
    method, headers, body: body === undefined ? undefined : JSON.stringify(body),
    redirect: 'manual', signal: AbortSignal.timeout(timeoutMs),
  });
  const data = parsedBody(await response.text());
  if (data?.user?.token) secrets.add(data.user.token);
  event('response', { id, source: 'api', status: response.status, headers: selectedHeaders(Object.fromEntries(response.headers)), body: data });
  assert.equal(response.status, expectedStatus, `${method} ${path} status`);
  return data;
}
function businessState(article) {
  assert.ok(article && typeof article === 'object', 'article response exists');
  return {
    title: article.title, description: article.description, body: article.body,
    tagList: [...new Set(article.tagList)].sort(), author: article.author?.username,
  };
}
function verifyState(article, body, label) {
  const observed = businessState(article);
  const expected = { ...input, body, tagList: [...new Set(input.tagList)].sort(), author: username };
  assert.deepEqual(observed, expected, label);
  result.checks.push({ check: label, passed: true, observed });
}
function matchResponse(response, method, pathname) {
  return response.request().method() === method && new URL(response.url()).pathname === pathname;
}
async function clickAndGetArticle(method, pathname) {
  const responsePromise = page.waitForResponse(r => matchResponse(r, method, pathname));
  await page.getByRole('button', { name: 'Publish Article', exact: true }).click();
  const response = await responsePromise;
  assert.equal(response.status(), method === 'POST' ? 201 : 200, `${method} article via UI status`);
  const data = await response.json();
  assert.ok(data.article?.slug, 'UI submission returns article slug');
  await page.waitForURL(url => url.hash === `#/article/${encodeURIComponent(data.article.slug)}` || url.hash === `#/article/${data.article.slug}`);
  return data.article;
}
async function createViaUi() {
  await page.goto(`${uiBase}/#/article/create`, { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Title', { exact: true }).fill(input.title);
  await page.getByLabel('Description', { exact: true }).fill(input.description);
  await page.getByLabel('Body', { exact: true }).fill(input.body);
  for (const tag of input.tagList) {
    await page.getByLabel('Tags', { exact: true }).fill(tag);
    // Native blur invokes the frontend's documented @change tag handler.
    await page.getByLabel('Title', { exact: true }).click();
    await page.locator('.tag-list .tag-pill').filter({ hasText: tag }).waitFor({ state: 'visible' });
  }
  return clickAndGetArticle('POST', '/api/articles');
}
async function editViaUi(slug) {
  await page.goto(`${uiBase}/#/article/${encodeURIComponent(slug)}/edit`, { waitUntil: 'domcontentloaded' });
  // Read-only DOM predicate waits for the asynchronous existing-article fetch.
  await page.waitForFunction(expected =>
    document.querySelector('textarea[aria-label="Body"]')?.value === expected,
  input.body, { timeout: timeoutMs });
  assert.equal(await page.getByLabel('Title', { exact: true }).inputValue(), input.title);
  await page.getByLabel('Body', { exact: true }).fill(editedBody);
  return clickAndGetArticle('PUT', `/api/articles/${slug}`);
}

try {
  phase = 'api_authentication';
  const auth = await apiCall('POST', '/api/users/login', { user: credentials });
  assert.equal(auth.user?.username, username, 'API principal matches fixture');
  assert.ok(auth.user?.token, 'API login returns token');
  apiToken = auth.user.token;

  phase = 'precondition';
  const before = await apiCall('GET', `/api/articles?author=${encodeURIComponent(username)}`);
  assert.equal(before.articlesCount, 0, 'clean fixture must have no existing articles by the synthetic actor');
  result.checks.push({ check: 'clean_actor_article_state', passed: true, count: before.articlesCount });

  phase = 'browser_setup';
  const require = createRequire(import.meta.url);
  const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
  browser = await chromium.launch({
    executablePath: process.env.CHROME_EXECUTABLE || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: true,
    args: ['--disable-background-networking', '--disable-component-update', '--disable-default-apps', '--disable-sync', '--no-first-run'],
  });
  result.environment.browser_version = browser.version();
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: 'en-US', timezoneId: 'UTC', serviceWorkers: 'block' });
  context.setDefaultTimeout(timeoutMs);
  context.setDefaultNavigationTimeout(timeoutMs);
  await context.route('**/*', async intercepted => {
    const request = intercepted.request();
    if (allowedNetworkUrl(request.url())) return intercepted.continue();
    const url = safeUrl(request.url());
    blockedResources.add(url);
    event('blocked_external_resource', { url, resource_type: request.resourceType() });
    return intercepted.abort('blockedbyclient');
  });
  if (typeof context.routeWebSocket === 'function') {
    await context.routeWebSocket('**/*', socket => {
      if (allowedNetworkUrl(socket.url())) socket.connectToServer();
      else {
        blockedResources.add(safeUrl(socket.url()));
        event('blocked_external_websocket', { url: safeUrl(socket.url()) });
        socket.close();
      }
    });
  }
  page = await context.newPage();
  page.on('request', request => {
    if (!apiPath(request.url())) return;
    const id = `ui-${++nextRequestId}`;
    requestIds.set(request, id);
    event('request', { id, source: 'ui', method: request.method(), url: safeUrl(request.url()), headers: selectedHeaders(request.headers()), body: parsedBody(request.postData()) });
  });
  page.on('response', response => {
    if (!apiPath(response.url())) return;
    const capture = (async () => {
      try {
        const data = parsedBody(await response.text());
        if (data?.user?.token) secrets.add(data.user.token);
        event('response', { id: requestIds.get(response.request()), source: 'ui', status: response.status(), headers: selectedHeaders(response.headers()), body: data });
      } catch (error) {
        event('response_capture_error', { id: requestIds.get(response.request()), message: error.message });
      }
    })();
    pendingResponses.add(capture);
    capture.finally(() => pendingResponses.delete(capture));
  });
  page.on('pageerror', error => event('page_error', { message: error.message }));
  page.on('requestfailed', request => {
    if (apiPath(request.url())) event('request_failed', { id: requestIds.get(request), source: 'ui', url: safeUrl(request.url()), error: request.failure()?.errorText });
  });

  phase = 'ui_authentication';
  await page.goto(`${uiBase}/#/login`, { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Email', { exact: true }).fill(credentials.email);
  await page.getByLabel('Password', { exact: true }).fill(credentials.password);
  const uiAuthPromise = page.waitForResponse(r => matchResponse(r, 'POST', '/api/users/login'));
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  const uiAuthResponse = await uiAuthPromise;
  assert.equal(uiAuthResponse.status(), 200, 'native UI login status');
  const uiAuth = await uiAuthResponse.json();
  assert.equal(uiAuth.user?.username, username, 'UI principal matches API principal');
  if (uiAuth.user?.token) secrets.add(uiAuth.user.token);
  await page.waitForURL(url => url.hash === '#/' || url.hash === '');
  result.checks.push({ check: 'equivalent_principal', passed: true, username });

  phase = 'create';
  event('logical_operation_start', { operation: 'create_article', interface: createRoute });
  const created = createRoute === 'ui'
    ? await createViaUi()
    : (await apiCall('POST', '/api/articles', { article: input }, 201)).article;
  assert.ok(created?.slug, 'created article has slug');
  const slug = created.slug;
  result.article_reference = { slug };
  const afterCreate = (await apiCall('GET', `/api/articles/${encodeURIComponent(slug)}`)).article;
  verifyState(afterCreate, input.body, 'persisted_create_state');
  event('logical_operation_complete', { operation: 'create_article', interface: createRoute });

  phase = 'edit';
  event('logical_operation_start', { operation: 'edit_article_body', interface: editRoute });
  // Match the UI's full-field update bundle, including unchanged fields.
  if (editRoute === 'ui') await editViaUi(slug);
  else await apiCall('PUT', `/api/articles/${encodeURIComponent(slug)}`, { article: { ...input, body: editedBody } });
  event('logical_operation_complete', { operation: 'edit_article_body', interface: editRoute });

  phase = 'verification';
  const persisted = (await apiCall('GET', `/api/articles/${encodeURIComponent(slug)}`)).article;
  verifyState(persisted, editedBody, 'persisted_edit_state');
  await page.goto(`${uiBase}/#/article/${encodeURIComponent(slug)}`, { waitUntil: 'domcontentloaded' });
  // Every route must issue a fresh native UI read, including when goto targets
  // the hash route already open after UI creation. A live open tab is not a
  // synchronization oracle for this persisted-workflow control.
  const freshRead = page.waitForResponse(r => matchResponse(r, 'GET', `/api/articles/${slug}`));
  await page.reload({ waitUntil: 'domcontentloaded' });
  const freshResponse = await freshRead;
  assert.equal(freshResponse.status(), 200, 'fresh native UI article read status');
  verifyState((await freshResponse.json()).article, editedBody, 'fresh_ui_read_state');
  event('fresh_ui_read', { action: 'reload', applied_to_every_route: true });
  await page.waitForFunction(expected =>
    document.querySelector('#article-content')?.textContent?.replace(/\s+/g, ' ').trim() === expected,
  editedBody, { timeout: timeoutMs });
  const renderedBody = (await page.locator('#article-content').innerText()).replace(/\s+/g, ' ').trim();
  assert.equal(renderedBody, editedBody, 'edited body is readable through the native UI');
  result.checks.push({ check: 'ui_readable_edited_body', passed: true, observed: renderedBody });
  const after = await apiCall('GET', `/api/articles?author=${encodeURIComponent(username)}`);
  assert.equal(after.articlesCount, 1, 'workflow created exactly one actor-owned article');
  result.checks.push({ check: 'single_article_created', passed: true, count: after.articlesCount });
  result.final_business_state = businessState(persisted);
  result.outcome = 'pass';
} catch (error) {
  result.outcome = 'failed';
  result.failure = {
    phase,
    classification: ['create', 'edit', 'verification'].includes(phase)
      ? 'workflow_discrepancy_unadjudicated'
      : 'runner_or_environment_precondition',
    name: error.name,
    message: scrubString(error.message),
  };
  if (options.screenshot && page) {
    try {
      const path = resolve(options.screenshot);
      await mkdir(dirname(path), { recursive: true });
      await page.screenshot({ path, type: 'jpeg', quality: 45, fullPage: false });
      result.failure.screenshot = options.screenshot;
    } catch (screenshotError) {
      result.failure.screenshot_error = scrubString(screenshotError.message);
    }
  }
} finally {
  await Promise.allSettled([...pendingResponses]);
  if (browser) await browser.close().catch(error => event('browser_close_error', { message: error.message }));
  result.environment.blocked_external_resources = [...blockedResources].sort();
  result.completed_at = new Date().toISOString();
  result.elapsed_ms = Math.round(performance.now() - started);
  // Redact again after all login responses have supplied their token strings.
  const serialized = `${JSON.stringify(redact(result), null, 2)}\n`;
  if (options.output) {
    const path = resolve(options.output);
    await mkdir(dirname(path), { recursive: true });
    await writeFile(path, serialized);
  }
  process.stdout.write(serialized);
  process.exitCode = result.outcome === 'pass' ? 0 : 1;
}
