import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const sha = b => createHash('sha256').update(b).digest('hex');
const canonical = v => Array.isArray(v) ? v.map(canonical) : v && typeof v === 'object' ? Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])) : v;
export function validateJob(job, registryBytes, controlsBytes) {
  assert.equal(sha(controlsBytes), 'b7b5751dcdb6437c64d903964b1817be6fc08675a95eba6cc5837344fa1707ae', 'Control contract differs');
  const controls=JSON.parse(controlsBytes);
  assert.equal(sha(registryBytes), controls.registry_sha256, 'Registry differs');
  assert.ok(controls.allowed_jobs.some(j=>JSON.stringify(canonical(j))===JSON.stringify(canonical(job))), 'Unregistered job');
  return job;
}
