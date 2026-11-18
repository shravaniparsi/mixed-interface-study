/** Ordinary native controls only. Returned envelopes contain secrets: keep private.
 * Caller supplies the pinned browser, isolated service, actor and checkpoint phases.
 * No launch, authentication bypass, force click or scientific dispatch occurs here.
 */
import assert from 'node:assert/strict';
import { materializeViseronUserUpdate } from './materialize_viseron_user_update_v1.mjs';

function matches(response, method, path) {
  return response.request().method() === method && new URL(response.url()).pathname === path;
}

async function envelope(response) {
  const request = response.request();
  return {
    method: request.method(), path: new URL(request.url()).pathname,
    headers: await request.allHeaders(), body: request.postDataJSON(),
    status: response.status(), response: await response.json(),
  };
}

export async function nativeCreate(page, origin, producer) {
  assert.deepEqual(Object.keys(producer).sort(), ['name', 'password', 'role', 'username']);
  assert.equal(producer.role, 'read');
  await page.goto(`${origin}/#/settings/users`, { waitUntil: 'domcontentloaded' });
  const add = page.getByRole('button', { name: 'add', exact: true });
  await add.waitFor({ state: 'visible' });
  assert.equal(await add.count(), 1);
  assert.equal(await add.isEnabled(), true);
  await add.click();
  const dialog = page.getByRole('dialog');
  await dialog.waitFor({ state: 'visible' });
  assert.equal(await dialog.count(), 1);
  await dialog.getByLabel('Display Name', { exact: true }).fill(producer.name);
  await dialog.getByLabel('Username', { exact: true }).fill(producer.username);
  await dialog.getByLabel('Password', { exact: true }).fill(producer.password);
  await dialog.getByLabel('Confirm Password', { exact: true }).fill(producer.password);
  // Preserve the original default rather than programmatically setting React state.
  assert.equal((await dialog.getByRole('combobox', { name: 'Role', exact: true }).innerText()).trim(), 'Read');
  const submit = dialog.getByRole('button', { name: 'Add', exact: true });
  assert.equal(await submit.isEnabled(), true);
  const response = page.waitForResponse((r) => matches(r, 'POST', '/api/v1/auth/create'));
  await submit.click();
  const observed = await envelope(await response);
  assert.deepEqual(observed.body, producer);
  assert.equal(observed.status, 200);
  assert.deepEqual(observed.response, { success: true });
  await dialog.waitFor({ state: 'hidden' });
  return observed;
}

export async function nativeEdit(page, origin, user, edit) {
  const materialized = materializeViseronUserUpdate(user, edit);
  await page.goto(`${origin}/#/settings/users`, { waitUntil: 'domcontentloaded' });
  const row = page.getByRole('button').filter({ has: page.getByText(user.username, { exact: true }) });
  await row.waitFor({ state: 'visible' });
  assert.equal(await row.count(), 1);
  await row.click();
  const dialog = page.getByRole('dialog');
  await dialog.waitFor({ state: 'visible' });
  assert.equal(await dialog.count(), 1);
  assert.equal(await dialog.getByLabel('Display Name', { exact: true }).inputValue(), user.name);
  assert.equal(await dialog.getByLabel('Username', { exact: true }).inputValue(), user.username);
  await dialog.getByLabel(edit.field === 'name' ? 'Display Name' : 'Username', { exact: true }).fill(edit.value);
  const save = dialog.getByRole('button', { name: 'Save', exact: true });
  const actionability = { visible: await save.isVisible(), enabled: await save.isEnabled() };
  assert.equal(actionability.visible, true);
  assert.equal(actionability.enabled, true);
  const path = '/api/v1' + materialized.api_relative_path;
  const response = page.waitForResponse((r) => matches(r, 'PUT', path));
  await save.click();
  const observed = await envelope(await response);
  assert.equal(observed.method, materialized.method);
  assert.equal(observed.path, path);
  assert.deepEqual(observed.body, materialized.body);
  assert.equal(observed.status, 200);
  assert.deepEqual(observed.response, { success: true });
  await dialog.waitFor({ state: 'hidden' });
  return { actionability, materialized, observed };
}

export function verifyOrdinaryReadback(user, producer) {
  // Materializer verifies the supported complete user representation as well.
  materializeViseronUserUpdate(user, { field: 'name', value: producer.name });
  assert.deepEqual(Object.keys(user).sort(), ['assigned_cameras', 'enabled', 'id', 'name', 'preferences', 'role', 'username']);
  assert.deepEqual(user, { id: user.id, name: producer.name, username: producer.username,
    role: producer.role, enabled: true, assigned_cameras: null, preferences: null });
}

export function verifyContinuationReadback(before, after, edit) {
  assert.deepEqual(after, { ...before, [edit.field]: edit.value });
}
