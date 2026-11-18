/** PRIVATE live runtime observation, not an atomic checkpoint or qualification.
 * Invoked by the future coordinator inside the original application container.
 * It reads state only and never starts/reloads nginx or modifies the application.
 */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { createReadStream } from 'node:fs';
import { lstat, readFile, readdir, readlink, realpath } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { inspectPeerState } from './nginx_peer_state_v1.mjs';

const ROOTS = ['/data', '/etc/letsencrypt', '/etc/nginx', '/tmp/nginx', '/var/lib/nginx/cache',
  '/var/cache/nginx', '/var/log/nginx', '/run/nginx', '/var/lib/logrotate'];
const REVISION = '20016b9d91d49c9133f1b4d26ab5a289c72ec1db';
const CONFIG = {
  '/etc/nginx/nginx.conf': '964daf41a24278eecfa5afae38005ac187075ca50d8a61e2ce4859562ab9b0ea',
  '/etc/nginx/conf.d/include/log-proxy.conf': 'd9985f766e4fec5902730acfa567a9c430aac1e7fad7d89720ecb8962b9f948f',
  '/etc/nginx/conf.d/include/log-stream.conf': 'a460455d0d1c6ec9c892c8a6ab1432bf76ec51efc8cee2b14d835d78aee4a76a',
};

export function processIdentity(status, stat, expectedUid, expectedGid) {
  const uid = /^Uid:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$/m.exec(status);
  const gid = /^Gid:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$/m.exec(status);
  assert.ok(uid && gid, 'Process ownership fields missing');
  assert.ok(uid.slice(1).every((v) => v === String(expectedUid)), 'Unexpected process UID');
  assert.ok(gid.slice(1).every((v) => v === String(expectedGid)), 'Unexpected process GID');
  const close = stat.lastIndexOf(')');
  assert.ok(close >= 0);
  const fields = stat.slice(close + 1).trim().split(/\s+/);
  assert.ok(fields.length >= 20 && /^\d+$/.test(fields[19]));
  return { uid: expectedUid, gid: expectedGid, startTicks: fields[19] };
}

export function backendEnvironment(raw, uid, gid) {
  const values = new Map();
  for (const entry of raw.split('\0').filter(Boolean)) {
    const index = entry.indexOf('=');
    assert.ok(index > 0, 'Malformed process environment');
    const key = entry.slice(0, index);
    assert.equal(values.has(key), false, 'Duplicate process environment key');
    values.set(key, entry.slice(index + 1));
  }
  const expected = { PUID: String(uid), PGID: String(gid), NODE_ENV: 'production', TZ: 'UTC',
    IP_RANGES_FETCH_ENABLED: 'false', DISABLE_IPV6: 'true', NPM_BUILD_COMMIT: REVISION };
  for (const [key, value] of Object.entries(expected)) assert.equal(values.get(key), value, key);
  for (const key of ['CI', 'DISABLE_RATE_LIMIT', 'DEVELOPMENT']) assert.equal(values.has(key), false, `${key} must be absent`);
  return expected; // Never return full environment or initial admin credentials.
}

async function hashFile(path) {
  const hash = createHash('sha256');
  for await (const chunk of createReadStream(path)) hash.update(chunk);
  return hash.digest('hex');
}

async function processState(pid, uid, gid) {
  const base = `/proc/${pid}`;
  const identity = processIdentity(await readFile(`${base}/status`, 'utf8'), await readFile(`${base}/stat`, 'utf8'), uid, gid);
  const executable = await readlink(`${base}/exe`);
  return { pid, ...identity, executable, executableSha256: await hashFile(executable),
    argv: (await readFile(`${base}/cmdline`, 'utf8')).split('\0').filter(Boolean),
    cwd: await readlink(`${base}/cwd`) };
}

