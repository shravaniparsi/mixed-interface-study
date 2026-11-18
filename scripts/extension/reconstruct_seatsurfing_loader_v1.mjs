/** Reconstruct original editor inputs from retained native GET evidence only. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
const sha = raw => createHash('sha256').update(raw).digest('hex');
export function reconstructSeatsurfingLoader({ events, afterRequestId, id, accessToken,
  origin = 'http://127.0.0.1:8080' }) {
  assert.match(id, /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
  assert.equal(origin, 'http://127.0.0.1:8080');
  assert.ok(Number.isSafeInteger(afterRequestId) && afterRequestId >= 0);
  const settingsPath = '/setting/'; // Original Navigation.PATH_API_SETTINGS.
  const requests = events.filter(e => e.kind === 'request' && e.id > afterRequestId);
  const consumed = [];
  const get = path => {
    const matches = requests.filter(e => e.method === 'GET' && e.url === origin + path);
    assert.equal(matches.length, 1, 'Missing or ambiguous native loader GET: ' + path);
    const request = matches[0];
    const only = kind => { const rows = events.filter(e => e.id === request.id && e.kind === kind); assert.equal(rows.length, 1); return rows[0]; };
    assert.equal(only('request_headers').headers.authorization, 'Bearer ' + accessToken);
    const response = only('response');
    assert.equal(response.status, 200); assert.equal(response.bodyCaptured, true);
    assert.equal(response.bodySha256, sha(response.body)); only('finished');
    assert.equal(events.some(e => e.kind === 'request_failed' && e.id === request.id), false);
    consumed.push({ id: request.id, path, bodySha256: response.bodySha256 });
    return JSON.parse(response.body);
  };
  const self = get('/user/me');
  assert.ok(self.permissions && typeof self.permissions === 'object');
  const settings = get(settingsPath); assert.ok(Array.isArray(settings));
  // Mirrors RuntimeConfig.resetInfos plus its ordered settings assignments.
  let featureGroups = false;
  for (const setting of settings) if (setting.name === 'feature_groups') featureGroups = setting.value === '1';
  const readback = get('/location/' + id); assert.equal(readback.id, id);
  assert.notEqual(readback.mapType, 'designed', 'Designed map branch remains outside this component');
  const canReadGroups = (self.permissions.groups ?? 0) >= 10;
  let groups = [];
  if (canReadGroups) groups = get('/group/');
  else assert.equal(requests.some(e => e.url === origin + '/group/'), false, 'Group request contradicts original permission branch');
  assert.ok(Array.isArray(groups));
  const rawSpaces = get('/location/' + id + '/space/'); assert.ok(Array.isArray(rawSpaces));
  const map = get('/location/' + id + '/map');
  assert.ok(map && typeof map === 'object' && !Array.isArray(map));
  const attributes = get('/space-attribute/'); assert.ok(Array.isArray(attributes));
  const rawValues = get('/location/' + id + '/attribute'); assert.ok(Array.isArray(rawValues));
  const timezones = get('/setting/timezones'); assert.ok(Array.isArray(timezones));
  const attributeValues = rawValues.map(value => ({ attributeId: value.attributeId, value: value.value }));
  // Space writes are absent for an unrelated scalar edit. Preserve all raw
  // records, while matching the original default [] for missing attributes.
  const spaces = rawSpaces.map(space => ({ ...space, attributes: space.attributes ? space.attributes.map(value => ({ attributeId:value.attributeId, value:value.value })) : [] }));
  return { materialization: { readback, groups, attributeValues, spaces, featureGroups, browserTimezone: 'UTC' },
    originalResponses: { self, settings, rawSpaces, map, attributes, rawValues, timezones }, consumed,
    sourceScope: 'fresh_editor_scalar_edit_without_map_design_or_file_changes',
    networkTraceSha256: sha(JSON.stringify(events)), afterRequestId,
    acquisitionProvenanceVerified: false, runtimeQualified: false };
}
