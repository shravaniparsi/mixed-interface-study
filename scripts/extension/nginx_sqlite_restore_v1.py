#!/usr/bin/env python3
"""Replace a disposable stopped application's SQLite file with a verified backup.

No container lifecycle or application startup. Full driver-level logical-state
verification must follow before any original application process is restarted.
"""
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile

from nginx_checkpoint_container_guard_v1 import inspect_container, verify_same_guard

MAX_BYTES = 64 * 1024 * 1024
SIDECARS = ('database.sqlite-wal', 'database.sqlite-shm', 'database.sqlite-journal')

def canonical(path):
    path = Path(path).absolute()
    if path.resolve() != path or path.is_symlink(): raise ValueError('Canonical non-symlink path required')
    return path

def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''): result.update(chunk)
    return result.hexdigest()

def regular(path):
    if not hasattr(os, 'listxattr'): raise RuntimeError('Native extended-attribute inspection required')
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError('SQLite state must be a single regular file')
    if info.st_size > MAX_BYTES: raise ValueError('SQLite file byte bound')
    if os.listxattr(path, follow_symlinks=False): raise ValueError('Unqualified SQLite extended attributes')
    return info

def signature(path):
    info = regular(path)
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid, digest(path))

def restore_database_file(container, data_root, certificates_root, backup, expected_sha256):
    if not re.fullmatch(r'[0-9a-f]{64}', expected_sha256): raise ValueError('Full backup SHA256 required')
    roots = {'/data': str(canonical(data_root)), '/etc/letsencrypt': str(canonical(certificates_root))}
    backup = canonical(backup)
    for root in map(Path, roots.values()):
        if root == backup or root in backup.parents: raise ValueError('Backup must be outside both writable state roots')
    guard = inspect_container(container, 'restore', roots)
    regular(backup)
    if digest(backup) != expected_sha256: raise ValueError('Backup identity mismatch; destination untouched')
    database = Path(roots['/data']) / 'database.sqlite'
    original = signature(database)
    metadata = database.stat()
    sidecars = {}
    for name in SIDECARS:
        path = database.parent / name
        if os.path.lexists(path): sidecars[name] = signature(path)
    descriptor, temporary_name = tempfile.mkstemp(prefix='.study-database-restore-', dir=database.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, 'wb') as target, backup.open('rb') as source:
            shutil.copyfileobj(source, target, 1024 * 1024)
            target.flush(); os.fsync(target.fileno())
        if digest(temporary) != expected_sha256 or digest(backup) != expected_sha256:
            raise ValueError('Backup changed or staging copy differs')
        current = temporary.stat()
        if (current.st_uid, current.st_gid) != (metadata.st_uid, metadata.st_gid):
            os.chown(temporary, metadata.st_uid, metadata.st_gid)
        os.chmod(temporary, stat.S_IMODE(metadata.st_mode))
        os.utime(temporary, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
        verify_same_guard(guard, inspect_container(container, 'restore', roots))
        if signature(database) != original: raise ValueError('Destination changed before replacement')
        for name in SIDECARS:
            path = database.parent / name
            if os.path.lexists(path) != (name in sidecars): raise ValueError('SQLite sidecar set changed')
            if name in sidecars and signature(path) != sidecars[name]: raise ValueError('SQLite sidecar changed')
        os.replace(temporary, database)
        # A standalone backup must not be combined with the old database's journals.
        for name in sidecars: (database.parent / name).unlink()
        directory_fd = os.open(database.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory_fd)
        finally: os.close(directory_fd)
        verify_same_guard(guard, inspect_container(container, 'restore', roots))
        if digest(database) != expected_sha256: raise ValueError('Restored file differs from verified backup')
        if any(os.path.lexists(database.parent / name) for name in SIDECARS): raise ValueError('Unexpected SQLite sidecar after restore')
        return {'status': 'database_bytes_restored_logical_state_and_application_unqualified',
                'backup_sha256': expected_sha256, 'previous_database_sha256': original[-1],
                'removed_sidecars': sorted(sidecars), 'container_guard': guard}
    finally:
        if temporary.exists(): temporary.unlink()
