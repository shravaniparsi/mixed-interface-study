import test from 'node:test';
import assert from 'node:assert/strict';
import { materializeSeatsurfingLocationUpdate as materialize } from '../scripts/extension/materialize_seatsurfing_location_update_v1.mjs';
const id = '11111111-1111-4111-8111-111111111111';
const group = '22222222-2222-4222-8222-222222222222';
const attr = '33333333-3333-4333-8333-333333333333';
function input() {
  return { readback: { id, name: 'ordinary', description: 'before', announcement: 'notice', maxConcurrentBookings: 0, timezone: 'UTC', enabled: true, mapScale: 1, mapType: '', allowedBookerGroupIds: [], bookableDays: [], blockedFrom: '', blockedUntil: '' }, groups: [], spaces: [], attributeValues: [], featureGroups: true, edit: { path: '/description', value: 'after' }, browserTimezone: Intl.DateTimeFormat().resolvedOptions().timeZone };
}
test('ordinary unrelated edit retains complete twelve-key update', () => {
  const x = input(); const result = materialize(x);
  assert.deepEqual(result.main.json, { name: 'ordinary', description: 'after', maxConcurrentBookings: 0, timezone: 'UTC', enabled: true, mapScale: 1, mapType: '', allowedBookerGroupIds: [], bookableDays: [], blockedFrom: '', blockedUntil: '', announcement: 'notice' });
  assert.equal(result.main.path, '/location/' + id);
  assert.equal(x.readback.description, 'before');
});
test('counterfactual serialization preserves null and missing target name', () => {
  const x = input(); x.readback.name = null;
  assert.equal(materialize(x).main.json.name, null);
  delete x.readback.name;
  assert.equal(Object.hasOwn(materialize(x).main.json, 'name'), false);
});
test('original announcement fallback is retained independently of nullable description', () => {
  const x = input(); x.readback.announcement = null; x.readback.description = null; x.edit = { path: '/name', value: 'edit' };
  const body = materialize(x).main.json;
  assert.equal(body.announcement, ''); assert.equal(body.description, null);
});
test('existing attributes remain writes even on unrelated scalar edit', () => {
  const x = input(); x.attributeValues = [{ attributeId: attr, value: 'retained' }]; x.groups = [{ id: group }]; x.readback.allowedBookerGroupIds = [group];
  const plan = materialize(x);
  assert.deepEqual(plan.main.json.allowedBookerGroupIds, [group]);
  assert.equal(plan.afterMainSuccess.length, 1);
  assert.equal(plan.afterMainSuccess[0].path, '/location/' + id + '/attribute/' + attr);
  assert.deepEqual(plan.afterMainSuccess[0].json, { value: 'retained' });
  assert.equal(plan.nativeSavedStateWaitsForAttributeCompletion, false);
});
test('date/day roundtrip and disabled feature preserve original transformations', () => {
  const x = input(); x.readback.blockedFrom = '2028-02-29'; x.readback.blockedUntil = '2028-03-01'; x.readback.bookableDays = [0,1,2,3,4,5,6]; x.featureGroups = false; x.groups = [{id:group}]; x.readback.allowedBookerGroupIds = [group];
  const body = materialize(x).main.json;
  assert.equal(body.blockedFrom, '2028-02-29'); assert.equal(body.blockedUntil, '2028-03-01'); assert.deepEqual(body.bookableDays, []); assert.deepEqual(body.allowedBookerGroupIds, []);
});
test('unmapped design and timezone mismatch are unavailable, not silently simplified', () => {
  const x = input(); x.readback.mapType = 'designed'; assert.throws(() => materialize(x), /Designed-map/);
  x.readback.mapType = ''; x.browserTimezone = 'mismatching-zone'; assert.throws(() => materialize(x), /timezone/);
});
