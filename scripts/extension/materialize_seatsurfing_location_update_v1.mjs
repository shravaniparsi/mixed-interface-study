/** Source-derived scalar-edit component, unqualified until native equality.
 * Inputs are complete fresh readbacks, not the producer payload or DOM text.
 * Emits a request plan only. No API request or native action is performed.
 */
import assert from 'node:assert/strict';
const uuid = value => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
const request = (method, path, payload) => {
  const body = JSON.stringify(payload);
  return { method, path, body, json: JSON.parse(body) };
};
const dateString = value => {
  const [year, month, day] = value.split('-').map(p => parseInt(p));
  const date = new Date(year, month - 1, day);
  assert.ok(Number.isFinite(date.getTime()), 'Unsupported invalid native date');
  return date.getFullYear().toString().padStart(4, '0') + '-' +
    (date.getMonth() + 1).toString().padStart(2, '0') + '-' + date.getDate().toString().padStart(2, '0');
};

export function materializeSeatsurfingLocationUpdate({ readback, groups, attributeValues, spaces, featureGroups, edit, browserTimezone }) {
  assert.ok(uuid(readback.id));
  assert.equal(Intl.DateTimeFormat().resolvedOptions().timeZone, browserTimezone, 'Native and materializer timezone must match');
  assert.ok(Array.isArray(groups) && Array.isArray(attributeValues) && Array.isArray(spaces));
  assert.equal(typeof featureGroups, 'boolean');
  assert.ok(['/announcement', '/description', '/name'].includes(edit.path));
  assert.equal(typeof edit.value, 'string');
  // Only a scalar field is edited: loaded spaces remain changed=false, with
  // pendingImage=null and removeImage=false. No attribute deletion is made.
  assert.ok(spaces.every(s => uuid(s.id) && Array.isArray(s.attributes)));
  assert.ok(groups.every(g => uuid(g.id)));
  const mapType = readback.mapType || '';
  assert.notEqual(mapType, 'designed', 'Designed-map save/reload branch not qualified by this component');
  const days = readback.bookableDays || [];
  const blockedFrom = readback.blockedFrom || '';
  const blockedUntil = readback.blockedUntil || '';
  const allowed = readback.allowedBookerGroupIds || [];
  assert.ok(Array.isArray(days) && Array.isArray(allowed));
  assert.equal(typeof blockedFrom, 'string');
  assert.equal(typeof blockedUntil, 'string');
  const stateDays = days.length > 0 ? days : [0, 1, 2, 3, 4, 5, 6];
  // Mirrors Location.deserialize -> loadData -> onSubmit -> serialize.
  // Name/description retain null or undefined; announcement uses original ||.
  const payload = {
    name: readback.name,
    description: readback.description,
    maxConcurrentBookings: readback.maxConcurrentBookings > 0 ? readback.maxConcurrentBookings : 0,
    timezone: readback.timezone,
    enabled: readback.enabled,
    mapScale: readback.mapScale,
    mapType: '',
    allowedBookerGroupIds: featureGroups ? groups.filter(g => allowed.includes(g.id)).map(g => g.id) : [],
    bookableDays: stateDays.length === 7 ? [] : stateDays,
    blockedFrom: blockedFrom !== '' ? dateString(blockedFrom || blockedUntil) : '',
    blockedUntil: blockedUntil !== '' ? dateString(blockedUntil || blockedFrom) : '',
    announcement: readback.announcement || '',
  };
  payload[edit.path.slice(1)] = edit.value;
  const main = request('PUT', '/location/' + readback.id, payload);
  const attributes = attributeValues.map(av => {
    assert.ok(uuid(av.attributeId));
    return request('POST', '/location/' + readback.id + '/attribute/' + av.attributeId, { value: av.value });
  });
  return {
    main,
    afterMainSuccess: attributes,
    attributeDispatch: 'start_in_readback_order_without_awaiting_completion_between_dispatches',
    nativeSavedStateWaitsForAttributeCompletion: false,
    spaceOrImageWrites: [],
    mapWrite: null,
    nativeAutomaticReadback: false,
    scope: 'fresh_editor_scalar_edit_without_map_design_or_file_changes',
    qualification: 'source_component_only_no_native_runtime_equality',
  };
}
