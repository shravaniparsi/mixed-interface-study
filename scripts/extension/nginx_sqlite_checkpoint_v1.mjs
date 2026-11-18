/** PRIVATE database evidence: may contain password hashes and user records.
 * Uses the application's integrity-verified better-sqlite3 13.0.3. This helper
 * alone does not coordinate filesystem snapshots or qualify restoration.
 */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { createHash } from 'node:crypto';

export function encodeSqliteValue(value) {
  if (value === null) return ['null'];
  if (typeof value === 'bigint') return ['integer', value.toString()];
  if (typeof value === 'number') return ['real', Object.is(value, -0) ? '-0' : String(value)];
  if (typeof value === 'string') return ['text', value];
  if (Buffer.isBuffer(value)) return ['blob', value.toString('base64')];
  throw new TypeError('Unsupported SQLite result type');
}
const sha256 = (value) => createHash('sha256').update(value).digest('hex');
const quote = (value) => '"' + value.replaceAll('"', '""') + '"';

export function inspectDatabase(db) {
  return db.transaction(() => {
    assert.equal(db.pragma('integrity_check', { simple: true }), 'ok');
    const schema = db.prepare('SELECT type, name, tbl_name, rootpage, sql FROM sqlite_schema ORDER BY type, name').raw().safeIntegers().all();
    assert.ok(schema.length <= 2000, 'Schema evidence bound');
    const tables = [];
    let rowCount = 0;
    let encodedBytes = 0;
    for (const row of schema.filter((row) => row[0] === 'table')) {
      const name = row[1];
      const columns = db.prepare(`PRAGMA table_xinfo(${quote(name)})`).raw().safeIntegers().all();
      const encodedRows = [];
      for (const values of db.prepare(`SELECT * FROM ${quote(name)}`).raw().safeIntegers().iterate()) {
        const encoded = JSON.stringify(values.map(encodeSqliteValue));
        rowCount += 1;
        encodedBytes += Buffer.byteLength(encoded);
        assert.ok(rowCount <= 100000 && encodedBytes <= 32 * 1024 * 1024, 'Database evidence bound');
        encodedRows.push(encoded);
      }
      // Preserve duplicate rows and SQLite integer/text/blob distinctions.
      encodedRows.sort();
      tables.push({ name, columns: columns.map((r) => r.map(encodeSqliteValue)), rows: encodedRows });
    }
    const state = { schema: schema.map((r) => r.map(encodeSqliteValue)), tables };
    return { state, sha256: sha256(JSON.stringify(state)), rowCount,
      sqliteVersion: db.prepare('SELECT sqlite_version() AS version').get().version };
  })();
}

export async function captureNginxDatabase({ databasePath, destination, dependencyRoot }) {
  assert.notEqual(resolve(databasePath), resolve(destination));
  assert.equal(existsSync(destination), false, 'Never overwrite a backup');
  const require = createRequire(resolve(dependencyRoot, 'package.json'));
  assert.equal(require('better-sqlite3/package.json').version, '13.0.3');
  const Database = require('better-sqlite3');
  const source = new Database(databasePath, { readonly: true, fileMustExist: true, timeout: 5000 });
  let backup;
  let timer;
  try {
    const before = inspectDatabase(source);
    const pageSize = source.pragma('page_size', { simple: true });
    timer = setTimeout(() => { if (source.open) source.close(); }, 20000);
    const result = await source.backup(destination, { progress({ totalPages }) {
      assert.ok(totalPages * pageSize <= 64 * 1024 * 1024, 'Backup byte bound');
      return 100;
    } });
    clearTimeout(timer);
    assert.equal(result.remainingPages, 0);
    const after = inspectDatabase(source);
    backup = new Database(destination, { readonly: true, fileMustExist: true, timeout: 5000 });
    const copied = inspectDatabase(backup);
    assert.deepEqual(after.state, before.state, 'Source changed across checkpoint');
    assert.deepEqual(copied.state, before.state, 'Backup differs from source checkpoint');
    return { before, after, copied, backupSha256: sha256(readFileSync(destination)),
      driverVersion: '13.0.3', status: 'database_checkpoint_only_filesystem_and_restore_unqualified' };
  } finally {
    clearTimeout(timer);
    if (backup?.open) backup.close();
    if (source.open) source.close();
  }
}
