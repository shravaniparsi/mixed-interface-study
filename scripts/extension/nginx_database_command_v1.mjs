/** PRIVATE original-driver checkpoint entrypoint for an offline helper container. */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { captureNginxDatabase, inspectDatabase } from './nginx_sqlite_checkpoint_v1.mjs';

const [operation, databasePath, destination] = process.argv.slice(2);
assert.ok(operation === 'capture' || operation === 'inspect');
assert.equal(typeof databasePath, 'string');
const dependencyRoot = '/app';
let result;
if (operation === 'capture') {
  assert.equal(typeof destination, 'string');
  result = await captureNginxDatabase({ databasePath, destination, dependencyRoot });
} else {
  assert.equal(destination, undefined);
  const require = createRequire(resolve(dependencyRoot, 'package.json'));
  assert.equal(require('better-sqlite3/package.json').version, '13.0.3');
  const Database = require('better-sqlite3');
  const database = new Database(databasePath, { readonly: true, fileMustExist: true, timeout: 5000 });
  try { result = inspectDatabase(database); }
  finally { database.close(); }
}
process.stdout.write(JSON.stringify(result) + '\n');
