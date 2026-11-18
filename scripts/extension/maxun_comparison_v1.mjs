// Prospective ordinary-control coverage: every public application table,
// plus empty background-job tables. Worker bookkeeping remains in raw evidence.
import assert from 'node:assert/strict';
import {sameState} from './maxun_serializer_v1.mjs';

export function applicationState(state) {
  assert.equal(state.comparison_field,'exact_rows');
  assert.ok(state.tables.every(t => ['public','graphile_worker'].includes(t.schema)), 'Unmapped persistence schema');
  const tables = state.tables.filter(t => t.schema === 'public');
  assert.ok(tables.some(t => t.table === 'robot'), 'Missing complete robot relation');
  const jobs = state.tables.filter(t => t.schema === 'graphile_worker' && /jobs/.test(t.table));
  assert.ok(jobs.length > 0, 'Cannot establish background-job quiescence');
  for (const table of jobs) assert.equal(table.rows.length,0,'Nonempty background-job relation: '+table.table);
  return tables.map(t => ({schema:t.schema,table:t.table,rows:t.exact_rows}));
}

export function assertSameApplicationState(expected, actual) {
  assert.ok(sameState(applicationState(expected),applicationState(actual)),
    'Application/actor state differs before continuation');
}

export function assertOrdinaryEdit(before, after, targetId, editedName) {
  const a = applicationState(before), b = applicationState(after);
  const source = before.tables.find(t => t.schema === 'public' && t.table === 'robot');
  assert.equal(source.rows.length,1,'Ordinary fixture must contain exactly one robot');
  assert.equal(source.rows[0].recording_meta.id,targetId);
  const expected = structuredClone(a);
  const exactRows = expected.find(t => t.table === 'robot').rows;
  assert.equal(exactRows[0],'array');
  assert.equal(exactRows[1].length,1);
  const object = exactRows[1][0];
  assert.equal(object[0],'object');
  const meta = object[1].find(([key])=>key === 'recording_meta')?.[1];
  assert.equal(meta?.[0],'object');
  const name = meta[1].find(([key])=>key === 'name');
  assert.ok(name,'Missing ordinary name');
  name[1] = ['string',editedName];
  assert.ok(sameState(expected,b),'Persisted ordinary edit differs beyond the requested name');
}
