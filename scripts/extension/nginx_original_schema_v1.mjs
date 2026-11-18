/** S baseline: execute the original API validator without starting the server.
 * Caller must first verify the full frozen source tree and installed dependency
 * integrity, and run in the isolated application runtime. No fallback validator.
 * Returned payloads/errors can contain synthetic credentials: keep raw privately.
 */
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const IDENTITIES = {
  'lib/validator/api.js': '9194268ef2ab3c914a5751cb8978400d0f07c4fe8cb9d1ced2f34f6f510bdcf5',
  'schema/index.js': '4a8fe3c1d3656f8dbc9c06f85aa9768136f97fe6637c9c7a583f46a82757fbc3',
  'lib/error.js': 'e80bd5c30b857f6aa9549c1269cea4cb5bc7e0683bca85e6a8e3b4f3411d4153',
  'package.json': 'f36ae3827414ec425e76bb18b1767dfa9293c72cc0b1267b5122b0ec753b1afa',
  'yarn.lock': '35a1f00939af0ef3738d39d4a3486a132b65b3621d2203d17ee8d3c9f3b2e44b',
};

export async function loadOriginalNginxSchemaBaseline(backendDirectory) {
  const root = resolve(backendDirectory);
  for (const [file, digest] of Object.entries(IDENTITIES)) {
    const bytes = await readFile(resolve(root, file));
    assert.equal(createHash('sha256').update(bytes).digest('hex'), digest, file);
  }
  const versions = {};
  for (const [dependency, version] of Object.entries({ ajv: '8.20.0', '@apidevtools/json-schema-ref-parser': '16.0.6' })) {
    const pkg = JSON.parse(await readFile(resolve(root, 'node_modules', dependency, 'package.json'), 'utf8'));
    assert.equal(pkg.version, version, dependency);
    versions[dependency] = pkg.version;
  }
  const originalImport = (file) => import(pathToFileURL(resolve(root, file)).href);
  const { default: validate } = await originalImport('lib/validator/api.js');
  const { default: errors } = await originalImport('lib/error.js');
  const { getCompiledSchema, getValidationSchema } = await originalImport('schema/index.js');
  await getCompiledSchema();
  return async ({ method, body }) => {
    assert.ok(method === 'POST' || method === 'PUT');
    // Use the exact JSON sent on the wire. Ajv may coerce this clone; it must not
    // change H's producer body or the complete native/API continuation request.
    assert.equal(typeof body, 'string');
    const input = JSON.parse(body);
    const candidate = JSON.parse(body);
    const path = method === 'POST' ? '/nginx/access-lists' : '/nginx/access-lists/{listID}';
    const schema = getValidationSchema(path, method.toLowerCase());
    assert.ok(schema, 'Original operation schema unavailable');
    try {
      const output = await validate(schema, candidate);
      return { status: 'accepted', input, afterValidation: output, versions };
    } catch (error) {
      // Import/compile/runtime errors must never be counted as schema rejection.
      if (!(error instanceof errors.ValidationError) || !Array.isArray(error.debug?.validationErrors)) throw error;
      return { status: 'rejected', input, afterValidation: candidate, versions,
        message: error.message, validationErrors: error.debug.validationErrors };
    }
  };
}
