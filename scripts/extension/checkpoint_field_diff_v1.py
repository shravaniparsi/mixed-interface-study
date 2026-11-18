"""Compare JSON representations while retaining hashes and type/precision metadata only."""
import calendar
import datetime
import hashlib
import json
import re


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def describe(value):
    return {'type': type(value).__name__, 'sha256': fingerprint(value)}


def instant(value):
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?Z', value)
    if not match:
        return None
    try:
        base = datetime.datetime.strptime(match[1], '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        return None
    fraction = match[2] or ''
    return calendar.timegm(base.timetuple()) * 10**9 + int(fraction.ljust(9, '0') or '0'), len(fraction)


def differences(before, after, pointer=''):
    if canonical(before) == canonical(after):
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        rows = []
        for key in sorted(set(before) | set(after)):
            path = pointer + '/' + key.replace('~', '~0').replace('/', '~1')
            if key not in before:
                rows.append({'path': path, 'change': 'added', 'after': describe(after[key])})
            elif key not in after:
                rows.append({'path': path, 'change': 'removed', 'before': describe(before[key])})
            else:
                rows.extend(differences(before[key], after[key], path))
        return rows
    if isinstance(before, list) and isinstance(after, list):
        rows = [{'path': pointer, 'change': 'array_representation', 'before': describe(before), 'after': describe(after),
                 'before_length': len(before), 'after_length': len(after),
                 'same_element_multiset': sorted(map(canonical, before)) == sorted(map(canonical, after))}]
        for i in range(max(len(before), len(after))):
            path = pointer + '/' + str(i)
            if i >= len(before):
                rows.append({'path': path, 'change': 'added', 'after': describe(after[i])})
            elif i >= len(after):
                rows.append({'path': path, 'change': 'removed', 'before': describe(before[i])})
            else:
                rows.extend(differences(before[i], after[i], path))
        return rows
    row = {'path': pointer, 'change': 'value_or_type', 'before': describe(before), 'after': describe(after)}
    a, b = instant(before), instant(after)
    if a is not None and b is not None:
        row['utc_instant_comparison'] = {'before_fraction_digits': a[1], 'after_fraction_digits': b[1],
                                         'after_minus_before_nanoseconds': b[0] - a[0]}
    return [row]


def compare_documents(before, after):
    def keyed(rows):
        result = {(r['index'], r['id']): r['source'] for r in rows}
        if len(result) != len(rows):
            raise ValueError('Duplicate index/document key')
        return result
    a, b = keyed(before), keyed(after)
    rows = []
    for key in sorted(set(a) | set(b)):
        row = {'index': key[0], 'id': key[1]}
        if key not in a:
            row.update(change='document_added', after=describe(b[key]))
        elif key not in b:
            row.update(change='document_removed', before=describe(a[key]))
        elif canonical(a[key]) != canonical(b[key]):
            row.update(change='document_changed', before=describe(a[key]), after=describe(b[key]), fields=differences(a[key], b[key]))
        else:
            continue
        rows.append(row)
    return {'before_documents': len(a), 'after_documents': len(b), 'changed_documents': rows}
