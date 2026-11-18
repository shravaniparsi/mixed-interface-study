import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { verifyPeerConfiguration } from './nginx_peer_state_v1.mjs';
const template = readFileSync(new URL('../../results/catalog-source-wave22-v1/8.txt', import.meta.url), 'utf8');
function fixture(secret = 'a'.repeat(64), disableIpv6 = false) {
  let configuration = template.replaceAll('{{NPM_ADMIN_PORT}}', '81').replaceAll('{{NPM_PEER_SECRET}}', secret);
  if (disableIpv6) configuration = configuration.replace('\tlisten [::]:81 default;', '\t#listen [::]:81 default;');
  return { template, configuration, secret, backendEnvironment: `OTHER=unreturned\0NPM_PEER_SECRET=${secret}\0`, disableIpv6 };
}
test('different valid startup secrets yield identical normalized configuration', () => {
  const first = verifyPeerConfiguration(fixture());
  const second = verifyPeerConfiguration(fixture('b'.repeat(64)));
  assert.notEqual(first.configurationSha256, second.configurationSha256);
  assert.equal(first.normalizedConfigurationSha256, second.normalizedConfigurationSha256);
  assert.ok(!JSON.stringify(first).includes('a'.repeat(64)));
});
test('rejects backend secret mismatch and duplicate environment entries', () => {
  const input = fixture(); input.backendEnvironment = 'NPM_PEER_SECRET=' + 'b'.repeat(64) + '\0';
  assert.throws(() => verifyPeerConfiguration(input));
  input.backendEnvironment = `NPM_PEER_SECRET=${input.secret}\0NPM_PEER_SECRET=${input.secret}\0`;
  assert.throws(() => verifyPeerConfiguration(input));
});
test('rejects unrelated configuration edits and changed source template', () => {
  const input = fixture(); input.configuration = input.configuration.replace('127.0.0.1:3000', '127.0.0.1:3999');
  assert.throws(() => verifyPeerConfiguration(input));
  assert.throws(() => verifyPeerConfiguration({ ...fixture(), template: template + '\n' }));
});
test('permits only the declared original IPv6 transformation', () => {
  assert.equal(verifyPeerConfiguration(fixture('a'.repeat(64), true)).disableIpv6, true);
  assert.throws(() => verifyPeerConfiguration({ ...fixture('a'.repeat(64), true), disableIpv6: false }));
});
