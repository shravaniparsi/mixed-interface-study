"""Prevent incomplete/errored golden runs receiving valid-service pass credit."""
import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/'scripts/extension/run_restestbench_valid_golden_v1.py'
spec=importlib.util.spec_from_file_location('golden_runner',p)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class GoldenClassificationTests(unittest.TestCase):
    def test_success_requires_real_unskipped_tests_and_successful_process(self):
        counts={'tests':1,'failures':0,'errors':0,'skipped':0}
        self.assertEqual(module.classify_test(0,False,counts),'passed')
        self.assertEqual(module.classify_test(1,False,counts),'execution_error')
        self.assertEqual(module.classify_test(-9,True,counts),'timeout')
        self.assertEqual(module.classify_test(0,False,None),'missing_test_report')
        for field,expected in [('failures','test_failed'),('errors','test_error'),('skipped','skipped_unqualified')]:
            self.assertEqual(module.classify_test(0,False,{**counts,field:1}),expected)
        self.assertEqual(module.classify_test(0,False,{**counts,'tests':0}),'no_tests')

if __name__=='__main__':unittest.main()
