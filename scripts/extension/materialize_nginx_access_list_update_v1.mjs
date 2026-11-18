/** Source-derived AccessList update; unqualified until native ordinary equality.
 * Caller supplies an isolated tools directory with the integrity-verified original
 * humps dependency. Passwords come only from persisted API readback, never from
 * the producer request. No native action or application request is executed.
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';

export function materializeNginxAccessListUpdate({ readback, edit, toolsDirectory }) {
  const require = createRequire(resolve(toolsDirectory, 'package.json'));
  assert.equal(require('humps/package.json').version, '2.0.1');
  const { camelizeKeys, decamelizeKeys } = require('humps');
  const data = camelizeKeys(readback);
  assert.ok(Number.isSafeInteger(data.id) && data.id > 0);
  const values = {
    name: data.name,
    satisfyAny: data.satisfyAny,
    passAuth: data.passAuth,
    items: data.items || [],
    clients: data.clients || [],
  };
  assert.equal(typeof edit.value, 'string');
  if (edit.path === '/name') {
    values.name = edit.value;
  } else {
    const match = /^\/(items|clients)\/(0|[1-9][0-9]*)\/(username|address)$/.exec(edit.path);
    assert.ok(match, 'Unsupported unrelated native text control');
    const [, collection, indexText, field] = match;
    assert.equal(field, collection === 'items' ? 'username' : 'address');
    const index = Number(indexText);
    assert.ok(Array.isArray(values[collection]) && index < values[collection].length);
    values[collection] = values[collection].map((item, i) => i === index ? { ...item, [field]: edit.value } : item);
    // AccessClientFields filters the entire local array when any client changes.
    if (collection === 'clients') {
      values.clients = values.clients.filter((client) => client?.address?.trim() !== '');
    }
  }
  // AccessListModal's onSubmit mapping, followed by updateAccessList's removal
  // of id/createdOn/modifiedOn. The five initial form keys are the whole payload.
  const payload = { ...values };
  payload.items = (values.items || [])
    .filter((item) => item.username?.trim() !== '')
    .map((item) => ({ username: item.username, password: item.password }));
  payload.clients = (values.clients || [])
    .map((item) => ({ directive: item.directive, address: item.address }));
  const body = JSON.stringify(decamelizeKeys(payload));
  return { method: 'PUT', path: `/api/nginx/access-lists/${data.id}`, body, json: JSON.parse(body) };
}
