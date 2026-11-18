import assert from 'node:assert/strict';
import {framePreserved,postComparable,equal} from './frame.mjs';
const before={schema:[],files:{},tables:{guardrail_definitions:{columns:['name','config','updated_at','description'],rows:[['target','{"a":"old","b":"keep"}',10,'keep']]},config_revisions:{columns:['entity','revision','updated_at'],rows:[['guardrails',2,5],['users',1,3]]},unrelated:{columns:['id','value'],rows:[[1,null]]}}};
const after=structuredClone(before);after.tables.guardrail_definitions.rows[0][1]='{"a":"new","b":"keep"}';after.tables.guardrail_definitions.rows[0][2]=12;after.tables.config_revisions.rows[0]=['guardrails',3,7];
assert(framePreserved(before,after,'target','a','new'));
for(const mutate of [x=>x.tables.unrelated.rows[0][1]=false,x=>x.tables.config_revisions.rows[0][1]=4,x=>x.tables.guardrail_definitions.rows[0][3]='changed',x=>x.files.extra={bytes:1,sha256:'x'},x=>x.tables.guardrail_definitions.rows[0][1]='{"a":"new","b":false}']){const bad=structuredClone(after);mutate(bad);assert(!framePreserved(before,bad,'target','a','new'));}
const other=structuredClone(after);other.tables.guardrail_definitions.rows[0][2]=14;other.tables.config_revisions.rows[0][2]=8;assert(equal(postComparable(after,'target'),postComparable(other,'target')));other.tables.config_revisions.rows[1][2]=9;assert(!equal(postComparable(after,'target'),postComparable(other,'target')));
console.log('Frame checks reject unrelated writes, extra revision changes, value-type changes and broad timestamp exclusions.');
