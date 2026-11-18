/** Offline build artifact inventory. Never imports application code or starts it. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { lstat, readFile, readdir, readlink, realpath } from 'node:fs/promises';
import { join, resolve } from 'node:path';

const mode = process.argv[2] || 'backend';
const root = resolve(process.argv[3] || '/app');
assert.ok(['backend', 'frontend'].includes(mode));
assert.equal(await realpath(root), root);
const limits = { entries: 100000, bytes: 2 * 1024 * 1024 * 1024 };
const rows = [];
let bytes = 0;

async function fileHash(file) {
  const hash = createHash('sha256');
  for await (const chunk of createReadStream(file)) hash.update(chunk);
  return hash.digest('hex');
}

async function visit(relative) {
  const path = join(root, relative);
  const info = await lstat(path);
  assert.ok(rows.length < limits.entries, 'Inventory entry bound');
  const row = { path: relative || '.', mode: info.mode & 0o7777 };
  rows.push(row);
  if (info.isSymbolicLink()) {
    row.kind = 'symlink'; row.target = await readlink(path);
  } else if (info.isDirectory()) {
    row.kind = 'directory';
    for (const name of (await readdir(path)).sort()) await visit(join(relative, name));
  } else {
    assert.ok(info.isFile(), 'Unexpected installed artifact type');
    bytes += info.size;
    assert.ok(bytes <= limits.bytes, 'Inventory byte bound');
    row.kind = 'file'; row.bytes = info.size; row.sha256 = await fileHash(path);
  }
}

await visit('');
const pkg = JSON.parse(await readFile(join(root, 'package.json'), 'utf8'));
const expected = mode === 'backend'
  ? { ajv: '8.20.0', '@apidevtools/json-schema-ref-parser': '16.0.6', 'better-sqlite3': '13.0.3', knex: '3.3.0', objection: '4.4.3' }
  : { humps: '2.0.1', formik: '2.4.9' };
const dependencies = {};
for (const name of Object.keys(pkg.dependencies).sort()) {
  const installed = JSON.parse(await readFile(join(root, 'node_modules', name, 'package.json'), 'utf8'));
  dependencies[name] = installed.version;
  if (name in expected) assert.equal(installed.version, expected[name], name);
}
for (const name of Object.keys(expected)) assert.ok(name in dependencies);
const sha = (data) => createHash('sha256').update(data).digest('hex');
const lockHash = await fileHash(join(root, 'yarn.lock'));
if (mode === 'backend') assert.equal(lockHash, '35a1f00939af0ef3738d39d4a3486a132b65b3621d2203d17ee8d3c9f3b2e44b');
const index = mode === 'backend' ? 'frontend/index.html' : 'dist/index.html';
assert.ok(rows.some((r) => r.path === index && r.kind === 'file'));
process.stdout.write(JSON.stringify({ status: 'installed_build_inventory_only', mode, root,
  node: process.version, packageVersion: pkg.version, dependencies, lockSha256: lockHash,
  totalFileBytes: bytes, inventorySha256: sha(JSON.stringify(rows)), rows }) + '\n');
