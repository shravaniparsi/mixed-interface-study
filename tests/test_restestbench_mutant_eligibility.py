"""A test failure cannot receive credit without the complete execution chain."""
import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/'scripts/extension/run_restestbench_mutant_runtime_v1.py'
spec=importlib.util.spec_from_file_location('mutant_runtime',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class MutantEligibilityTests(unittest.TestCase):
    def test_each_missing_execution_gate_rejects_credit(self):
        row={'mutant_index':0,'control_passed':True,'mutation_applied':True,'bytes_changed':True,'execution_setup_qualified':True,'test_executed':True,'after_sha256':'a'*64,'container_source_sha256':'a'*64,'outcome':'execution_qualified_test_failure'}
        self.assertTrue(m.eligible_detection(row))
        for key in ['control_passed','mutation_applied','bytes_changed','execution_setup_qualified','test_executed']:
            with self.subTest(key=key):self.assertFalse(m.eligible_detection({**row,key:False}))
        self.assertFalse(m.eligible_detection({**row,'mutant_index':None}))
        self.assertFalse(m.eligible_detection({**row,'container_source_sha256':'b'*64}))
        self.assertFalse(m.eligible_detection({**row,'after_sha256':None,'container_source_sha256':None}))
        for outcome in ['timeout','test_error','survived','mutation_install_failure','reset_or_readiness_failure']:
            self.assertFalse(m.eligible_detection({**row,'outcome':outcome}))
    def test_junit_and_process_must_agree(self):
        failure={'tests':1,'errors':0,'failures':1,'skipped':0}
        self.assertEqual(m.classify(1,False,failure),'execution_qualified_test_failure')
        self.assertEqual(m.classify(0,False,failure),'execution_error')
        self.assertEqual(m.classify(1,True,failure),'timeout')
        self.assertEqual(m.classify(1,False,{**failure,'errors':1}),'test_error')
        self.assertEqual(m.classify(1,False,{**failure,'skipped':1}),'skipped_unqualified')
        self.assertEqual(m.classify(0,False,None),'missing_test_report')
if __name__=='__main__':unittest.main()
