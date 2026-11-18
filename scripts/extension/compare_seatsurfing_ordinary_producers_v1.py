"""Complete database insert checks for the two ordinary producer controls."""
from collections import Counter
from decimal import Decimal
import json
from compare_seatsurfing_ordinary_state_v1 import bind_rows, selected_row, epoch_microseconds


def compare_creation_step(before, after, *, location_id, session_id, window_start_us, window_end_us):
    if not all(type(x) is int for x in (window_start_us, window_end_us)) or not 0 <= window_end_us - window_start_us <= 180000000:
        raise ValueError('Require bounded prospectively recorded creation window')
    left, right = bind_rows(before), bind_rows(after)
    if set(left) != set(right): raise ValueError('Creation changed relation set')
    metadata = lambda snapshot: {k: v for k, v in snapshot['state'].items() if k != 'tables'}
    if metadata(before) != metadata(after): raise ValueError('Creation changed database metadata or sequences')
    descriptors = lambda snapshot: sorted((t['schema_name'], t['relation_name'], t['relkind']) for t in snapshot['state']['tables'])
    if descriptors(before) != descriptors(after): raise ValueError('Creation changed relation kind')
    locations, sessions = ('public', 'locations'), ('public', 'sessions')
    if not {locations, sessions}.issubset(left): raise ValueError('Missing original relations')
    for table in set(left) - {locations, sessions}:
        if Counter(left[table]) != Counter(right[table]): raise ValueError('Creation changed unrelated table: ' + '.'.join(table))
    inserted, other_locations = selected_row(right[locations], location_id)
    if any(json.loads(row).get('id') == location_id for row in left[locations]):
        raise ValueError('Producer identity already existed')
    if Counter(left[locations]) != other_locations:
        raise ValueError('Producer changed existing locations or inserted extra rows')
    old_session, old_others = selected_row(left[sessions], session_id)
    new_session, new_others = selected_row(right[sessions], session_id)
    if old_others != new_others: raise ValueError('Producer changed another session')
    old_activity, new_activity = old_session.pop('last_activity'), new_session.pop('last_activity')
    if old_session != new_session: raise ValueError('Producer changed session identity or lifetime')
    previous, current = epoch_microseconds(old_activity), epoch_microseconds(new_activity)
    if not previous <= current or not window_start_us <= current <= window_end_us:
        raise ValueError('Producer session activity outside recorded window')
    raw = next(row for row in right[locations] if json.loads(row).get('id') == location_id)
    return {'status': 'single_location_insert_with_bounded_session_activity', 'location_id': location_id,
            'inserted_row': raw, 'session_id': session_id,
            'session_activity': {'before': old_activity, 'after': new_activity,
                                 'window_start_us': window_start_us, 'window_end_us': window_end_us},
            'all_other_rows_and_metadata_unchanged': True, 'runtime_qualified': False}


def compare_producer_rows(native, api, *, organization_id):
    for result in (native, api):
        if result.get('status') != 'single_location_insert_with_bounded_session_activity':
            raise ValueError('Require complete creation-step evidence')
    if native['session_id'] != api['session_id']: raise ValueError('Producer actors differ')
    if native['location_id'] == api['location_id']: raise ValueError('Producer identities must be distinct')
    first, second = [json.loads(result['inserted_row'], parse_float=Decimal) for result in (native, api)]
    for result, row in ((native, first), (api, second)):
        if row.pop('id') != result['location_id']: raise ValueError('Inserted identity does not bind response')
    if first != second: raise ValueError('Complete inserted rows differ beyond assigned identity')
    expected = {'organization_id': organization_id, 'name': 'Study area', 'description': 'Study description',
                'announcement': 'Study notice', 'max_concurrent_bookings': 0, 'tz': '', 'enabled': True,
                'map_scale': Decimal('1'), 'map_type': '', 'bookable_days': '', 'blocked_from': None, 'blocked_until': None}
    for key, value in expected.items():
        if key not in first or first[key] != value: raise ValueError('Ordinary inserted value mismatch: ' + key)
    return {'status': 'ordinary_producer_rows_match', 'native_location_id': native['location_id'],
            'api_location_id': api['location_id'], 'mapped_fields': ['id'],
            'all_other_inserted_fields_equal': True, 'request_transport_qualified': False, 'runtime_qualified': False}
