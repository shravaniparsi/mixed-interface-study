"""Public qualification preserves case semantics and isolates the host change."""
import sys,unittest
from copy import deepcopy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from quartz_public_qualification_preflight_v1 import ROOT,PREPARATION,read,sources,units

class PublicQualificationTests(unittest.TestCase):
    def test_only_host_cpu_and_attempt_identity_change(self):
        old=read(ROOT/'manifests/quartz-form-correction-preparation-v1.json')
        new=read(PREPARATION)
        expected=deepcopy(old['environment']);expected['logical_cpus']=4
        self.assertEqual(new['environment'],expected)
        expected=deepcopy(old['smoke_units'])
        for unit in expected:
            unit['batch_id']=unit['batch_id'].replace('qfix-','qpublic-')
            for job in unit['jobs']:job['attempt_id']=job['attempt_id'].replace('qfix-','qpublic-')
        self.assertEqual(units('smoke'),expected)
        sources(old);sources(new)

    def test_research_phases_cannot_run_via_qualification(self):
        for mode in ('initial','repeat2','repeat3','unknown'):
            with self.subTest(mode=mode),self.assertRaises(Exception):units(mode)

if __name__=='__main__':unittest.main()
