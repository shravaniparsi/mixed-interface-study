#!/usr/bin/env python3
"""Coordinate original-driver and mounted-file checkpoints. No application start.

All outputs are PRIVATE: database rows and Docker metadata contain credentials.
Caller supplies live quiescence checks and later verifies full restarted state;
this component alone cannot qualify native/API continuation equivalence.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from nginx_checkpoint_container_guard_v1 import inspect_container, verify_same_guard, LABEL, VALUE
from nginx_filesystem_checkpoint_v1 import canonical, separate, inventory, capture, restore
from nginx_sqlite_restore_v1 import restore_database_file, digest

ROOT = Path(__file__).resolve().parents[2]


def require_quiescence(proof):
    required = ('browser_requests_settled', 'application_operations_settled',
                'empty_certificate_fixture_verified', 'initial_certificate_timer_settled',
                'token_unchanged', 'refresh_outside_checkpoint_interval')
    if not isinstance(proof, dict) or any(proof.get(k) is not True for k in required):
        raise ValueError('Live caller quiescence evidence incomplete')
    if not re.fullmatch(r'[0-9a-f]{64}', proof.get('observation_sha256', '')):
        raise ValueError('Retained live observation identity missing')
    return proof


def validate_checkpoint_trees(checkpoint):
    """Prevalidate BOTH trees before any destination tree is removed."""
    for name in ('data', 'certificates'):
        directory = checkpoint / name
        expected = json.loads((directory / 'manifest.json').read_text())
        if inventory(directory / 'tree') != expected:
            raise ValueError(f'Corrupt {name} checkpoint; both destinations untouched')


class NginxCheckpoint:
    def __init__(self, container, image_id, data_root, certificates_root):
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', image_id):
            raise ValueError('Built immutable image ID required')
        self.container = container
        self.image_id = image_id
        self.roots = {'/data': str(canonical(data_root)), '/etc/letsencrypt': str(canonical(certificates_root))}
        separate(data_root, certificates_root)

    def command(self, args, timeout=15):
        return subprocess.check_output(['docker', *args], timeout=timeout)

    def metadata(self):
        raw = self.command(['inspect', '--type', 'container', self.container])
        if len(raw) > 1024 * 1024:
            raise ValueError('Container metadata bound')
        item, = json.loads(raw)
        if item['Config'].get('Labels', {}).get(LABEL) != VALUE:
            raise ValueError('Not the disposable study application')
        if item['Image'] != self.image_id:
            raise ValueError('Application differs from verified build')
        if item['HostConfig']['RestartPolicy']['Name'] not in ('', 'no'):
            raise ValueError('Automatic restart is not admitted')
        return item

    def database(self, operation, source_root, output, backup_directory=None, private_copy=False):
        """Use the installed original driver with the state mount READ ONLY."""
        output = canonical(output)
        if private_copy:
            if operation != 'inspect':
                raise ValueError('Private copy is inspection only')
            for root in self.roots.values():
                separate(root, source_root)
        name = 'study-nginx-checkpoint-database'
        args = ['docker', 'run', '--rm', '--name', name, '--network', 'none',
                '--user', f'{os.getuid()}:{os.getgid()}', '--entrypoint', 'node',
                '-v', f'{ROOT}:{ROOT}:ro', '-v', f'{canonical(source_root)}:/state:{"rw" if private_copy else "ro"}']
        if operation == 'capture':
            args += ['-v', f'{canonical(backup_directory)}:/checkpoint:rw']
        args += [self.image_id, str(ROOT / 'scripts/extension/nginx_database_command_v1.mjs'),
                 operation, '/state/database.sqlite']
        if operation == 'capture':
            args += ['/checkpoint/database.sqlite']
        try:
            with output.open('xb') as stream:
                subprocess.run(args, stdout=stream, stderr=subprocess.PIPE, check=True, timeout=45)
            if output.stat().st_size > 128 * 1024 * 1024:
                raise ValueError('Database evidence bound')
            return json.loads(output.read_text())
        finally:
            subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=15, check=False)

    def capture(self, checkpoint, live_quiescence_check):
        checkpoint = canonical(checkpoint)
        for root in self.roots.values():
            separate(root, checkpoint)
        checkpoint.mkdir(mode=0o700, exist_ok=False)
        metadata = self.metadata()
        if metadata['State']['Running'] is not True or metadata['State']['Paused']:
            raise ValueError('Capture must begin with the original warm process running')
        report = {'status': 'capturing_unqualified', 'container_id': metadata['Id'],
                  'image_id': self.image_id, 'roots': self.roots}
        def save():
            (checkpoint / 'coordination.json').write_text(json.dumps(report, indent=2) + '\n')
        save()
        paused = False
        try:
            report['quiescence_before'] = require_quiescence(live_quiescence_check())
            database = self.database('capture', self.roots['/data'], checkpoint / 'database-capture.json', checkpoint)
            report['backup_sha256'] = database['backupSha256']
            self.command(['pause', self.container])
            paused = True
            guard = inspect_container(self.container, 'capture', self.roots)
            if guard['container_id'] != metadata['Id']:
                raise ValueError('Container replaced before pause')
            report['data'] = capture(self.roots['/data'], checkpoint / 'data')
            report['certificates'] = capture(self.roots['/etc/letsencrypt'], checkpoint / 'certificates')
            # Preserve complete metadata/diff; do not silently classify root-layer
            # changes as irrelevant. The full runtime comparison consumes these.
            (checkpoint / 'paused-container.json').write_text(json.dumps(self.metadata(), indent=2) + '\n')
            (checkpoint / 'container-diff.txt').write_bytes(self.command(['diff', self.container]))
            verify_same_guard(guard, inspect_container(self.container, 'capture', self.roots))
            self.command(['unpause', self.container])
            paused = False
            resumed = self.metadata()
            if resumed['Id'] != metadata['Id'] or resumed['State']['Pid'] != metadata['State']['Pid'] or resumed['State']['StartedAt'] != metadata['State']['StartedAt']:
                raise ValueError('Warm application process changed during capture')
            current = self.database('inspect', self.roots['/data'], checkpoint / 'database-resumed.json')
            copied = self.database('inspect', checkpoint / 'data/tree', checkpoint / 'database-raw-copy.json')
            if current['state'] != database['before']['state'] or copied['state'] != database['before']['state']:
                raise ValueError('Database changed across paused filesystem capture')
            if digest(checkpoint / 'database.sqlite') != report['backup_sha256']:
                raise ValueError('Standalone backup changed')
            report['quiescence_after'] = require_quiescence(live_quiescence_check())
            report['status'] = 'database_and_mount_checkpoint_captured_runtime_unqualified'
            save()
            return report
        except Exception as error:
            report.update(status='checkpoint_failed', error_type=type(error).__name__, error=str(error))
            save()
            raise
        finally:
            if paused:
                self.command(['unpause', self.container])

    def stop_and_restore(self, checkpoint, evidence):
        checkpoint, evidence = canonical(checkpoint), canonical(evidence)
        for root in self.roots.values():
            separate(root, checkpoint)
            separate(root, evidence)
        separate(checkpoint, evidence)
        evidence.mkdir(mode=0o700, exist_ok=False)
        saved = json.loads((checkpoint / 'coordination.json').read_text())
        if saved['status'] != 'database_and_mount_checkpoint_captured_runtime_unqualified':
            raise ValueError('Incomplete checkpoint')
        if saved['roots'] != self.roots or saved['image_id'] != self.image_id:
            raise ValueError('Checkpoint belongs to different state roots/image')
        current = self.metadata()
        if current['Id'] != saved['container_id']:
            raise ValueError('Checkpoint belongs to a different original container')
        if current['State']['Running'] is not True or current['State']['Paused']:
            raise ValueError('Restore expects the original running branch, not an unexplained exit')
        # Corrupt backup or either corrupt tree must fail before stopping writers
        # or touching either mounted state tree.
        validate_checkpoint_trees(checkpoint)
        if digest(checkpoint / 'database.sqlite') != saved['backup_sha256']:
            raise ValueError('Standalone backup identity mismatch')
        expected = json.loads((checkpoint / 'database-capture.json').read_text())['before']['state']
        self.command(['stop', '--time', '20', self.container], timeout=30)
        guard = inspect_container(self.container, 'restore', self.roots)
        if guard['container_id'] != saved['container_id']:
            raise ValueError('Container identity changed while stopping')
        # Validation above is repeated by restore() immediately before each copy.
        # A partial failure leaves the application stopped; it never starts here.
        result = {'status': 'restoring_application_stopped'}
        try:
            result['data'] = restore(self.roots['/data'], checkpoint / 'data')
            verify_same_guard(guard, inspect_container(self.container, 'restore', self.roots))
            result['certificates'] = restore(self.roots['/etc/letsencrypt'], checkpoint / 'certificates')
            verify_same_guard(guard, inspect_container(self.container, 'restore', self.roots))
            result['database'] = restore_database_file(self.container, self.roots['/data'],
                self.roots['/etc/letsencrypt'], checkpoint / 'database.sqlite', saved['backup_sha256'])
            # A standalone WAL-mode file can need new auxiliary files even for
            # a read-only SQL connection. Inspect an exact private byte copy in
            # a writable directory, leaving restored application state untouched.
            copy_root = evidence / 'inspection-copy'
            copy_root.mkdir()
            original = Path(self.roots['/data']) / 'database.sqlite'
            copied = copy_root / 'database.sqlite'
            shutil.copyfile(original, copied)
            if digest(original) != saved['backup_sha256'] or digest(copied) != saved['backup_sha256']:
                raise ValueError('Restored inspection copy differs')
            logical = self.database('inspect', copy_root, evidence / 'database-restored.json', private_copy=True)
            if digest(original) != saved['backup_sha256'] or digest(copied) != saved['backup_sha256']:
                raise ValueError('Database bytes changed during logical inspection')
            if logical['state'] != expected:
                raise ValueError('Restored original-driver logical state differs')
            verify_same_guard(guard, inspect_container(self.container, 'restore', self.roots))
            result['status'] = 'database_and_mounts_restored_stopped_runtime_unqualified'
            return result
        except Exception as error:
            result.update(status='restore_failed_application_left_stopped', error_type=type(error).__name__, error=str(error))
            raise
        finally:
            (evidence / 'restore.json').write_text(json.dumps(result, indent=2) + '\n')
