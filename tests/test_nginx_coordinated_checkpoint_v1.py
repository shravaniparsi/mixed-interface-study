"""Failure sequencing with mocked Docker/driver operations, not runtime proof."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

EXTENSION = Path(__file__).resolve().parents[1] / 'scripts/extension'
sys.path.insert(0, str(EXTENSION))
spec = importlib.util.spec_from_file_location('nginx_coordination', EXTENSION / 'nginx_coordinated_checkpoint_v1.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CoordinatedCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.data = self.root / 'data'; self.data.mkdir()
        self.certificates = self.root / 'certificates'; self.certificates.mkdir()
        self.image = 'sha256:' + 'a' * 64
        self.checkpoint = self.root / 'checkpoint'
        self.evidence = self.root / 'restore-evidence'
        self.coordinator = module.NginxCheckpoint('study-nginx', self.image, self.data, self.certificates)
        self.metadata = {'Id': 'original-container', 'State': {'Running': True, 'Paused': False, 'Pid': 100, 'StartedAt': 'start'}}
        self.coordinator.metadata = Mock(return_value=self.metadata)
        self.coordinator.command = Mock(return_value=b'')
        self.guard = {'container_id': 'original-container'}
        self.proof = {key: True for key in ('browser_requests_settled', 'application_operations_settled',
                      'empty_certificate_fixture_verified', 'initial_certificate_timer_settled',
                      'token_unchanged', 'refresh_outside_checkpoint_interval')}
        self.proof['observation_sha256'] = 'b' * 64
        self.state = {'schema': [], 'tables': []}
        self.backup_bytes = b'synthetic test bytes, not a SQLite database'
        self.backup_hash = hashlib.sha256(self.backup_bytes).hexdigest()

    def prepare_restore(self):
        self.checkpoint.mkdir()
        (self.checkpoint / 'database.sqlite').write_bytes(self.backup_bytes)
        (self.checkpoint / 'database-capture.json').write_text(json.dumps({'before': {'state': self.state}}))
        (self.checkpoint / 'coordination.json').write_text(json.dumps({
            'status': 'database_and_mount_checkpoint_captured_runtime_unqualified',
            'roots': self.coordinator.roots, 'image_id': self.image,
            'container_id': 'original-container', 'backup_sha256': self.backup_hash,
        }))
        for name in ('data', 'certificates'):
            directory = self.checkpoint / name; directory.mkdir()
            (directory / 'manifest.json').write_text('[]')
        (self.data / 'database.sqlite').write_bytes(self.backup_bytes)

    def test_reject_unsettled_capture_without_pausing_or_reading_database(self):
        self.coordinator.database = Mock()
        self.proof['application_operations_settled'] = False
        with self.assertRaisesRegex(ValueError, 'quiescence'):
            self.coordinator.capture(self.checkpoint, lambda: self.proof)
        self.coordinator.command.assert_not_called()
        self.coordinator.database.assert_not_called()

    def test_capture_copy_failure_resumes_warm_process(self):
        self.coordinator.database = Mock(return_value={'backupSha256': self.backup_hash})
        with patch.object(module, 'inspect_container', return_value=self.guard), patch.object(module, 'capture', side_effect=OSError('copy failed')):
            with self.assertRaisesRegex(OSError, 'copy failed'):
                self.coordinator.capture(self.checkpoint, lambda: self.proof)
        calls = [call.args[0][0] for call in self.coordinator.command.call_args_list]
        self.assertEqual(calls, ['pause', 'unpause'])
        self.assertTrue(all(call.args[0][-1] == 'original-container' for call in self.coordinator.command.call_args_list))
        report = json.loads((self.checkpoint / 'coordination.json').read_text())
        self.assertEqual(report['status'], 'checkpoint_failed')

    def test_corrupt_second_tree_does_not_stop_or_mutate_either_destination(self):
        self.prepare_restore()
        def actual(path):
            return [{'changed': True}] if path.parent.name == 'certificates' else []
        with patch.object(module, 'inventory', side_effect=actual), patch.object(module, 'restore') as restore:
            with self.assertRaisesRegex(ValueError, 'Corrupt certificates'):
                self.coordinator.stop_and_restore(self.checkpoint, self.evidence)
            restore.assert_not_called()
        self.coordinator.command.assert_not_called()

    def test_bad_backup_does_not_stop_application(self):
        self.prepare_restore()
        (self.checkpoint / 'database.sqlite').write_bytes(b'corrupt')
        with patch.object(module, 'inventory', return_value=[]), patch.object(module, 'restore') as restore:
            with self.assertRaisesRegex(ValueError, 'backup identity'):
                self.coordinator.stop_and_restore(self.checkpoint, self.evidence)
            restore.assert_not_called()
        self.coordinator.command.assert_not_called()

    def test_second_restore_failure_leaves_application_stopped(self):
        self.prepare_restore()
        with patch.object(module, 'inventory', return_value=[]), patch.object(module, 'inspect_container', return_value=self.guard), patch.object(module, 'restore', side_effect=[{}, OSError('certificate restore failed')]), patch.object(module, 'restore_database_file') as database:
            with self.assertRaisesRegex(OSError, 'certificate restore failed'):
                self.coordinator.stop_and_restore(self.checkpoint, self.evidence)
            database.assert_not_called()
        self.assertEqual([c.args[0][0] for c in self.coordinator.command.call_args_list], ['stop'])
        self.assertEqual(self.coordinator.command.call_args.args[0][-1], 'original-container')
        report = json.loads((self.evidence / 'restore.json').read_text())
        self.assertEqual(report['status'], 'restore_failed_application_left_stopped')

    def test_logical_mismatch_is_failure_with_no_application_start(self):
        self.prepare_restore()
        self.coordinator.database = Mock(return_value={'state': {'changed': True}})
        with patch.object(module, 'inventory', return_value=[]), patch.object(module, 'inspect_container', return_value=self.guard), patch.object(module, 'restore', return_value={}), patch.object(module, 'restore_database_file', return_value={}):
            with self.assertRaisesRegex(ValueError, 'logical state differs'):
                self.coordinator.stop_and_restore(self.checkpoint, self.evidence)
        self.assertEqual([c.args[0][0] for c in self.coordinator.command.call_args_list], ['stop'])
        self.assertEqual((self.data / 'database.sqlite').read_bytes(), self.backup_bytes)
        self.assertTrue(self.coordinator.database.call_args.kwargs['private_copy'])

    def test_success_still_reports_runtime_unqualified_and_leaves_stopped(self):
        self.prepare_restore()
        self.coordinator.database = Mock(return_value={'state': self.state})
        with patch.object(module, 'inventory', return_value=[]), patch.object(module, 'inspect_container', return_value=self.guard), patch.object(module, 'restore', return_value={}), patch.object(module, 'restore_database_file', return_value={}):
            result = self.coordinator.stop_and_restore(self.checkpoint, self.evidence)
        self.assertEqual(result['status'], 'database_and_mounts_restored_stopped_runtime_unqualified')
        self.assertEqual([c.args[0][0] for c in self.coordinator.command.call_args_list], ['stop'])


if __name__ == '__main__':
    unittest.main()
