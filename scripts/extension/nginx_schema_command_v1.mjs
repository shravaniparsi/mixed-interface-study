/** Private original-schema invocation; caller owns image/source integrity. */
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { loadOriginalNginxSchemaBaseline } from './nginx_original_schema_v1.mjs';
assert.equal(process.argv.slice(2).length, 1);
const input = JSON.parse(await readFile(process.argv[2], 'utf8'));
const validate = await loadOriginalNginxSchemaBaseline('/app');
process.stdout.write(JSON.stringify(await validate(input)) + '\n');
