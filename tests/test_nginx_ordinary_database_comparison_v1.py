"""Synthetic typed-state comparison tests; no database/application execution."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/extension/nginx_ordinary_database_comparison_v1.py'
spec = importlib.util.spec_from_file_location('nginx_database_comparison', path)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def table(name, rows):
    columns = list(rows[0])
    cell = lambda v: ['integer', str(v)] if type(v) is int else ['text', v]
    return {'name': name, 'columns': [[['integer', str(i)], ['text', c]] for i,c in enumerate(columns)],
            'rows': sorted(json.dumps([cell(row[c]) for c in columns]) for row in rows)}


def change(state, name, column, value, index=0):
    t = next(t for t in state['tables'] if t['name'] == name)
    names = [c[1][1] for c in t['columns']]
    cells = json.loads(t['rows'][index])
    cells[names.index(column)] = ['integer', str(value)] if type(value) is int else ['text', value]
    t['rows'][index] = json.dumps(cells)


class OrdinaryDatabaseComparisonTests(unittest.TestCase):
    def fixture(self, path='/clients/0/address', stamp='2026-11-18 12:00:00'):
        old = '2026-11-18 11:00:00'
        root = dict(id=3, created_on=old, modified_on=old, name='Study Control', satisfy_any=0, pass_auth=0, owner_user_id=1, is_deleted=0, meta='{}')
        auth = dict(id=7, created_on=old, modified_on=old, access_list_id=3, username='studycontrol', password='Study-Only-Control-2026', meta='{}')
        client = dict(id=9, created_on=old, modified_on=old, access_list_id=3, address='192.0.2.10', directive='allow', meta='{}')
        audit = dict(id=20, created_on=old, modified_on=old, user_id=1, object_id=3, object_type='access-list', action='created', meta='{"kept":true}')
        sequences = {'access_list': 3, 'access_list_auth': 7, 'access_list_client': 9, 'audit_log': 20}
        rows = {'access_list': [root], 'access_list_auth': [auth], 'access_list_client': [client], 'audit_log': [audit], 'user': [dict(id=1, roles='admin')]}
        def state():
            return {'schema': ['synthetic-schema-same-in-both-branches'], 'tables':
                    [table(name, value) for name,value in rows.items()] +
                    [table('sqlite_sequence', [dict(name=k, seq=v) for k,v in sequences.items()])]}
        before = state()
        root['modified_on'] = stamp
        client.update(id=10, created_on=stamp, modified_on=stamp)
        sequences['access_list_client'] += 1; sequences['audit_log'] += 1
        if path == '/clients/0/address': client['address'] = m.EDITS[path]
        else:
            auth.update(id=8, created_on=stamp, modified_on=stamp, password=m.EDITS[path])
            sequences['access_list_auth'] += 1
        rows['audit_log'].append(dict(audit, id=21, created_on=stamp, modified_on=stamp, action='updated', meta='{"complete":"same"}'))
        after = state()
        epoch = datetime.strptime(stamp, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
        window = dict(timezone='UTC', start_epoch_seconds=epoch + .1, end_epoch_seconds=epoch + .9)
        return before, after, dict(path=path, value=m.EDITS[path]), window

    def test_both_frozen_edits_allow_only_observed_write_timestamps(self):
        for path in m.EDITS:
            with self.subTest(path=path):
                before, left, edit, lw = self.fixture(path)
                _, right, _, rw = self.fixture(path, '2026-11-18 12:01:00')
                result = m.compare_ordinary_databases(before, left, right, 3, 1, edit, lw, rw)
                self.assertEqual(len(result['left_timestamps']), 5 if path == '/clients/0/address' else 7)
                self.assertNotEqual(result['left_timestamps'], result['right_timestamps'])

    def test_historical_audit_timestamp_cannot_be_ignored(self):
        before, after, edit, window = self.fixture()
        change(after, 'audit_log', 'created_on', '2026-11-18 12:00:00')
        with self.assertRaisesRegex(ValueError, 'Historical audit'):
            m.normalize_ordinary_database(before, after, 3, 1, edit, window)

    def test_unrelated_changes_fail_even_if_both_branches_share_them(self):
        before, after, edit, window = self.fixture()
        change(after, 'user', 'roles', 'other')
        with self.assertRaisesRegex(ValueError, 'Unrelated table'):
            m.compare_ordinary_databases(before, after, deepcopy(after), 3, 1, edit, window, window)

    def test_root_creation_time_is_not_an_operation_timestamp(self):
        before, after, edit, window = self.fixture()
        change(after, 'access_list', 'created_on', '2026-11-18 12:00:00')
        with self.assertRaisesRegex(ValueError, 'root fields'):
            m.normalize_ordinary_database(before, after, 3, 1, edit, window)

    def test_out_of_window_time_rejected(self):
        before, after, edit, window = self.fixture()
        change(after, 'access_list_client', 'modified_on', '2026-11-18 12:00:02')
        with self.assertRaisesRegex(ValueError, 'outside observed'):
            m.normalize_ordinary_database(before, after, 3, 1, edit, window)

    def test_audit_actor_and_sequence_changes_rejected(self):
        for name, column, value, expected in [('audit_log', 'user_id', 2, 'actor/object'), ('sqlite_sequence', 'seq', 99, 'sequence mutation')]:
            before, after, edit, window = self.fixture()
            change(after, name, column, value, index=1 if name == 'audit_log' else 0)
            with self.assertRaisesRegex(ValueError, expected):
                m.normalize_ordinary_database(before, after, 3, 1, edit, window)

    def test_audit_payload_difference_survives_timestamp_comparison(self):
        before, left, edit, window = self.fixture(); right = deepcopy(left)
        change(right, 'audit_log', 'meta', '{"different":true}', index=1)
        with self.assertRaisesRegex(ValueError, 'outcomes differ'):
            m.compare_ordinary_databases(before, left, right, 3, 1, edit, window, window)

    def test_unedited_password_cannot_change(self):
        before, after, edit, window = self.fixture()
        change(after, 'access_list_auth', 'password', 'wrong')
        with self.assertRaisesRegex(ValueError, 'Unedited auth'):
            m.normalize_ordinary_database(before, after, 3, 1, edit, window)


if __name__ == '__main__':
    unittest.main()
