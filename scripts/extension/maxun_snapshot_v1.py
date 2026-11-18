"""Prepared stopped-container volume snapshots; not an execution registration.

Archives preserve ownership/modes/timestamps. Restores are verified by complete
entry inventories, without editing database values or normalizing identities.
Application/browser state must be supplied separately by the control harness.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import time

VOLUMES = {'postgres': '/var/lib/postgresql/data', 'minio': '/data'}


def file_sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def archive_inventory(path):
    result = {}
    with tarfile.open(path, 'r:*') as archive:
        for item in archive:
            name = PurePosixPath(item.name)
            if name.is_absolute() or '..' in name.parts:
                raise ValueError('Unsafe archive member path')
            key = str(name)
            if key in result:
                raise ValueError('Duplicate archive member')
            if not (item.isfile() or item.isdir()):
                raise ValueError('Unsupported link or special persistence entry')
            entry = dict(kind='directory' if item.isdir() else 'file', mode=item.mode,
                         uid=item.uid, gid=item.gid, mtime=item.mtime, bytes=item.size)
            if item.isfile():
                digest = hashlib.sha256()
                with archive.extractfile(item) as f:
                    for block in iter(lambda: f.read(1024 * 1024), b''):
                        digest.update(block)
                entry['sha256'] = digest.hexdigest()
            result[key] = entry
    if not result:
        raise ValueError('Empty persistence archive')
    return result


class VolumeSnapshots:
    def __init__(self, deadline):
        if os.environ.get('GITHUB_ACTIONS') != 'true':
            raise RuntimeError('Only registered CI control job may snapshot containers')
        self.deadline = deadline

    def command(self, args, **kwargs):
        seconds = self.deadline - time.time()
        if seconds <= 0:
            raise TimeoutError('Shared qualification deadline')
        return subprocess.run(args, check=True, timeout=min(90, seconds), **kwargs)

    def stopped(self, container):
        data = self.command(['docker', 'inspect', container], capture_output=True).stdout
        records = json.loads(data)
        if len(records) != 1 or records[0]['State']['Running'] or records[0]['State'].get('Paused'):
            raise ValueError('Snapshot requires a stopped container')
        state = records[0]['State']
        if state.get('ExitCode') != 0 or state.get('OOMKilled'):
            raise ValueError('Unclean container shutdown')
        return records[0]

    def export(self, container, role, path):
        self.stopped(container)
        # Exclusive creation preserves prior attempts and failed partial exports.
        with Path(path).open('xb') as output:
            self.command(['docker', 'cp', container + ':' + VOLUMES[role] + '/.', '-'], stdout=output)
        self.stopped(container)
        return archive_inventory(path)

    def capture(self, containers, destination):
        if set(containers) != set(VOLUMES):
            raise ValueError('Both registered persistence services are required')
        root = Path(destination)
        root.mkdir()  # No overwrite/repeat.
        record = {'status': 'started', 'volumes': {}, 'browser_state_included': False,
                  'application_layer_included': False, 'runtime_qualified': False}
        manifest = root / 'snapshot.json'
        try:
            # All persistence services must already be stopped, not just one at a time.
            for name in containers.values():
                self.stopped(name)
            for role, name in containers.items():
                path = root / (role + '.tar')
                inventory = self.export(name, role, path)
                record['volumes'][role] = {'archive': path.name, 'sha256': file_sha(path),
                                           'inventory': inventory, 'container': name}
            for name in containers.values():
                self.stopped(name)
            record['status'] = 'captured'
        except Exception as exc:
            record.update(status='unavailable', error=str(exc))
            raise
        finally:
            manifest.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
        return record

    def restore(self, source, containers, evidence):
        root, out = Path(source), Path(evidence)
        out.mkdir()  # Separate immutable branch evidence, no repeat.
        manifest = json.loads((root / 'snapshot.json').read_text())
        if manifest['status'] != 'captured' or set(containers) != set(VOLUMES):
            raise ValueError('Incomplete snapshot/restore roles')
        for name in containers.values():
            self.stopped(name)
        for role, name in containers.items():
            expected = manifest['volumes'][role]
            if expected['archive'] != role + '.tar':
                raise ValueError('Unexpected archive filename')
            path = root / expected['archive']
            if file_sha(path) != expected['sha256']:
                raise ValueError('Immutable snapshot changed')
            # Harness must create fresh empty destination volumes; leftover entries
            # are additionally detected by the complete post-copy inventory.
            with path.open('rb') as source_tar:
                self.command(['docker', 'cp', '-a', '-', name + ':' + VOLUMES[role]], stdin=source_tar)
            actual = self.export(name, role, out / (role + '.tar'))
            if actual != expected['inventory']:
                raise ValueError('Restored persistence inventory differs: ' + role)
            if file_sha(path) != expected['sha256']:
                raise ValueError('Snapshot changed during restoration')
        (out / 'restore.json').write_text(json.dumps({'status':'volume_restore_verified',
            'runtime_qualified':False,'browser_and_application_state_verified':False}) + '\n')
