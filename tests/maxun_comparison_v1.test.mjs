import test from 'node:test';
import assert from 'node:assert/strict';
import {applicationState, assertSameApplicationState, assertOrdinaryEdit} from '../scripts/extension/maxun_comparison_v1.mjs';
const tag=v=>v===null?['null']:Array.isArray(v)?['array',v.map(tag)]:typeof v==='object'?['object',Object.keys(v).sort().map(k=>[k,tag(v[k])])]:[typeof v==='number'?'number':typeof v,typeof v==='number'?String(v):v];
function state(name='ordinary',actor='same') {
 const rows=[{id:'row-1',recording_meta:{id:'meta-1',name,createdAt:'fixed'},recording:{workflow:[1,2]}}];
 return {comparison_field:'exact_rows',tables:[
  {schema:'graphile_worker',table:'_private_jobs',rows:[],exact_rows:tag([])},
  {schema:'public',table:'robot',rows,exact_rows:tag(rows)},
  {schema:'public',table:'users',rows:[{id:1,actor}],exact_rows:tag([{id:1,actor}])}]};
}
test('equal application/actor state is accepted',()=>assertSameApplicationState(state(),state()));
test('only intended name edit is accepted',()=>{
 assertOrdinaryEdit(state(),state('edited'),'meta-1','edited');
 assert.throws(()=>assertOrdinaryEdit(state(),state('edited','changed'),'meta-1','edited'),/differs beyond/);
 assert.throws(()=>assertOrdinaryEdit(state(),state('other'),'meta-1','edited'),/differs beyond/);
});
test('nonempty jobs and unknown schemas are unavailable',()=>{
 const a=state();a.tables[0].rows.push({id:1});assert.throws(()=>applicationState(a),/Nonempty/);
 const b=state();b.tables.push({schema:'other',table:'hidden',rows:[]});assert.throws(()=>applicationState(b),/Unmapped/);
});
test('actor drift fails before edit',()=>assert.throws(()=>assertSameApplicationState(state(),state('ordinary','different')),/differs before/));
