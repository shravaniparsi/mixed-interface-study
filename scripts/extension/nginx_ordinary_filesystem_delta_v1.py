"""Check one ordinary edit's filesystem delta, not restart equivalence.

Database and credential predicates run here; no caller-supplied success flags.
Snapshots/raw access bytes and the returned diff are private evidence.
"""
import hashlib
import math
from pathlib import PurePosixPath

from nginx_ordinary_database_comparison_v1 import normalize_ordinary_database
from nginx_access_file_comparison_v1 import ordinary_credential, verify_access_file

ROOTS = {'/data', '/etc/letsencrypt', '/etc/nginx', '/tmp/nginx',
         '/var/lib/nginx/cache', '/var/cache/nginx', '/var/log/nginx',
         '/run/nginx', '/var/lib/logrotate'}
DB = '/data/database.sqlite'
SIDECARS = {DB + suffix for suffix in ('-wal', '-shm', '-journal')}


def flatten(observation):
    inventories = observation['inventories']
    if set(inventories) != ROOTS or observation.get('extendedAttributesAbsent') is not True:
        raise ValueError('Complete registered roots and xattr observation required')
    result = {}
    for root, rows in inventories.items():
        for row in rows:
            rel = row['path']
            if not isinstance(rel, str) or (rel != '.' and
                    (str(PurePosixPath(rel)) != rel or rel.startswith('/') or '..' in PurePosixPath(rel).parts)):
                raise ValueError('Noncanonical inventory path')
            absolute = root if rel == '.' else root + '/' + rel
            if absolute in result:
                raise ValueError('Duplicate inventory path')
            if row.get('kind') not in ('file', 'directory', 'symlink'):
                raise ValueError('Unsupported inventory kind')
            result[absolute] = row
        if root not in result or result[root]['kind'] != 'directory':
            raise ValueError('Missing directory root')
    return result


def verify_delta(before, after, window, list_id):
    """Inventory portion only; public entry point below also checks DB/credentials."""
    if type(list_id) is not int or list_id <= 0:
        raise ValueError('Positive subject ID required')
    start, end = window['start_epoch_seconds'], window['end_epoch_seconds']
    if window.get('timezone') != 'UTC' or not all(type(v) in (int, float) and math.isfinite(v) for v in (start, end)) or not 0 <= end-start <= 120:
        raise ValueError('Invalid operation window')
    low, high = math.floor(start * 1e9), math.ceil(end * 1e9)
    old, new = flatten(before), flatten(after)
    access = '/data/access/' + str(list_id)
    if any(path not in old or path not in new for path in (DB, access, '/data/access')):
        raise ValueError('Ordinary database/access fixture missing')
    for state in (old, new):
        if state[DB]['kind'] != 'file' or state[access]['kind'] != 'file' or state['/data/access']['kind'] != 'directory':
            raise ValueError('Unexpected ordinary fixture kind')
    changed = []
    for path in sorted(old.keys() | new.keys()):
        a, b = old.get(path), new.get(path)
        if a == b:
            continue
        changed.append({'path': path, 'before': a, 'after': b})
        if path in SIDECARS:
            for row in (a, b):
                if row is not None and (row['kind'] != 'file' or any(row[k] != old[DB][k] for k in ('mode', 'uid', 'gid'))):
                    raise ValueError('Unexpected database sidecar identity')
            # Sidecar absence/replacement is checked with the complete original-
            # driver logical database below, never mixed into a restored backup.
            continue
        if a is None or b is None:
            raise ValueError('Unregistered filesystem path addition/removal: ' + path)
        if path not in {DB, access, '/data', '/data/access'}:
            raise ValueError('Unrelated filesystem state changed: ' + path)
        mutable = {'mtimeNs'} if path in {'/data', '/data/access'} else {'mtimeNs', 'sha256', 'bytes'}
        if {k:v for k,v in a.items() if k not in mutable} != {k:v for k,v in b.items() if k not in mutable}:
            raise ValueError('Filesystem ownership/mode/kind changed: ' + path)
        expected_kind = 'directory' if path in {'/data', '/data/access'} else 'file'
        if b['kind'] != expected_kind:
            raise ValueError('Unexpected ordinary fixture kind')
        if a['mtimeNs'] != b['mtimeNs']:
            raw = b['mtimeNs']
            if not isinstance(raw, str) or str(int(raw)) != raw or not low <= int(raw) <= high:
                raise ValueError('Filesystem write timestamp outside operation: ' + path)
    return changed


def verify_ordinary_filesystem_delta(before, after, before_database, after_database,
        list_id, actor_id, edit, window, before_access, after_access, derive_hash):
    database = normalize_ordinary_database(before_database, after_database, list_id, actor_id, edit, window)
    changes = verify_delta(before, after, window, list_id)
    path = '/data/access/' + str(list_id)
    access_evidence = []
    for observation, state, raw in ((before, before_database, before_access), (after, after_database, after_access)):
        row = flatten(observation)[path]
        evidence = verify_access_file(raw, ordinary_credential(state, list_id), derive_hash)
        if row['kind'] != 'file' or row['sha256'] != hashlib.sha256(raw).hexdigest() or row['bytes'] != len(raw):
            raise ValueError('Credential bytes differ from runtime inventory')
        access_evidence.append(evidence)
    return {'status': 'ordinary_operation_delta_checked_restart_equivalence_unqualified',
            'changes': changes, 'database_timestamps': database['timestamp_evidence'],
            'access_files': access_evidence}
