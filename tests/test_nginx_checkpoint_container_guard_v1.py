import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('guard', ROOT / 'scripts/extension/nginx_checkpoint_container_guard_v1.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name).resolve()
        self.roots = {'/data': str(base / 'data'), '/etc/letsencrypt': str(base / 'certs')}
        self.info = {'Id': 'fixture-id', 'Config': {'Labels': {m.LABEL: m.VALUE}},
            'HostConfig': {'RestartPolicy': {'Name': 'no'}},
            'State': {'Running': True, 'Paused': True, 'Pid': 123, 'Dead': False, 'Restarting': False, 'StartedAt': 'fixture-start'},
            'Mounts': [{'Destination': k, 'Source': v, 'Type': 'bind', 'RW': True} for k,v in self.roots.items()]}
    def test_capture_requires_actual_paused_state_fields(self):
        m.validate_inspection(self.info, 'capture', self.roots)
        self.info['State']['Paused'] = False
        with self.assertRaises(ValueError): m.validate_inspection(self.info, 'capture', self.roots)
    def test_restore_refuses_live_or_paused_writers(self):
        with self.assertRaises(ValueError): m.validate_inspection(self.info, 'restore', self.roots)
        self.info['State'].update(Running=False, Paused=False, Pid=0)
        m.validate_inspection(self.info, 'restore', self.roots)
    def test_wrong_label_and_automatic_restart_rejected(self):
        other = copy.deepcopy(self.info); other['Config']['Labels'] = {}
        with self.assertRaises(ValueError): m.validate_inspection(other, 'capture', self.roots)
        self.info['HostConfig']['RestartPolicy']['Name'] = 'always'
        with self.assertRaises(ValueError): m.validate_inspection(self.info, 'capture', self.roots)
    def test_wrong_mount_rejected(self):
        self.info['Mounts'][0]['Source'] += '-other'
        with self.assertRaises(ValueError): m.validate_inspection(self.info, 'capture', self.roots)
    def test_restart_between_checks_rejected(self):
        before = m.validate_inspection(self.info, 'capture', self.roots)
        self.info['State']['StartedAt'] = 'another-start'
        after = m.validate_inspection(self.info, 'capture', self.roots)
        with self.assertRaises(ValueError): m.verify_same_guard(before, after)

if __name__ == '__main__': unittest.main()
