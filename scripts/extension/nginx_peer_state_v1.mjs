/** Exact source-template/peer-secret checks; not application qualification.
 * Reads environment only for the unique original /app node index.js process.
 * No secret values or raw process environments are returned or printed.
 */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync, readlinkSync } from 'node:fs';
import { basename } from 'node:path';
const TEMPLATE_SHA256 = 'e5afb7b37e50ea5eaf4bf982fa7e289236b2460c56658748af541806882c919c';
const sha = (value) => createHash('sha256').update(value).digest('hex');

export function verifyPeerConfiguration({ template, configuration, secret, backendEnvironment, disableIpv6 = false }) {
  assert.equal(sha(template), TEMPLATE_SHA256, 'Original proxy template identity changed');
  assert.match(secret, /^[0-9a-f]{64}$/, 'Expected exact original 32-byte hex secret');
  const entries = backendEnvironment.split('\0').filter((s) => s.startsWith('NPM_PEER_SECRET='));
  assert.equal(entries.length, 1, 'Backend peer-secret environment entry must be unique');
  assert.equal(entries[0].slice('NPM_PEER_SECRET='.length), secret, 'Proxy and actual backend secret differ');
  assert.equal(typeof disableIpv6, 'boolean');
  let expected = template.replaceAll('{{NPM_ADMIN_PORT}}', '81').replaceAll('{{NPM_PEER_SECRET}}', secret);
  // Original prepare/50-ipv6.sh transforms complete configuration lines.
  expected = expected.split('\n').map((line) => disableIpv6
    ? line.replace(/^([^#]*)listen \[::\]/, '$1#listen [::]')
    : line.replace(/^(\s*)#listen \[::\]/, '$1listen [::]')).join('\n');
  assert.equal(configuration, expected, 'Generated proxy configuration contains an unexplained difference');
  assert.equal(configuration.split(secret).length - 1, 1);
  return { templateSha256: TEMPLATE_SHA256, configurationSha256: sha(configuration),
    normalizedConfigurationSha256: sha(configuration.replace(secret, '{{NPM_PEER_SECRET}}')),
    backendSecretMatches: true, adminPort: 81, disableIpv6 };
}

export function inspectPeerState({ originalTemplatePath, disableIpv6 = false }) {
  const candidates = [];
  for (const entry of readdirSync('/proc').filter((s) => /^[0-9]+$/.test(s))) {
    try {
      const args = readFileSync(`/proc/${entry}/cmdline`, 'utf8').split('\0').filter(Boolean);
      if (args.length && basename(args[0]) === 'node' && args.at(-1) === 'index.js' &&
          readlinkSync(`/proc/${entry}/cwd`) === '/app') candidates.push(entry);
    } catch (error) {
      if (error.code !== 'ENOENT' && error.code !== 'ESRCH') throw error;
    }
  }
  assert.equal(candidates.length, 1, 'Require one identifiable original backend process');
  const pid = candidates[0];
  const result = verifyPeerConfiguration({
    template: readFileSync(originalTemplatePath, 'utf8'),
    configuration: readFileSync('/etc/nginx/conf.d/production.conf', 'utf8'),
    secret: readFileSync('/var/run/s6/container_environment/NPM_PEER_SECRET', 'utf8'),
    backendEnvironment: readFileSync(`/proc/${pid}/environ`, 'utf8'), disableIpv6,
  });
  return { ...result, backendPid: Number(pid), status: 'peer_configuration_consistent_runtime_comparison_unqualified' };
}
