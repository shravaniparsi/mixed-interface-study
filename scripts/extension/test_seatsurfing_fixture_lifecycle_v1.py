"""Synthetic transition tests; no Docker commands or application execution."""
import os
import unittest
from unittest.mock import patch
import seatsurfing_fixture_lifecycle_v1 as lifecycle


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, GITHUB_ACTIONS='true', GITHUB_REPOSITORY='shravaniparsi/mixed-interface-study', GITHUB_SHA='commit')
        self.env.start(); self.addCleanup(self.env.stop)
        self.items = []
        for name, image in [('app', 'app-image'), ('pg', lifecycle.checkpoint.PG_IMAGE_ID), ('browser', lifecycle.checkpoint.BROWSER_IMAGE_ID)]:
            self.items.append({'Id': name, 'RestartCount': 0, 'Image': image, 'Config': {'Labels': {'org.mixed-interface.study': lifecycle.LABEL}}, 'State': {'Running': True, 'Paused': False, 'Restarting': False, 'Pid': 123, 'StartedAt': '2026-11-18T00:00:00Z'}, 'HostConfig': {'NetworkMode': 'none' if name == 'pg' else 'container:pg', 'RestartPolicy': {'Name': 'no'}}})
        self.calls = []
        self.command = patch.object(lifecycle, 'command', side_effect=self.fake)
        self.command.start(); self.addCleanup(self.command.stop)
        self.bind = patch.object(lifecycle.checkpoint, 'bind_build', return_value='app-image')
        self.bind.start(); self.addCleanup(self.bind.stop)
        self.guard = patch.object(lifecycle.checkpoint, 'guard')
        self.guard_mock = self.guard.start(); self.addCleanup(self.guard.stop)
    def fake(self, argv):
        import json
        self.calls.append(argv)
        if argv[1] == 'inspect': return json.dumps(self.items).encode()
        item = self.items[2 if argv[-1] == lifecycle.checkpoint.BROWSER else 0]
        if argv[1] in ('pause', 'unpause'): item['State']['Paused'] = argv[1] == 'pause'
        elif argv[1] == 'stop': item['State']['Running'] = False
        else: self.fail(argv)
        return b''
    def make(self): return lifecycle.FixtureLifecycle({'study_commit': 'commit'})
    def test_same_process_pause_resume_order(self):
        state = self.make(); state.pause(); state.resume()
        actions = [c[1:] for c in self.calls if c[1] != 'inspect']
        self.assertEqual(actions, [['pause', lifecycle.checkpoint.BROWSER], ['pause', lifecycle.checkpoint.APP], ['unpause', lifecycle.checkpoint.APP], ['unpause', lifecycle.checkpoint.BROWSER]])
        self.assertEqual(state.phase, 'running'); self.guard_mock.assert_called_once()
    def test_active_database_failure_poisoned_no_retry(self):
        state = self.make(); self.guard_mock.side_effect = RuntimeError('active transaction')
        with self.assertRaisesRegex(RuntimeError, 'active transaction'): state.pause()
        count = len(self.calls)
        with self.assertRaises(RuntimeError): state.resume()
        self.assertEqual(len(self.calls), count); self.assertEqual(state.phase, 'failed')
    def test_container_replacement_rejected_before_mutation(self):
        state = self.make(); self.items[2]['Id'] = 'replacement'
        with self.assertRaisesRegex(RuntimeError, 'identity'): state.pause()
        self.assertFalse(any(c[1] == 'pause' for c in self.calls))
    def test_restarted_process_in_same_container_rejected(self):
        state = self.make(); self.items[0]['State']['Pid'] = 456
        with self.assertRaisesRegex(RuntimeError, 'process identity'): state.pause()
        self.assertFalse(any(c[1] == 'pause' for c in self.calls))
    def test_partial_pause_failure_not_rolled_back(self):
        state = self.make()
        def fail(argv):
            if argv == ['docker', 'pause', lifecycle.checkpoint.APP]: raise TimeoutError()
            return self.fake(argv)
        with patch.object(lifecycle, 'command', side_effect=fail):
            with self.assertRaises(TimeoutError): state.pause()
        self.assertEqual(state.phase, 'failed'); self.assertTrue(self.items[2]['State']['Paused'])
    def test_stop_requires_browser_actually_exited(self):
        state = self.make()
        with self.assertRaisesRegex(RuntimeError, 'stopped'): state.stop(lambda: None)
        self.assertEqual(state.phase, 'failed')
    def test_stop_checks_database_after_browser_exit(self):
        state = self.make()
        def close(): self.items[2]['State']['Running'] = False
        state.stop(close); self.assertEqual(state.phase, 'stopped'); self.guard_mock.assert_called_once()
    def test_stop_while_paused_does_not_close_worker(self):
        state = self.make(); state.pause()
        with self.assertRaises(RuntimeError): state.stop(lambda: self.fail('must not close'))
    def test_wrong_commit_rejected_without_docker(self):
        with self.assertRaisesRegex(RuntimeError, 'commit'): lifecycle.FixtureLifecycle({'study_commit': 'other'})
        self.assertEqual(self.calls, [])


if __name__ == '__main__': unittest.main()
