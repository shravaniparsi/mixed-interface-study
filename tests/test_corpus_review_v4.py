"""Generated reconciliation preserves catalog identity and observed path limits."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from prepare_corpus_review_v4 import collect
from realworld_terminal_campaign import read
from mixed_interface.coverage_review_v4 import reconcile

class GeneratedReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous=read(ROOT/'manifests/retained-corpus-review-v3.json')['review'];cls.attempts=collect()

    def test_counts_scope_and_unrelated_rows_preserved(self):
        before=deepcopy(self.previous);r=reconcile(self.previous,self.attempts)
        self.assertEqual(before,self.previous)
        for key,value in {'pair_entries':73,'singletons':2,'logical_branches':148,
                          'entries_with_recorded_engineering_evidence':55,'primary_dispatch_ready':0,
                          'generated_entries_with_observed_attempt':9,'generated_observed_attempts':10,
                          'generated_entries_with_both_continuations_reached':5}.items():self.assertEqual(r['counts'][key],value,key)
        self.assertEqual(r['remaining_execution_requirement_counts']['generated_primary_campaign_binding'],9)
        for old,new in zip(self.previous['rows'],r['rows']):
            if old['path_family']!='realworld_generated':self.assertEqual(old,new)
            else:
                self.assertEqual(old['open_binding_gaps'],new['open_binding_gaps'])
                self.assertFalse(new['primary_dispatch_ready'])
        self.assertFalse(r['execution_authorized']);self.assertFalse(r['primary_freeze_complete'])

    def test_halt_policy_rejections_and_reference_attempts_preserved(self):
        rows=[r for r in reconcile(self.previous,self.attempts)['rows'] if r['path_family']=='realworld_generated']
        index={r['inventory_entry']['mutation']['transformation_id']:r for r in rows if r['inventory_entry']['mutation']}
        for name in ('article-body-empty','article-body-null','article-body-omitted'):
            row=index[name];self.assertIn('generated_assigned_continuation_not_exercised',row['retained_outcome_limits'])
            self.assertEqual(row['observed_generated_attempts'][0]['terminal_kind'],'matched_rejection')
        row=index['article-title-151'];self.assertIn('generated_semantic_evidence_incomplete',row['retained_outcome_limits'])
        self.assertIn('generated_requirement_policy_unresolved',row['retained_outcome_limits'])
        self.assertEqual(row['observed_generated_attempts'][0]['campaign_status'],'halted_terminal_outcome')
        refs=[r for r in rows if r['inventory_entry']['intervention']=='route_only']
        self.assertEqual(sorted(len(r['observed_generated_attempts']) for r in refs),[1,2])

    def test_source_route_reference_scope_and_inventory_changes_rejected(self):
        for mode in ('source','route','reference','scope','duplicate','missing','channel','pair'):
            with self.subTest(mode=mode):
                a=deepcopy(self.attempts)
                if mode=='source':a[0]['specs']['api']['case_id']='changed'
                elif mode=='route':a[0]['job']['branches'][0]['fresh_reset_required']=False
                elif mode=='reference':a[0]['job']['reference_pair_id']='foreign'
                elif mode=='scope':a[0]['new_primary_samples']=1
                elif mode=='duplicate':a.append(deepcopy(a[0]))
                elif mode=='missing':a.pop()
                elif mode=='channel':a[0]['branch_observations'].pop('api')
                else:a[0]['job']['pair']['producer_interface']='changed'
                with self.assertRaises(ValueError):reconcile(self.previous,a)

    def test_prior_primary_promotion_rejected(self):
        p=deepcopy(self.previous);p['rows'][0]['primary_dispatch_ready']=True
        with self.assertRaises(ValueError):reconcile(p,self.attempts)
