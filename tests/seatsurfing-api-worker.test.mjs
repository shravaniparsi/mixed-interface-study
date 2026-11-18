import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { bindApiStorage, performApiOperation } from '../scripts/extension/seatsurfing_api_worker_v1.mjs';
function storage() { return { cookies: [], origins: [{ origin: 'http://127.0.0.1:8080', localStorage: [{ name: 'accessToken', value: 'token' }, { name: 'refreshToken', value: 'refresh' }, { name: 'accessTokenExpiry', value: String(Date.now() + 900000) }] }] }; }
function bind(value) { const raw = Buffer.from(JSON.stringify(value)); return bindApiStorage(raw, createHash('sha256').update(raw).digest('hex')); }
test('API credentials bind exact original browser storage', () => {
  assert.equal(bind(storage()).accessToken, 'token');
  assert.throws(() => bindApiStorage(Buffer.from('{}'), 'a'.repeat(64)));
});
test('cookies, duplicate credentials, other origins and expired tokens rejected', () => {
  for (const mutate of [x => x.cookies.push({ name: 'session' }), x => x.origins[0].localStorage.push({ name: 'accessToken', value: 'other' }), x => x.origins[0].origin = 'http://elsewhere', x => x.origins[0].localStorage[2].value = '1']) {
    const value = storage(); mutate(value); assert.throws(() => bind(value));
  }
});
test('one ordinary create invocation without target or edit', async () => {
  let count = 0;
  const result = await performApiOperation({ origin: 'http://127.0.0.1:8080', operation: 'ordinary_create' }, { accessToken: 'token' }, { create: async ({ credentials }) => { count++; assert.equal(credentials.accessToken, 'token'); return 'result'; } });
  assert.equal(count, 1); assert.equal(result, 'result');
});
test('loading and continuation use independent acquisition functions', async () => {
  const id = '12345678-1234-1234-1234-123456789abc'; const config = { origin: 'http://127.0.0.1:8080', operation: 'independent_load', id };
  assert.equal(await performApiOperation(config, {}, { load: async input => { assert.equal(input.id, id); return 'loaded'; } }), 'loaded');
  config.operation = 'ordinary_continue'; config.edit = { path: '/description', value: 'Edit description' };
  assert.equal(await performApiOperation(config, {}, { continuation: async input => { assert.deepEqual(input.edit, config.edit); return 'continued'; } }), 'continued');
});
test('unregistered edit rejected before any request', async () => {
  await assert.rejects(performApiOperation({ origin: 'http://127.0.0.1:8080', operation: 'ordinary_continue', id: '12345678-1234-1234-1234-123456789abc', edit: { path: '/name', value: 'arbitrary' } }, {}, { continuation: () => assert.fail('dispatch') }));
});
