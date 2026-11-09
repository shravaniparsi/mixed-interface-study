import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const sha = b => createHash('sha256').update(b).digest('hex');
const canonical = v => Array.isArray(v) ? v.map(canonical) : v && typeof v === 'object' ? Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])) : v;
export function validateJob(job, registryBytes, controlsBytes, batch) {
  assert.equal(sha(controlsBytes), '716c5ffeed77f00146038441324a9ba6f4a863681cdd3b1c9e7c23cd9b50800d', 'Control contract differs');
  const controls=JSON.parse(controlsBytes);
  assert.equal(sha(registryBytes), controls.registry_sha256, 'Registry differs');
  assert.ok(controls.batches[batch]?.allowed_jobs.some(j=>JSON.stringify(canonical(j))===JSON.stringify(canonical(job))), 'Unregistered job');
  return job;
}
