/** Offline actor verifier entry point; all inputs and outputs remain private. */
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { verifySeatsurfingActor } from './verify_seatsurfing_actor_v1.mjs';
assert.equal(process.argv.slice(2).length, 2);
const [input, output] = process.argv.slice(2);
const raw = await readFile(input);
assert.ok(raw.length <= 32 * 1024 * 1024);
const report = { inputSha256: createHash('sha256').update(raw).digest('hex'), nodeVersion: process.version };
try {
  report.result = verifySeatsurfingActor(JSON.parse(raw));
  report.status = 'actor_identity_verified';
} catch (error) {
  report.status = 'actor_verification_failed'; report.errorType = error.name; process.exitCode = 1;
}
await writeFile(output, JSON.stringify(report), { flag: 'wx', mode: 0o600 });
