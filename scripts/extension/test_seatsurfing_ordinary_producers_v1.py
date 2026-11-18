"""Synthetic complete insert comparisons, including unrelated-state failures."""
import copy
import json
import unittest
from test_seatsurfing_ordinary_state_v1 import snapshot
from compare_seatsurfing_ordinary_producers_v1 import compare_creation_step, compare_producer_rows
from compare_seatsurfing_ordinary_state_v1 import epoch_microseconds


class Producers(unittest.TestCase):
    def setUp(self):
        self.before = {'locations': [{'id': 'sample', 'name': 'Sample'}], 'sessions': [{'id': 'session', 'last_activity': '2026-11-18T00:00:00', 'user_id': 'user'}], 'users': [{'id': 'user'}]}
        self.row = {'id': 'native', 'organization_id': 'org', 'name': 'Study area', 'description': 'Study description', 'announcement': 'Study notice', 'max_concurrent_bookings': 0, 'tz': '', 'enabled': True, 'map_scale': 1.0, 'map_type': '', 'bookable_days': '', 'blocked_from': None, 'blocked_until': None, 'map_data': None}
        self.after = copy.deepcopy(self.before); self.after['locations'].append(self.row)
        self.after['sessions'][0]['last_activity'] = '2026-11-18T00:00:02'
        self.kw = dict(location_id='native', session_id='session', window_start_us=epoch_microseconds('2026-11-18T00:00:01Z'), window_end_us=epoch_microseconds('2026-11-18T00:00:03Z'))
    def step(self): return compare_creation_step(snapshot(self.before), snapshot(self.after), **self.kw)
    def pair(self):
        native = self.step(); api = copy.deepcopy(native); api['location_id'] = 'api'
        row = json.loads(api['inserted_row']); row['id'] = 'api'; api['inserted_row'] = json.dumps(row)
        return native, api
    def test_only_one_insert_and_activity_change_allowed(self):
        self.assertEqual(self.step()['status'], 'single_location_insert_with_bounded_session_activity')
    def test_existing_and_extra_location_changes_rejected(self):
        self.after['locations'][0]['name'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'existing locations'): self.step()
        self.after['locations'][0]['name'] = 'Sample'; self.after['locations'].append({'id': 'extra'})
        with self.assertRaisesRegex(ValueError, 'extra rows'): self.step()
    def test_unrelated_table_and_session_changes_rejected(self):
        self.after['users'].append({'id': 'other'})
        with self.assertRaisesRegex(ValueError, 'unrelated'): self.step()
        self.after['users'].pop(); self.after['sessions'][0]['user_id'] = 'other'
        with self.assertRaisesRegex(ValueError, 'identity'): self.step()
    def test_preexisting_producer_id_rejected(self):
        self.before['locations'].append(copy.deepcopy(self.row))
        with self.assertRaisesRegex(ValueError, 'already existed'): self.step()
    def test_activity_outside_window_rejected(self):
        self.after['sessions'][0]['last_activity'] = '2026-11-18T00:00:04'
        with self.assertRaisesRegex(ValueError, 'window'): self.step()
    def test_row_pair_maps_only_id(self):
        native, api = self.pair()
        self.assertEqual(compare_producer_rows(native, api, organization_id='org')['mapped_fields'], ['id'])
        row = json.loads(api['inserted_row']); row['map_data'] = 'unexpected'; api['inserted_row'] = json.dumps(row)
        with self.assertRaisesRegex(ValueError, 'beyond assigned identity'): compare_producer_rows(native, api, organization_id='org')
    def test_equal_but_wrong_ordinary_values_rejected(self):
        self.row['description'] = 'wrong'; native, api = self.pair()
        with self.assertRaisesRegex(ValueError, 'value mismatch'): compare_producer_rows(native, api, organization_id='org')
    def test_metadata_change_rejected(self):
        before, after = snapshot(self.before), snapshot(self.after); after['state']['roles_sha256'] = 'b' * 64
        with self.assertRaisesRegex(ValueError, 'metadata'): compare_creation_step(before, after, **self.kw)


if __name__ == '__main__': unittest.main()
