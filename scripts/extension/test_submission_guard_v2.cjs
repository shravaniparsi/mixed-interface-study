'use strict';
const assert = require('node:assert/strict');
const {extractGuard, evaluateGuard} = require('./extract_submission_guard_v2.cjs');
const ts = require(process.env.STUDY_TYPESCRIPT_PATH || 'typescript');
const selection = {method:'submit',form:'details',service:'writer',sink:'create'};
const fixture = `class Example {
  mismatch = false;
  submit() {
    this.mismatch = false;
    const {secret: a, repeat: b} = this.details.getRawValue();
    if (a !== b) { this.mismatch = true; }
    else { this.writer.create({secret:a}).subscribe({}); }
  }
}`;
const r = extractGuard(ts,fixture,selection);
assert.equal(r.status,'extracted');
assert.deepEqual(r.predicate,{left:'secret',operator:'!==',right:'repeat',sink_when:false});
assert.equal(evaluateGuard(r,{secret:'same',repeat:'same'}),'sink_branch');
assert.equal(evaluateGuard(r,{secret:'same',repeat:'other'}),'non_sink_branch');
assert.equal(evaluateGuard(r,{secret:'same'}),'unknown');
assert.equal(evaluateGuard(r,{secret:null,repeat:null}),'unknown');
const equal = extractGuard(ts, fixture.replace('a !== b','a === b'),selection);
assert.equal(evaluateGuard(equal,{secret:'same',repeat:'same'}),'non_sink_branch');
const mutations = [
  ['loose equality',fixture.replace('a !== b','a != b')],
  ['additional guard',fixture.replace('a !== b','a !== b || this.error')],
  ['side effect before branch',fixture.replace('this.mismatch = false;','this.refresh();')],
  ['default binding',fixture.replace('secret: a','secret: a = "default"')],
  ['async method',fixture.replace('submit()','async submit()')],
  ['inherited state',fixture.replace('class Example {','class Example extends Base {')],
  ['post-branch side effect',fixture.replace('\n  }','\n    this.refresh();\n  }')],
  ['transformed payload',fixture.replace('secret:a','secret:normalize(a)')],
  ['extra sink',fixture.replace('this.mismatch = true;','this.writer.create({secret:a}).subscribe({});')],
  ['unknown flag',fixture.replace('mismatch = false;','other = false;')],
];
for (const [name,source] of mutations) assert.equal(extractGuard(ts,source,selection).status,'unsupported',name);
console.log('Submission guard checks passed: alias mapping, polarity, missing/type states and 10 unsupported mutations. Authored unit fixtures, not study cases.');

assert.equal(extractGuard(ts,fixture.replace('class Example {','class Example implements AfterViewInit {'),selection).status,'extracted');
