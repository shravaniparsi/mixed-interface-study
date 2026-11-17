import copy
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from mixed_interface.shared_reconstruction import digest,package_shared_evidence

class SharedEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.obs={'target':'submit_decision','point':'api_request','context':
                  dict(revision='r1',operation='register',actor='anonymous',lifecycle='create'),
                  'document':{'password':'abcd'}}
    def fact(self,key='confirmation.value',status='known',value='abcd'):
        f=dict(id=key,status=status,origin='provided_context',evidence='fixture:context',observation_sha256=digest(self.obs))
        if status=='known':f['value']=value
        return f
    def bundle(self,facts,obs=None):
        return package_shared_evidence(obs or self.obs,['confirmation.value'],facts)
    def test_request_alone_does_not_copy_password(self):
        result=self.bundle([])
        self.assertFalse(result['evidence_complete_for_declared_requirements'])
        self.assertEqual(result['resolved'],{})
        self.assertEqual(result['unresolved'][0]['reason'],'not_supplied')
    def test_null_empty_and_absent_remain_distinct(self):
        values=[self.bundle([self.fact(value=v)]) for v in [None,'',False]]
        absent=self.bundle([self.fact(status='absent')])
        self.assertEqual(len({v['shared_input_sha256'] for v in values+[absent]}),4)
        self.assertNotIn('value',absent['resolved']['confirmation.value'])
        self.assertIsNone(values[0]['resolved']['confirmation.value']['value'])
    def test_unknown_is_not_absent_or_pass(self):
        result=self.bundle([self.fact(status='unknown')])
        self.assertFalse(result['evidence_complete_for_declared_requirements'])
        self.assertEqual(result['unresolved'][0]['reason'],'explicitly_unknown')
    def test_binding_includes_document_scope_and_target(self):
        for key in ['document','target','point','context']:
            changed=copy.deepcopy(self.obs)
            changed[key]={'document':{'password':'different'},'target':'form_validation',
                          'point':'frontend_model','context':dict(self.obs['context'],actor='admin')}[key]
            result=self.bundle([self.fact()],changed)
            self.assertEqual(result['unresolved'][0]['reason'],'stale_or_different_observation')
    def test_provenance_required_but_not_certified(self):
        f=self.fact();f['evidence']=''
        self.assertFalse(self.bundle([f])['evidence_complete_for_declared_requirements'])
        good=self.bundle([self.fact()]);self.assertTrue(good['evidence_complete_for_declared_requirements'])
        self.assertFalse(good['provenance_truth_verified'])
        self.assertFalse(good['requirement_completeness_verified'])
    def test_duplicate_facts_and_requirements_rejected(self):
        with self.assertRaises(ValueError):self.bundle([self.fact(),self.fact()])
        with self.assertRaises(ValueError):package_shared_evidence(self.obs,['x','x'],[])
    def test_unrelated_fact_does_not_fill_requirement(self):
        result=self.bundle([self.fact(key='password.value')])
        self.assertEqual(result['resolved'],{})
        self.assertEqual(result['unused_fact_ids'],['password.value'])
    def test_same_evidence_same_hash_different_context_different_hash(self):
        a=self.bundle([self.fact()]);b=self.bundle([self.fact()]);c=self.bundle([self.fact(value='wxyz')])
        self.assertEqual(a['shared_input_sha256'],b['shared_input_sha256'])
        self.assertNotEqual(a['shared_input_sha256'],c['shared_input_sha256'])
    def test_output_does_not_alias_inputs(self):
        f=self.fact();result=self.bundle([f]);f['value']='modified';self.obs['document']['password']='changed'
        self.assertEqual(result['resolved']['confirmation.value']['value'],'abcd')
        self.assertEqual(result['observation']['document']['password'],'abcd')
    def test_malformed_and_nonfinite_states_rejected(self):
        with self.assertRaises(ValueError):self.bundle([self.fact(value=math.nan)])
        with self.assertRaises(ValueError):self.bundle([self.fact(value=('x',))])
        with self.assertRaises(ValueError):self.bundle([self.fact(value={1:'x'})])
        f=self.fact();f['status']='absent'
        with self.assertRaises(ValueError):self.bundle([f])
        bad=copy.deepcopy(self.obs);bad['target']='arbitrary'
        with self.assertRaises(ValueError):self.bundle([],bad)

if __name__=='__main__':unittest.main()
