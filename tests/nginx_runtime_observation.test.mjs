import test from 'node:test';
import assert from 'node:assert/strict';
import { processIdentity, backendEnvironment } from '../scripts/extension/nginx_runtime_observation_v1.mjs';

const status = 'Name:\tnode\nUid:\t1001\t1001\t1001\t1001\nGid:\t121\t121\t121\t121\n';
const fields = ['S', ...Array(18).fill('0'), '123456', '0'];
const stat = `42 (name with ) parentheses) ${fields.join(' ')}`;
const values = {
  PUID:'1001', PGID:'121', NODE_ENV:'production', TZ:'UTC', IP_RANGES_FETCH_ENABLED:'false',
  DISABLE_IPV6:'true', NPM_BUILD_COMMIT:'20016b9d91d49c9133f1b4d26ab5a289c72ec1db',
  INITIAL_ADMIN_PASSWORD:'synthetic-do-not-return',
};
const env = (v=values) => Object.entries(v).map(([k,v]) => `${k}=${v}`).join('\0') + '\0';

test('process identity handles parentheses and retains exact start ticks', () => {
  assert.deepEqual(processIdentity(status, stat, 1001, 121), { uid:1001, gid:121, startTicks:'123456' });
});
test('different real/effective/saved ownership is rejected', () => {
  assert.throws(() => processIdentity(status.replace('1001\t1001', '1001\t0'), stat, 1001, 121));
  assert.throws(() => processIdentity(status.replace('121\t121', '121\t0'), stat, 1001, 121));
});
test('missing identity or malformed process start tick is rejected', () => {
  assert.throws(() => processIdentity('Name:\tnode', stat, 1001, 121));
  assert.throws(() => processIdentity(status, stat.replace('123456', 'unknown'), 1001, 121));
});
test('runtime settings are checked without returning full environment', () => {
  const result = backendEnvironment(env(), 1001, 121);
  assert.equal(result.TZ, 'UTC');
  assert.equal('INITIAL_ADMIN_PASSWORD' in result, false);
  assert.equal(JSON.stringify(result).includes('synthetic-do-not-return'), false);
});
test('test mode, rate-limit bypass and development variables are rejected', () => {
  for (const key of ['CI','DISABLE_RATE_LIMIT','DEVELOPMENT']) {
    assert.throws(() => backendEnvironment(env({...values,[key]:'true'}), 1001, 121));
  }
});
test('wrong revision, IP-fetch policy or duplicate environment is rejected', () => {
  assert.throws(() => backendEnvironment(env({...values,NPM_BUILD_COMMIT:'wrong'}), 1001, 121));
  assert.throws(() => backendEnvironment(env({...values,IP_RANGES_FETCH_ENABLED:'true'}), 1001, 121));
  assert.throws(() => backendEnvironment(env() + 'TZ=UTC\0', 1001, 121));
});
