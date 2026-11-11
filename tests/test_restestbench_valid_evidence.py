"""Synthetic verifier controls; these are not application observations."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('golden_verify',ROOT/'scripts/extension/verify_restestbench_valid_golden_v1.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class GoldenEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name)
        self.registration={'upstream_commit':'pin','services':{'todoapp':[1]},'sha256':{'scripts/extension/run_restestbench_valid_golden_v1.py':'instrument'}}
        self.hashes={'data/tests/todoapp/test_1.py':'testhash'}
        self.data={'service':'todoapp','upstream_commit':'pin','paid_model_calls':0,'mutations_installed':0,'expected_ids':[1],'unattempted_ids':[],'terminal':'completed','commands':[],'cases':[{'id':1,'test_executed':True,'test_sha256':'testhash','return_code':0,'timeout':False,'junit':{'tests':1,'failures':0,'errors':0,'skipped':0},'outcome':'passed'}]}
        for label in ['build','start','images','req-1-clean','req-1-restart','req-1-test']:
            self.data['commands'].append({'label':label,'return_code':0,'timeout':False,'elapsed_seconds':1,'log':label+'.log'});(self.folder/(label+'.log')).write_text('synthetic control')
        for label in ['initial-health','req-1-health']:(self.folder/(label+'.json')).write_text('[{"status":200}]')
        (self.folder/'study-head.txt').write_text(module.HEAD)
        (self.folder/'instrument-sha256.txt').write_text('instrument script.py')
        (self.folder/'input-sha256.json').write_text(json.dumps(self.hashes))
        (self.folder/'req-1.xml').write_text('<testsuites><testsuite tests="1" errors="0" failures="0" skipped="0"/></testsuites>')
    def check(self):
        (self.folder/'observations.json').write_text(json.dumps(self.data))
        return module.validate_observation(self.folder,self.registration,self.hashes)
    def test_complete_proof_accepts(self):self.assertTrue(self.check()['all_valid_tests_qualified'])
    def test_false_pass_rejected_by_raw_junit(self):
        (self.folder/'req-1.xml').write_text('<testsuites><testsuite tests="1" errors="0" failures="1" skipped="0"/></testsuites>')
        with self.assertRaises(AssertionError):self.check()
    def test_failed_reset_cannot_support_pass(self):
        self.data['commands'][3]['return_code']=1
        with self.assertRaises(AssertionError):self.check()
    def test_changed_test_source_rejected(self):
        (self.folder/'input-sha256.json').write_text(json.dumps({**self.hashes,'unexpected.py':'hash'}))
        with self.assertRaises(AssertionError):self.check()
    def test_partial_record_cannot_claim_complete(self):
        self.data['cases']=[];self.data['unattempted_ids']=[1]
        with self.assertRaises(AssertionError):self.check()

if __name__=='__main__':unittest.main()
