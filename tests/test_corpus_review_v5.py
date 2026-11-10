"""Exact runtime qualification closes one gap and preserves history and scope."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from prepare_corpus_review_v5 import collect
from realworld_terminal_campaign import read
from mixed_interface.coverage_review_v5 import reconcile,GAP

class ReferenceReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous=read(ROOT/'manifests/retained-corpus-review-v4.json')['review'];cls.attempts=collect()

    def test_only_one_requirement_closes_and_history_is_preserved(self):
        old=deepcopy(self.previous);v=reconcile(self.previous,self.attempts);self.assertEqual(old,self.previous)
        self.assertNotIn(GAP,v['remaining_execution_requirement_counts'])
        self.assertEqual(v['remaining_execution_requirement_counts']['legacy_primary_campaign_binding'],7)
        self.assertEqual(v['counts']['entries_with_recorded_engineering_evidence'],55)
        self.assertEqual(v['counts']['primary_dispatch_ready'],0)
        changed=[]
        for a,b in zip(old['rows'],v['rows']):
            if a['remaining_execution_requirements']!=b['remaining_execution_requirements']:changed.append(b['inventory_entry']['candidate_id'])
            for key in ('observed_legacy_attempts','retained_outcome_limits','primary_dispatch_ready'):
                self.assertEqual(a[key],b[key])
            if 'observed_reference_runtime_attempts' not in b:self.assertEqual(a,b)
        self.assertEqual(changed,['article-update-duplicate-full'])
        self.assertFalse(v['execution_authorized']);self.assertFalse(v['primary_freeze_complete'])

    def test_altered_reference_proof_cannot_close_gap(self):
        for mode in ('gate','binding','kind','qualified'):
            a=deepcopy(self.attempts);full=next(x for x in a if x['job']['job_id']=='legacy-006');proof=full['reference_comparison']
            if mode=='gate':proof['derived_gates']['same_reset']=False
            elif mode=='binding':proof['local_bindings']['ui']=False
            elif mode=='kind':full['terminal_kind']='incomparable_observation'
            else:proof['reference_comparison_qualified']=False
            with self.assertRaises(ValueError):reconcile(self.previous,a)

    def test_source_cardinality_inventory_and_scope_tampering_rejected(self):
        for mode in ('source','channel','case','missing','duplicate','order','scope'):
            a=deepcopy(self.attempts)
            if mode=='source':a[0]['source_commit']='foreign'
            elif mode=='channel':a[0]['channels']=['api']
            elif mode=='case':a[0]['spec']['candidate_id']='foreign'
            elif mode=='missing':a.pop()
            elif mode=='duplicate':a.append(deepcopy(a[0]))
            elif mode=='order':a.reverse()
            else:a[0]['primary_freeze_complete']=True
            with self.assertRaises(ValueError):reconcile(self.previous,a)
