/** Original visible-form location controls; runtime UNQUALIFIED.
 * No browser/app starts here. Returned requests/DOM values are private evidence.
 * Global network recording and worker deadlines belong to the runtime harness.
 */
import assert from 'node:assert/strict';
const selectors = { '/name': '#location-name', '/description': '#location-description', '/announcement': '#location-announcement' };
const validId = id => typeof id === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id);
function clock() {
  const end = Date.now() + 30000;
  return () => { const n = end - Date.now(); assert.ok(n > 0, 'Native location observation deadline'); return n; };
}
async function ready(page, remaining) {
  const form = page.locator('form#form');
  await form.waitFor({ state: 'visible', timeout: remaining() });
  assert.equal(await form.count(), 1);
  for (const selector of Object.values(selectors)) assert.equal(await form.locator(selector).count(), 1);
  return form;
}
export async function inspectSeatsurfingLocationForm(page) {
  return page.locator('form#form').evaluate(form => Array.from(form.elements)
    .filter(el => ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName))
    .map(el => ({ id: el.id, name: el.name, type: el.type, value: el.value,
      disabled: el.disabled, readOnly: !!el.readOnly, required: !!el.required,
      valid: el.validity.valid, validationMessage: el.validationMessage,
      valueMissing: el.validity.valueMissing, patternMismatch: el.validity.patternMismatch,
      tooLong: el.validity.tooLong, tooShort: el.validity.tooShort,
      checked: 'checked' in el ? el.checked : null })));
}
export async function openSeatsurfingLocationEditor(page, { baseUrl, id }) {
  assert.ok(validId(id));
  const remaining = clock();
  const expected = new URL('/location/' + id, baseUrl).href;
  const [response] = await Promise.all([
    page.waitForResponse(r => r.url() === expected && r.request().method() === 'GET', { timeout: remaining() }),
    page.goto(new URL('/ui/admin/locations/' + id + '/', baseUrl).href, { waitUntil: 'domcontentloaded', timeout: remaining() }),
  ]);
  const readback = await response.json();
  assert.equal(response.status(), 200);
  assert.equal(readback.id, id);
  await ready(page, remaining);
  return { readback, form: await inspectSeatsurfingLocationForm(page) };
}
async function submit(page, { baseUrl, method, path, expectedJson, remaining }) {
  const form = await ready(page, remaining);
  const before = await inspectSeatsurfingLocationForm(page);
  const button = page.locator('button[type="submit"][form="form"]');
  assert.equal(await button.count(), 1);
  const actionability = { visible: await button.isVisible(), enabled: await button.isEnabled() };
  if (!actionability.visible || !actionability.enabled) return { observation: 'save_not_actionable', actionability, before, requests: [], qualified: false };
  const url = new URL(path, baseUrl).href;
  const requests = [];
  const listener = request => { if (request.url() === url && request.method() === method) requests.push({ method, url, body: request.postData() }); };
  page.on('request', listener);
  try {
    const invalid = before.some(el => !el.disabled && !el.valid);
    if (invalid) {
      // Read validity without checkValidity/reportValidity or any validity edit.
      // Click the original button once, then retain a bounded observation only.
      await button.click({ timeout: remaining() });
      assert.ok(remaining() > 500);
      await page.waitForTimeout(500);
      return { observation: 'constraint_observation_window', observationMs: 500, actionability,
        before, after: await inspectSeatsurfingLocationForm(page), requests,
        qualified: false, absenceBeyondWindowClaimed: false };
    }
    const [response] = await Promise.all([
      page.waitForResponse(r => r.url() === url && r.request().method() === method, { timeout: remaining() }),
      button.click({ timeout: remaining() }),
    ]);
    const request = response.request();
    const body = request.postData();
    const actual = JSON.parse(body);
    let completePayloadMatches = true;
    try { assert.deepEqual(actual, expectedJson); } catch { completePayloadMatches = false; }
    const responseHeaders = await response.allHeaders();
    const status = response.status();
    const result = { observation: 'main_response_observed', actionability, before,
      request: { method, url, headers: await request.allHeaders(), body },
      response: { status, headers: responseHeaders }, completePayloadMatches,
      requests, qualified: false, ancillaryCompletionEstablished: false };
    if (method === 'POST') {
      const id = responseHeaders['x-object-id'];
      result.createdId = id ?? null;
      result.createdIdValid = validId(id);
    }
    if (status >= 200 && status < 300) {
      try {
        await page.waitForFunction(() => {
          const buttons = document.querySelectorAll('button[type="submit"][form="form"]');
          return buttons.length === 1 && !buttons[0].disabled;
        }, undefined, { timeout: remaining() });
        result.formCompletion = {
          saveEnabled: await button.isEnabled(),
          successAlertVisible: await form.locator('.alert-success').isVisible(),
          errorAlertVisible: await form.locator('.alert-danger').isVisible(),
        };
      } catch (error) {
        result.formCompletion = { observationUnavailable: true, error: error.message };
      }
    }
    // Do not equate the main response or the form's success alert with complete
    // ancillary persistence. Global request settlement remains a separate gate.
    return result;
  } finally { page.off('request', listener); }
}
export async function nativeSeatsurfingOrdinaryCreate(page, { baseUrl, values, expectedJson }) {
  const remaining = clock();
  await page.goto(new URL('/ui/admin/locations/add/', baseUrl).href, { waitUntil: 'domcontentloaded', timeout: remaining() });
  const form = await ready(page, remaining);
  for (const field of ['name', 'description', 'announcement']) {
    assert.equal(typeof values[field], 'string');
    await form.locator(selectors['/' + field]).fill(values[field], { timeout: remaining() });
  }
  return submit(page, { baseUrl, method: 'POST', path: '/location/', expectedJson, remaining });
}
export async function nativeSeatsurfingScalarEdit(page, { baseUrl, id, edit, expectedJson }) {
  assert.ok(validId(id));
  assert.ok(Object.hasOwn(selectors, edit.path));
  assert.equal(typeof edit.value, 'string');
  const remaining = clock();
  const form = await ready(page, remaining);
  // Caller chooses a warm editor or the separately observed reopened editor.
  // This function does not navigate/reload, inject data or reconstruct state.
  await form.locator(selectors[edit.path]).fill(edit.value, { timeout: remaining() });
  return submit(page, { baseUrl, method: 'PUT', path: '/location/' + id, expectedJson, remaining });
}
