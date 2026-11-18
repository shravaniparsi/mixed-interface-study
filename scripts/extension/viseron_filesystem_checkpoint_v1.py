#!/usr/bin/env python3
"""Offline config-volume checkpoint. CLI only operates on /state in a container.

The caller must verify the application is stopped and mount only its disposable
configuration volume at /state. Checkpoints contain authentication secrets and
must stay private. Public reports contain aggregate fingerprints only.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def inventory(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError('State root must be a real directory')
    rows = []
    for path in [root, *sorted(root.rglob('*'))]:
        info = path.lstat()
        if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise RuntimeError('Unsupported non-regular state entry')
        if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise RuntimeError('Hard-linked state is unsupported')
        if os.listxattr(path):
            raise RuntimeError('Extended attributes require separate qualification')
        row = {'path': path.relative_to(root).as_posix(),
               'kind': 'directory' if path.is_dir() else 'file',
               'mode': stat.S_IMODE(info.st_mode), 'uid': info.st_uid,
               'gid': info.st_gid, 'mtime_ns': info.st_mtime_ns}
        if row['kind'] == 'file':
            raw = path.read_bytes()
            row.update(bytes=len(raw), sha256=digest(raw))
        rows.append(row)
    return rows


def fingerprint(rows):
    return digest(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode())


def validate_paths(root, checkpoint):
    root, checkpoint = Path(root).absolute(), Path(checkpoint).absolute()
    # Reject symlinked ancestors and overlapping locations before any mutation.
    for path in (root, checkpoint):
        if path.resolve() != path:
            raise RuntimeError('Paths must be canonical and cannot contain symlinks')
    if root == checkpoint or root in checkpoint.parents or checkpoint in root.parents:
        raise RuntimeError('State and checkpoint locations must not overlap')


def copy_tree(source, target, rows):
    target.mkdir(exist_ok=True)
    for row in rows:
        src, dst = source / row['path'], target / row['path']
        if row['kind'] == 'directory':
            dst.mkdir(exist_ok=True)
        else:
            shutil.copyfile(src, dst)
    # Restore directories last because creating descendants changes their mtimes.
    for row in reversed(rows):
        dst = target / row['path']
        current = dst.stat()
        if (current.st_uid, current.st_gid) != (row['uid'], row['gid']):
            os.chown(dst, row['uid'], row['gid'])
        os.chmod(dst, row['mode'])
        os.utime(dst, ns=(row['mtime_ns'], row['mtime_ns']))


def capture(root, checkpoint):
    root, checkpoint = Path(root), Path(checkpoint)
    validate_paths(root, checkpoint)
    if checkpoint.exists():
        raise RuntimeError('Refuse checkpoint overwrite')
    before = inventory(root)
    checkpoint.mkdir(mode=0o700, parents=True)
    copy_tree(root, checkpoint / 'tree', before)
    if inventory(root) != before or inventory(checkpoint / 'tree') != before:
        raise RuntimeError('State changed during capture or copy lost metadata')
    (checkpoint / 'manifest.json').write_text(json.dumps(before, sort_keys=True))
    return {'status': 'filesystem_checkpoint_captured', 'state_sha256': fingerprint(before),
            'entries': len(before)}


def restore(root, checkpoint):
    root, checkpoint = Path(root), Path(checkpoint)
    validate_paths(root, checkpoint)
    before = inventory(root)  # Validate destination before any deletion.
    rows = json.loads((checkpoint / 'manifest.json').read_text())
    # Inspect actual files and compare before trusting manifest paths or deleting.
    if inventory(checkpoint / 'tree') != rows:
        raise RuntimeError('Checkpoint content or metadata mismatch')
    for item in root.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
    copy_tree(checkpoint / 'tree', root, rows)
    actual = inventory(root)
    if actual != rows:
        raise RuntimeError('Restored filesystem differs from checkpoint')
    return {'status': 'filesystem_restore_matches', 'state_sha256': fingerprint(actual),
            'previous_state_sha256': fingerprint(before), 'entries': len(actual)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['capture', 'restore', 'inspect'])
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    root = Path('/state')
    if not Path('/.dockerenv').is_file() or not root.is_mount():
        raise RuntimeError('Only a container-mounted /state volume is permitted')
    validate_paths(root, args.checkpoint)
    validate_paths(root, args.report)
    validate_paths(args.checkpoint, args.report)
    if args.report.exists():
        raise RuntimeError('Refuse report overwrite')
    if args.action == 'inspect':
        rows = inventory(root)
        report = {'status': 'filesystem_inspected', 'state_sha256': fingerprint(rows),
                  'entries': len(rows)}
    else:
        report = (capture if args.action == 'capture' else restore)(root, args.checkpoint)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
