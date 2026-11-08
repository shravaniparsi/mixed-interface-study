import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {orderedCases} from '../scripts/run_quartz_pair_job.mjs';
import {REGISTRY_SHA256} from '../scripts/quartz_generated_case.mjs';
const registry=JSON.parse(await readFile(new URL('../manifests/quartz-job-generated-pool-v2.json',import.meta.url)));
const controls=registry.cases.filter(c=>c.intervention==='route_only'&&c.operations[0].interface==='api');
const order=cases=>({schema_version:1,scope:'quartz_repeat_pair',registry_sha256:REGISTRY_SHA256,case_ids:cases.map(c=>c.case_id)});
test('explicit control pair preserves supplied continuation order',()=>assert.deepEqual(orderedCases(registry,'controls',order(controls)),controls));
test('missing order cannot dispatch full registry',()=>assert.throws(()=>orderedCases(registry,'controls')));
test('duplicate branch cannot stand for a pair',()=>assert.throws(()=>orderedCases(registry,'controls',order([controls[0],controls[0]]))));
test('all mode cannot bypass pair selection',()=>assert.throws(()=>orderedCases(registry,'all',order(controls))));
test('different producer routes cannot be paired',()=>assert.throws(()=>orderedCases(registry,'controls',order([controls[0],registry.cases.find(c=>c.intervention==='route_only'&&c.operations[0].interface==='ui')]))));
test('mutations cannot enter control dispatch',()=>{
 const first=registry.cases.find(c=>c.intervention==='payload_mutation');
 const members=registry.cases.filter(c=>c.intervention==='payload_mutation'&&JSON.stringify(c.mutation)===JSON.stringify(first.mutation));
 assert.equal(members.length,2);assert.throws(()=>orderedCases(registry,'controls',order(members)));
 assert.equal(orderedCases(registry,'boundary-pair',order(members)).length,2);
});
