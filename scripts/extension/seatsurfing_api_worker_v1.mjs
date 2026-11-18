/** One registered ordinary API operation in the isolated fixture namespace. */
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { createSeatsurfingOrdinaryApi } from './create_seatsurfing_ordinary_api_v1.mjs';
import { loadSeatsurfingApiState } from './load_seatsurfing_api_state_v1.mjs';
import { runSeatsurfingApiContinuation } from './run_seatsurfing_api_continuation_v1.mjs';

export function bindApiStorage(raw, expectedSha256) {
  assert.equal(createHash('sha256').update(raw).digest('hex'), expectedSha256);
  const storage = JSON.parse(raw);
  assert.deepEqual(storage.cookies, [], 'Cookies require separate transport qualification');
  assert.equal(storage.origins.length, 1);
  assert.equal(storage.origins[0].origin, 'http://127.0.0.1:8080');
  const entries = storage.origins[0].localStorage;
  assert.equal(new Set(entries.map(x => x.name)).size, entries.length);
  const values = Object.fromEntries(entries.map(x => [x.name, x.value]));
  assert.ok(typeof values.accessToken === 'string' && values.accessToken.length > 0);
  assert.ok(typeof values.refreshToken === 'string' && values.refreshToken.length > 0);
  const accessTokenExpiryMs = Number(values.accessTokenExpiry);
  assert.ok(Number.isFinite(accessTokenExpiryMs) && accessTokenExpiryMs > Date.now() + 210000);
  return { accessToken: values.accessToken, accessTokenExpiryMs };
}

export async function performApiOperation(config, credentials, dependencies = {}) {
  assert.equal(config.origin, 'http://127.0.0.1:8080');
  assert.ok(['ordinary_create', 'independent_load', 'ordinary_continue'].includes(config.operation));
  const functions = { create: createSeatsurfingOrdinaryApi, load: loadSeatsurfingApiState, continuation: runSeatsurfingApiContinuation, ...dependencies };
  if (config.operation === 'ordinary_create') {
    assert.equal(Object.hasOwn(config, 'id'), false); assert.equal(Object.hasOwn(config, 'edit'), false);
    return functions.create({ credentials });
  }
  assert.match(config.id, /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
  if (config.operation === 'independent_load') {
    assert.equal(Object.hasOwn(config, 'edit'), false);
    return functions.load({ id: config.id, credentials });
  }
  const edits = [{ path: '/description', value: 'Edit description' }, { path: '/announcement', value: 'Edit notice' }];
  assert.ok(edits.some(edit => JSON.stringify(edit) === JSON.stringify(config.edit)));
  return functions.continuation({ id: config.id, credentials, edit: config.edit });
}

async function main() {
  assert.equal(process.version, 'v24.18.1');
  assert.equal(Intl.DateTimeFormat().resolvedOptions().timeZone, 'UTC');
  assert.deepEqual(process.argv.slice(2), ['/input/config.json', '/input/storage.json', '/evidence/result.json']);
  const rawConfig = await readFile('/input/config.json');
  const rawStorage = await readFile('/input/storage.json');
  assert.ok(rawConfig.length <= 65536 && rawStorage.length <= 1048576);
  const config = JSON.parse(rawConfig);
  const report = { operation: config.operation, storageSha256: config.storageSha256,
    configSha256: createHash('sha256').update(rawConfig).digest('hex'), retryCount: 0, runtimeQualified: false };
  // Parent also enforces a longer process deadline. This does not retry on a
  // hanging process and must not convert a partial mutation into a rejection.
  const deadline = setTimeout(() => process.exit(124), 85000);
  try {
    const credentials = bindApiStorage(rawStorage, config.storageSha256);
    report.result = await performApiOperation(config, credentials);
    report.status = 'api_operation_observed';
  } catch (error) {
    report.status = 'api_instrument_failure';
    report.error = { name: error.name, message: error.message };
    process.exitCode = 1;
  } finally {
    clearTimeout(deadline);
    const bytes = JSON.stringify(report);
    assert.ok(Buffer.byteLength(bytes) <= 16 * 1024 * 1024);
    await writeFile('/evidence/result.json', bytes, { flag: 'wx', mode: 0o600 });
  }
}
// Importing this module for synthetic tests never launches a request.
if (process.argv[1]?.endsWith('/seatsurfing_api_worker_v1.mjs')) {
  main().catch(() => { process.stderr.write('API worker initialization or retention failed\n'); process.exitCode = 1; });
}
