#!/usr/bin/env python3
"""Private offline/quiescent filesystem checkpoints; no Docker lifecycle here.

Caller must establish authoritative quiescence before capture and stopped writers
before restore. This module never traverses symlinks. No public raw state output.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat

MAX_ENTRIES = 20000
MAX_BYTES = 1024 * 1024 * 1024

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()

def canonical(path):
    path = Path(path).absolute()
    if path.resolve() != path or path.is_symlink():
        raise ValueError('Root/ancestors must be canonical, without symlinks')
    return path

def separate(root, checkpoint):
    root, checkpoint = canonical(root), canonical(checkpoint)
    if root == checkpoint or root in checkpoint.parents or checkpoint in root.parents:
        raise ValueError('State and checkpoint must not overlap')
    return root, checkpoint

def inventory(root):
    root = canonical(root)
    if not hasattr(os, 'listxattr'):
        raise RuntimeError('Native listxattr support is required; filesystem checkpoint is unavailable')
    if not root.is_dir(): raise ValueError('State root must be a directory')
    paths = [root]
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files: paths.append(Path(directory) / name)
        if len(paths) > MAX_ENTRIES: raise ValueError('Filesystem entry bound')
    rows = []; total = 0
    for path in sorted(paths, key=lambda p: p.relative_to(root).as_posix()):
        info = path.lstat()
        if os.listxattr(path, follow_symlinks=False):
            raise ValueError('Extended attributes require separate qualification')
        row = {'path': path.relative_to(root).as_posix(), 'mode': stat.S_IMODE(info.st_mode),
               'uid': info.st_uid, 'gid': info.st_gid, 'mtime_ns': info.st_mtime_ns}
        if stat.S_ISLNK(info.st_mode):
            row.update(kind='symlink', target=os.readlink(path))
        elif stat.S_ISDIR(info.st_mode): row['kind'] = 'directory'
        elif stat.S_ISREG(info.st_mode):
            if info.st_nlink != 1: raise ValueError('Hard-linked state is unsupported')
            total += info.st_size
            if total > MAX_BYTES: raise ValueError('Filesystem byte bound')
            row.update(kind='file', bytes=info.st_size, sha256=sha(path))
        else: raise ValueError('Unsupported special filesystem entry')
        rows.append(row)
    return rows

def fingerprint(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def copy_tree(source, target, rows):
    target.mkdir(exist_ok=True)
    for row in rows:
        src, dst = source / row['path'], target / row['path']
        if row['kind'] == 'directory': dst.mkdir(exist_ok=True)
        elif row['kind'] == 'symlink': os.symlink(row['target'], dst)
        else: shutil.copyfile(src, dst, follow_symlinks=False)
    for row in reversed(rows):
        dst = target / row['path']; current = dst.lstat()
        if (current.st_uid, current.st_gid) != (row['uid'], row['gid']):
            os.chown(dst, row['uid'], row['gid'], follow_symlinks=False)
        if row['kind'] != 'symlink': os.chmod(dst, row['mode'], follow_symlinks=False)
        os.utime(dst, ns=(row['mtime_ns'], row['mtime_ns']), follow_symlinks=False)

def capture(root, checkpoint):
    root, checkpoint = separate(root, checkpoint)
    if checkpoint.exists(): raise ValueError('Never overwrite a checkpoint')
    before = inventory(root)
    checkpoint.mkdir(parents=True, mode=0o700)
    copy_tree(root, checkpoint / 'tree', before)
    if inventory(root) != before or inventory(checkpoint / 'tree') != before:
        raise ValueError('Source changed or checkpoint lost metadata')
    (checkpoint / 'manifest.json').write_text(json.dumps(before, sort_keys=True) + '\n')
    return {'status': 'filesystem_component_captured', 'sha256': fingerprint(before), 'entries': len(before)}

def restore(root, checkpoint):
    root, checkpoint = separate(root, checkpoint)
    before = inventory(root)
    rows = json.loads((checkpoint / 'manifest.json').read_text())
    # Actual tree inventory, not untrusted manifest paths, establishes safety.
    if inventory(checkpoint / 'tree') != rows:
        raise ValueError('Checkpoint content/metadata mismatch; destination untouched')
    for entry in root.iterdir():
        if entry.is_symlink() or not entry.is_dir(): entry.unlink()
        else: shutil.rmtree(entry)
    copy_tree(checkpoint / 'tree', root, rows)
    actual = inventory(root)
    if actual != rows: raise ValueError('Restored filesystem differs from checkpoint')
    return {'status': 'filesystem_component_restored', 'sha256': fingerprint(actual),
            'previous_sha256': fingerprint(before), 'entries': len(actual)}
