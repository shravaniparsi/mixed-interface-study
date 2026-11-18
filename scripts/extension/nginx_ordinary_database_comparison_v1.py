"""Prospective ordinary-update comparison; private typed SQLite snapshots only.

No timestamps are dropped globally. Each permitted timestamp is checked against
the observed UTC operation interval and retained in the returned private report.
This does not qualify other filesystem, process, actor or browser state.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
import math

EDITS = {'/clients/0/address': '192.0.2.11', '/items/0/password': 'Study-Only-Edited-2026'}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def tables(state):
    result = {t['name']: t for t in state['tables']}
    if len(result) != len(state['tables']):
        raise ValueError('Duplicate database table')
    return result


def records(table):
    names = [column[1][1] for column in table['columns'] if column[1][0] == 'text']
    if len(names) != len(table['columns']) or len(names) != len(set(names)):
        raise ValueError('Malformed column identities')
    result = []
    for raw in table['rows']:
        values = json.loads(raw)
        if len(values) != len(names):
            raise ValueError('Malformed typed row')
        result.append(dict(zip(names, values)))
    return names, result


def integer(cell):
    if not isinstance(cell, list) or len(cell) != 2 or cell[0] != 'integer':
        raise ValueError('Expected stored SQLite integer')
    result = int(cell[1])
    if str(result) != cell[1]:
        raise ValueError('Noncanonical stored integer')
    return result


def equal_rows(left, right, message):
    if Counter(map(encoded, left)) != Counter(map(encoded, right)):
        raise ValueError(message)


def normalize_ordinary_database(before, after, target_id, actor_id, edit, window):
    if type(target_id) is not int or target_id <= 0 or type(actor_id) is not int or actor_id <= 0:
        raise ValueError('Positive stable record and actor IDs required')
    if edit.get('path') not in EDITS or edit.get('value') != EDITS[edit['path']]:
        raise ValueError('Only the frozen ordinary edits are supported')
    if window.get('timezone') != 'UTC':
        raise ValueError('Original localtime must be observed as UTC')
    start, end = window['start_epoch_seconds'], window['end_epoch_seconds']
    if not all(type(v) in (float, int) and math.isfinite(v) for v in (start, end)) or not 0 <= end - start <= 120:
        raise ValueError('Invalid or excessive observed operation interval')
    old, new = tables(before), tables(after)
    if before['schema'] != after['schema'] or old.keys() != new.keys():
        raise ValueError('Database schema/table set changed')
    for name in old:
        if old[name]['columns'] != new[name]['columns']:
            raise ValueError('Database columns changed')
    needed = {'access_list', 'access_list_auth', 'access_list_client', 'audit_log', 'sqlite_sequence'}
    if not needed <= old.keys():
        raise ValueError('Required original tables/sequences unavailable')
    for name in old.keys() - needed:
        equal_rows(records(old[name])[1], records(new[name])[1], 'Unrelated table changed: ' + name)
    output = deepcopy(after)
    normalized_tables = tables(output)
    timestamp_evidence = []

    def time_field(name, row, column):
        cell = row[column]
        if not isinstance(cell, list) or len(cell) != 2 or cell[0] != 'text':
            raise ValueError('Operation timestamp is not stored text')
        parsed = datetime.strptime(cell[1], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        if parsed.strftime('%Y-%m-%d %H:%M:%S') != cell[1] or not math.floor(start) <= parsed.timestamp() <= math.floor(end):
            raise ValueError('Timestamp outside observed operation interval')
        timestamp_evidence.append({'table': name, 'row_id': integer(row['id']), 'column': column, 'value': cell[1]})
        row[column] = ['operation_timestamp', name, column]

    def subject_rows(name, key):
        columns, prior = records(old[name]); _, current = records(new[name])
        for rows in (prior, current):
            ids = [integer(r['id']) for r in rows]
            if len(ids) != len(set(ids)):
                raise ValueError('Duplicate entity IDs')
        predicate = lambda r: r[key] == ['integer', str(target_id)]
        equal_rows([r for r in prior if not predicate(r)], [r for r in current if not predicate(r)],
                   'Unrelated entity row changed: ' + name)
        prior_target = [r for r in prior if predicate(r)]; current_target = [r for r in current if predicate(r)]
        if len(prior_target) != 1 or len(current_target) != 1:
            raise ValueError('Ordinary subject row count differs: ' + name)
        return columns, current, prior_target[0], current_target[0]

    def save(name, columns, rows):
        normalized_tables[name]['rows'] = sorted(json.dumps([r[c] for c in columns], separators=(',', ':'), ensure_ascii=False) for r in rows)

    def sequences(table):
        _, rows = records(table)
        result = {}
        for row in rows:
            if row['name'][0] != 'text' or row['name'][1] in result:
                raise ValueError('Malformed sequence identity')
            result[row['name'][1]] = integer(row['seq'])
        return result

    old_seq, new_seq = sequences(old['sqlite_sequence']), sequences(new['sqlite_sequence'])
    increments = {'access_list_client', 'audit_log'}
    if edit['path'] == '/items/0/password':
        increments.add('access_list_auth')
    expected_seq = dict(old_seq)
    for name in increments:
        if name not in expected_seq:
            raise ValueError('Original autoincrement sequence unavailable')
        expected_seq[name] += 1
    if expected_seq != new_seq:
        raise ValueError('Unexpected sequence mutation')

    columns, current, prior, subject = subject_rows('access_list', 'id')
    if {k:v for k,v in prior.items() if k != 'modified_on'} != {k:v for k,v in subject.items() if k != 'modified_on'}:
        raise ValueError('Ordinary root fields changed')
    time_field('access_list', subject, 'modified_on'); save('access_list', columns, current)

    for name, field, edit_path in [('access_list_auth', 'password', '/items/0/password'), ('access_list_client', 'address', '/clients/0/address')]:
        columns, current, prior, subject = subject_rows(name, 'access_list_id')
        if name == 'access_list_auth' and edit['path'] != edit_path:
            if prior != subject:
                raise ValueError('Unedited auth row changed')
        else:
            expected = deepcopy(prior)
            expected['id'] = ['integer', str(expected_seq[name])]
            if edit['path'] == edit_path:
                expected[field] = ['text', edit['value']]
            for key in ('created_on', 'modified_on'):
                expected[key] = subject[key]
            if expected != subject:
                raise ValueError('Unexpected ordinary child-row values: ' + name)
            time_field(name, subject, 'created_on'); time_field(name, subject, 'modified_on')
        save(name, columns, current)

    columns, prior_audit = records(old['audit_log']); _, current_audit = records(new['audit_log'])
    ids = [integer(r['id']) for r in prior_audit]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate historical audit ID')
    historical = [r for r in current_audit if integer(r['id']) in ids]
    equal_rows(prior_audit, historical, 'Historical audit rows changed')
    added = [r for r in current_audit if integer(r['id']) not in ids]
    if len(added) != 1:
        raise ValueError('Expected exactly one new audit row')
    event = added[0]
    required = {'id': ['integer', str(expected_seq['audit_log'])], 'user_id': ['integer', str(actor_id)],
                'object_id': ['integer', str(target_id)], 'object_type': ['text', 'access-list'], 'action': ['text', 'updated']}
    if any(event.get(k) != v for k,v in required.items()):
        raise ValueError('Audit event actor/object/action differs')
    time_field('audit_log', event, 'created_on'); time_field('audit_log', event, 'modified_on')
    save('audit_log', columns, current_audit)
    return {'normalized_state': output, 'timestamp_evidence': timestamp_evidence}


def compare_ordinary_databases(before, left, right, target_id, actor_id, edit, left_window, right_window):
    a = normalize_ordinary_database(before, left, target_id, actor_id, edit, left_window)
    b = normalize_ordinary_database(before, right, target_id, actor_id, edit, right_window)
    if a['normalized_state'] != b['normalized_state']:
        raise ValueError('Complete ordinary database outcomes differ beyond checked operation times')
    return {'status': 'ordinary_database_equivalence_only_other_state_unqualified',
            'left_timestamps': a['timestamp_evidence'], 'right_timestamps': b['timestamp_evidence']}
