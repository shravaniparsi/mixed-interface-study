/** Offline comparison of both retained native branches against the API branch. */
import assert from 'node:assert/strict';
import { readFile, writeFile, lstat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { compareContinuationRequests } from './compare_seatsurfing_continuation_requests_v1.mjs';
assert.equal(process.argv.slice(2).length, 5);
const [warmPath, nativePath, apiPath, storagePath, output] = process.argv.slice(2);
const report = { status: 'comparison_pending', nodeVersion: process.version, runtimeQualified: false, inputHashes: {} };
try {
  const values = {};
  for (const [name, path, limit] of [['warm', warmPath, 33554432], ['native', nativePath, 33554432], ['api', apiPath, 16777216], ['storage', storagePath, 1048576]]) {
    const info = await lstat(path); assert.equal(info.isSymbolicLink(), false); assert.equal(info.isFile(), true); assert.ok(info.size <= limit);
    const raw = await readFile(path); report.inputHashes[name] = createHash('sha256').update(raw).digest('hex'); values[name] = JSON.parse(raw);
  }
  assert.deepEqual(values.storage.cookies, []);
  assert.equal(values.storage.origins.length, 1);
  assert.equal(values.storage.origins[0].origin, 'http://127.0.0.1:8080');
  const entries = values.storage.origins[0].localStorage;
  assert.equal(new Set(entries.map(x => x.name)).size, entries.length);
  const accessToken = Object.fromEntries(entries.map(x => [x.name, x.value])).accessToken;
  assert.ok(typeof accessToken === 'string' && accessToken.length > 0);
  assert.equal(values.api.status, 'api_operation_observed');
  assert.equal(values.api.operation, 'ordinary_continue');
  report.warm = compareContinuationRequests({ native: values.warm, api: values.api.result, accessToken });
  report.restoredNative = compareContinuationRequests({ native: values.native, api: values.api.result, accessToken });
  report.status = 'both_native_write_plans_match_independent_api';
} catch (error) {
  report.status = 'request_comparison_unavailable'; report.errorType = error.name; process.exitCode = 1;
}
const raw = JSON.stringify(report); assert.ok(Buffer.byteLength(raw) <= 33554432);
await writeFile(output, raw, { flag: 'wx', mode: 0o600 });
