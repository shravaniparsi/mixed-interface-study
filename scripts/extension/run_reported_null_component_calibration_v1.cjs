/* Isolated in-memory source calibration: never imports the frontend application. */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const vm = require('vm');
const assert = require('assert');
const [sourceDir, dependencyDir, output] = process.argv.slice(2);
assert(sourceDir && dependencyDir && output, 'sourceDir dependencyDir output required');
assert(!fs.existsSync(output), 'Refusing to overwrite a measurement');
const repo = path.resolve(__dirname, '../..');
const manifest = JSON.parse(fs.readFileSync(path.join(repo, 'manifests/reported-interface-fault-admission-v1.json')));
const hash = x => crypto.createHash('sha256').update(x).digest('hex');
const mongoose = require(path.join(path.resolve(dependencyDir), 'node_modules/mongoose'));
assert.equal(mongoose.version, '4.7.1');
assert.equal(process.version, 'v16.13.2');
const provenance = [];
function source(id) {
  const file = `${id}.json`;
  const entry = manifest.evidence.find(x => x.file === file);
  const raw = fs.readFileSync(path.join(sourceDir, file));
  assert.equal(hash(raw), entry.sha256);
  const data = JSON.parse(raw);
  const code = Buffer.from(data.content, 'base64').toString('utf8');
  provenance.push({file, endpoint: entry.endpoint, response_sha256: hash(raw), source_sha256: hash(code)});
  return code;
}
function constructor(id) {
  const code = source(id);
  const match = code.match(/constructor\(props\)\{\s*super\(props\);([\s\S]*?)\n  \}\s*\n  render\(\)/);
  assert(match && code.split('constructor(props)').length === 2, 'Unexpected constructor shape');
  return new vm.Script(`(function(){${match[1]} }).call(target)`);
}
function schema(id) {
  mongoose.deleteModel && mongoose.deleteModel('Post');
  delete mongoose.models.Post;
  delete mongoose.modelSchemas.Post;
  const code = source(id);
  const module = {exports: {}};
  vm.runInNewContext(code, {module, global: {Promise}, require: name => { assert.equal(name, 'mongoose'); return mongoose; }}, {timeout: 1000});
  return module.exports;
}
const fronts = {before: constructor(17), after: constructor(25)};
const schemas = {before: schema(21), after: schema(24)};
const inputs = [
  {id: 'omitted', provenance: 'external reported condition and repository test', fields: {}},
  {id: 'null', provenance: 'external reported condition', fields: {setup: null}},
  {id: 'empty_array', provenance: 'analyst representation control', fields: {setup: []}},
  {id: 'one_array', provenance: 'analyst representation control', fields: {setup: ['ScreenHero']}},
  {id: 'empty_string', provenance: 'analyst representation control', fields: {setup: ''}},
  {id: 'one_string', provenance: 'analyst representation control', fields: {setup: 'ScreenHero'}}
];
const records = [];
for (const [schemaVersion, Model] of Object.entries(schemas)) {
  for (const input of inputs) {
    const document = new Model({username: 'Gauja', postTime: 0, endTime: 3600000, ...input.fields});
    const error = document.validateSync();
    const serialized = JSON.parse(JSON.stringify(document));
    delete serialized._id; // Generated identity is unrelated to these predicates; no persistence claim.
    const hasSetup = Object.prototype.hasOwnProperty.call(serialized, 'setup');
    const record = {schema_version: schemaVersion, input: input.id, input_provenance: input.provenance,
      validation_error: error ? {name: error.name, message: error.message} : null,
      serialized, predicates: {nonnull: hasSetup && serialized.setup !== null, array: Array.isArray(serialized.setup)}, constructors: {}};
    for (const [frontendVersion, script] of Object.entries(fronts)) {
      const target = {props: {camper: serialized}};
      try {
        script.runInNewContext({target}, {timeout: 1000});
        record.constructors[frontendVersion] = {threw: false, state: JSON.parse(JSON.stringify(target.state))};
      } catch (e) { record.constructors[frontendVersion] = {threw: true, error_name: e.name, error_message: e.message}; }
    }
    records.push(record);
  }
}
const result = {scope: 'in-memory schema and extracted constructor only; no HTTP, DB, React mount or browser',
  measured_at: new Date().toISOString(), node: process.version, mongoose: mongoose.version,
  dependency_lock_sha256: hash(fs.readFileSync(path.join(dependencyDir, 'package-lock.json'))),
  source_provenance: provenance, records};
fs.writeFileSync(output, JSON.stringify(result, null, 2) + '\n', {flag: 'wx'});
console.log(JSON.stringify({schema_rows: records.length, constructor_calls: records.length * 2, output}));
