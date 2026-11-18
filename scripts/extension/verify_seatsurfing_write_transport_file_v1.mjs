import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { verifyWriteTransport } from './verify_seatsurfing_write_transport_v1.mjs';
assert.equal(process.argv.slice(2).length, 2);
const [input, output] = process.argv.slice(2); const raw = await readFile(input); assert.ok(raw.length <= 33554432);
const report = { inputSha256: createHash('sha256').update(raw).digest('hex'), nodeVersion: process.version };
try { report.result = verifyWriteTransport(JSON.parse(raw)); report.status = 'write_transport_evidence_verified'; }
catch (error) { report.status = 'write_transport_evidence_unavailable'; report.errorType = error.name; process.exitCode = 1; }
await writeFile(output, JSON.stringify(report), { flag: 'wx', mode: 0o600 });