export async function observeRuntime(uid, gid) {
  assert.ok(Number.isSafeInteger(uid) && uid > 0 && Number.isSafeInteger(gid) && gid > 0);
  const startedAtMs = Date.now();
  const peer = inspectPeerState({ originalTemplatePath: '/etc/nginx/conf.d/production.conf.template', disableIpv6: true });
  const backend = await processState(peer.backendPid, uid, gid);
  assert.equal(backend.cwd, '/app');
  const environment = backendEnvironment(await readFile(`/proc/${peer.backendPid}/environ`, 'utf8'), uid, gid);
  const masterText = (await readFile('/run/nginx/nginx.pid', 'utf8')).trim();
  assert.match(masterText, /^[1-9][0-9]*$/);
  const master = await processState(Number(masterText), uid, gid);
  assert.equal(master.executable, await realpath('/usr/sbin/nginx'));
  assert.ok(master.argv.join(' ').includes('nginx: master process'));
  for (const [path, digest] of Object.entries(CONFIG)) assert.equal(await hashFile(path), digest, path);
  const inventories = {};
  const observedPaths = [];
  let totalBytes = 0;
  for (const root of ROOTS) {
    assert.equal(await realpath(root), root, 'Registered root must be canonical');
    const rows = [];
    const visit = async (relative) => {
      const path = join(root, relative);
      const info = await lstat(path, { bigint: true });
      observedPaths.push(path);
      assert.ok(observedPaths.length <= 40000, 'Runtime inventory entry bound');
      const row = { path: relative || '.', mode: Number(info.mode & 0o7777n), uid: Number(info.uid), gid: Number(info.gid), mtimeNs: info.mtimeNs.toString() };
      rows.push(row);
      if (info.isSymbolicLink()) {
        row.kind = 'symlink'; row.target = await readlink(path);
      } else if (info.isDirectory()) {
        row.kind = 'directory';
        for (const name of (await readdir(path)).sort()) await visit(join(relative, name));
      } else {
        assert.ok(info.isFile() && info.nlink === 1n, 'Unsupported runtime file kind/hard link');
        totalBytes += Number(info.size);
        assert.ok(totalBytes <= 1024 * 1024 * 1024, 'Runtime inventory byte bound');
        row.kind = 'file'; row.bytes = Number(info.size); row.sha256 = await hashFile(path);
        const after = await lstat(path, { bigint: true });
        for (const field of ['dev', 'ino', 'mode', 'uid', 'gid', 'size', 'mtimeNs', 'ctimeNs']) {
          assert.equal(after[field], info[field], 'File changed while being observed');
        }
      }
    };
    await visit(''); inventories[root] = rows;
  }
  // The image contains Python for its original certbot runtime. If native xattr
  // inspection is unavailable, fail rather than silently omitting attributes.
  const xattrCheck = execFileSync('python3', ['-c',
    'import json,os,sys\npaths=json.load(sys.stdin)\nassert hasattr(os,"listxattr")\nassert all(not os.listxattr(p,follow_symlinks=False) for p in paths)\nprint(len(paths))'],
    { input: JSON.stringify(observedPaths), encoding: 'utf8', timeout: 15000, maxBuffer: 1024 * 1024 });
  assert.equal(Number(xattrCheck.trim()), observedPaths.length);
  assert.deepEqual(await processState(peer.backendPid, uid, gid), backend, 'Backend process changed across observation');
  assert.deepEqual(await processState(Number(masterText), uid, gid), master, 'Nginx master changed across observation');
  assert.deepEqual(inspectPeerState({ originalTemplatePath: '/etc/nginx/conf.d/production.conf.template', disableIpv6: true }), peer);
  return { status: 'runtime_observation_only_not_atomic_or_qualified', startedAtMs, endedAtMs: Date.now(),
    backend, master, environment, peer, inventories, totalBytes, extendedAttributesAbsent: true };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  assert.equal(process.argv.slice(2).length, 2);
  process.stdout.write(JSON.stringify(await observeRuntime(Number(process.argv[2]), Number(process.argv[3]))) + '\n');
}
