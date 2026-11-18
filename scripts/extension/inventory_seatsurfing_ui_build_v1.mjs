/** Offline inspector: reads installed UI dependencies, imports no app code. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { lstat, readdir, readFile, readlink, realpath } from 'node:fs/promises';
import { createReadStream } from 'node:fs';
import { join, relative } from 'node:path';
const root = '/app/node_modules';
let bytes = 0;
const files = [], packages = [];
async function visit(directory) {
  for (const name of (await readdir(directory)).sort()) {
    const path = join(directory, name), stat = await lstat(path);
    const item = { path: relative(root, path), mode: stat.mode & 0o7777 };
    if (stat.isDirectory()) { await visit(path); continue; }
    assert.ok(files.length < 100000, 'UI dependency file bound');
    if (stat.isSymbolicLink()) { assert.ok((await realpath(path)).startsWith(root + '/'), 'Dependency link escapes installed tree'); files.push({ ...item, kind: 'symlink', target: await readlink(path) }); continue; }
    assert.ok(stat.isFile(), 'Unsupported UI dependency file kind');
    bytes += stat.size; assert.ok(bytes <= 2 * 1024 ** 3, 'UI dependency byte bound');
    const hash = createHash('sha256');
    for await (const chunk of createReadStream(path)) hash.update(chunk);
    files.push({ ...item, kind: 'file', bytes: stat.size, sha256: hash.digest('hex') });
    if (name === 'package.json') {
      assert.ok(stat.size <= 1048576);
      const parsed = JSON.parse(await readFile(path, 'utf8'));
      packages.push({ path: item.path, name: parsed.name ?? null, version: parsed.version ?? null });
    }
  }
}
await visit(root);
assert.ok(files.length && packages.length);
const lock = await readFile('/app/package-lock.json');
process.stdout.write(JSON.stringify({ node: process.version, files, packages, totalFileBytes: bytes,
  lockSha256: createHash('sha256').update(lock).digest('hex'), applicationImported: false }) + '\n');
