"""Common preflight preserves exact runtime selection, identity and repetition policy."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from prepare_common_bindings_v1 import collect
from petclinic_timed_jobs_v4 import read,sha
from mixed_interface.common_bindings_v1 import registry,preflight,bind_job
from mixed_interface.campaign_v2 import followups
from mixed_interface.terminal_outcomes import terminal

class CommonBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review=read(ROOT/'manifests/retained-corpus-review-v5.json')['review'];cls.records,cls.profiles=collect()
        cls.value=registry(cls.review,cls.records,cls.profiles)
        cls.ids=[b['pair_id'] for b in cls.value['bindings']]
        cls.live={p:sha(ROOT/p) for profile in cls.profiles.values() for p in profile['source_sha256']}
        cls.checked=preflight(cls.value,cls.ids,cls.live)

    def test_fifteen_exact_bindings_and_full_corpus_accounting(self):
        self.assertEqual(self.value['counts'],{'catalog_entries':75,'bound_pairs':15,'unbound_entries':60,'singletons_excluded':2})
        before=deepcopy(self.value)
        for job in self.checked['campaign']['schedule']['initial_jobs']:
            bound=bind_job(self.value,self.checked,job)
            self.assertEqual(bound['campaign_job'],job);self.assertTrue(bound['requires_fresh_execution'])
            self.assertFalse(bound['historical_attempt_reuse_allowed']);self.assertFalse(bound['execution_authorized'])
        self.assertEqual(before,self.value);self.assertFalse(self.checked['primary_freeze_complete'])
        self.assertEqual(len({b['reference_pair_id'] for b in self.value['bindings']}),5)

    def test_changed_source_case_missing_cost_and_policy_are_rejected(self):
        for mode in ('case','cost','policy','duplicate'):
            records=deepcopy(self.records);profiles=deepcopy(self.profiles)
            if mode=='case':records[0]['cases']['api']['case_id']='foreign'
            elif mode=='cost':records[0]['observed_cost_s']['api']=None
            elif mode=='policy':profiles[records[0]['profile']]['terminal_policy_sha256']='0'*64
            else:records.append(deepcopy(records[0]))
            with self.assertRaises(ValueError):registry(self.review,records,profiles)
        altered=dict(self.live);altered[next(iter(altered))]='0'*64
        with self.assertRaises(ValueError):preflight(self.value,self.ids,altered)

    def test_unbound_singleton_missing_reference_and_reordered_selection_rejected(self):
        missing_ref=self.ids[1:]
        singleton=next(r['pair_id'] for r in self.value['unbound_entries'] if r['entry_kind']=='singleton')
        reordered=self.ids[:];reordered[0],reordered[1]=reordered[1],reordered[0]
        for ids in ([singleton],self.ids+[self.ids[0]],missing_ref,reordered,[self.value['unbound_entries'][0]['pair_id']]):
            with self.assertRaises(ValueError):preflight(self.value,ids,self.live)

    def synthetic_initial(self):
        values=[]
        for i,j in enumerate(self.checked['campaign']['schedule']['initial_jobs']):
            mismatch=i==1
            outcome={'job_id':j['job_id'],'execution':'complete','prefix':'accepted','channel_discrepancy':mismatch,'check_failure':mismatch,
                     'cleanup_confirmed':True,'observation_signature':{'synthetic_policy_test':True}}
            values.append(terminal(outcome,'completed_mismatch' if mismatch else 'clean_observation',{'synthetic':'a'*64}))
        return values

    def test_registered_repeat_and_reference_jobs_bind_to_fresh_namespaces(self):
        initial=self.synthetic_initial();f=followups(self.checked['campaign'],initial)
        self.assertEqual(len(f['jobs']),4)
        namespaces=[]
        for job in f['jobs']:
            b=bind_job(self.value,self.checked,job,initial);namespaces.append(b['attempt_namespace'])
            self.assertEqual(b['campaign_job']['repetition'],job['repetition'])
            self.assertTrue(b['requires_fresh_execution']);self.assertFalse(b['execution_authorized'])
        self.assertEqual(len(set(namespaces)),4)
        with self.assertRaises(ValueError):bind_job(self.value,self.checked,f['jobs'][0])
        forged=deepcopy(f['jobs'][0]);forged['role']='initial'
        with self.assertRaises(ValueError):bind_job(self.value,self.checked,forged,initial)
        halted=deepcopy(initial);halted[0]=terminal({**halted[0]['outcome'],'execution':'incomplete','channel_discrepancy':None,'check_failure':None},'missing_evidence',{'synthetic':'a'*64})
        with self.assertRaises(ValueError):bind_job(self.value,self.checked,f['jobs'][0],halted)

    def test_job_and_scope_tampering_rejected(self):
        job=deepcopy(self.checked['campaign']['schedule']['initial_jobs'][0]);job['branches'][0]['fresh_reset_required']=False
        with self.assertRaises(ValueError):bind_job(self.value,self.checked,job)
        checked=deepcopy(self.checked);checked['execution_authorized']=True
        with self.assertRaises(ValueError):bind_job(self.value,checked,self.checked['campaign']['schedule']['initial_jobs'][0])
