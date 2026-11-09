"""Readiness reconciliation preserves scope, evidence gaps and accounting units."""
from copy import deepcopy
from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'src'))
from prepare_corpus_review_v3 import collect
from realworld_terminal_campaign import read
from mixed_interface.coverage_review_v3 import reconcile


class CorpusReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous=read(ROOT/'manifests/retained-corpus-review-v2.json')['review']
        cls.attempts,cls.diagnostics=collect()

    def result(self,previous=None,attempts=None,diagnostics=None):
        return reconcile(self.previous if previous is None else previous,
                         self.attempts if attempts is None else attempts,
                         self.diagnostics if diagnostics is None else diagnostics)

    def test_exact_inventory_and_no_primary_promotion(self):
        before=deepcopy(self.previous);result=self.result();self.assertEqual(self.previous,before)
        self.assertEqual(result['counts']['entries_with_recorded_engineering_evidence'],49)
        self.assertEqual(result['counts']['pair_entries'],73)
        self.assertEqual(result['counts']['singletons'],2)
        self.assertEqual(result['counts']['logical_branches'],148)
        self.assertEqual(result['counts']['primary_dispatch_ready'],0)
        self.assertEqual(result['remaining_execution_requirement_counts']['legacy_primary_campaign_binding'],7)
        self.assertEqual(result['remaining_execution_requirement_counts']['identity_primary_campaign_binding'],3)

    def test_halt_and_retrospective_classification_are_not_overwritten(self):
        rows={r['inventory_entry'].get('candidate_id'):r for r in self.result()['rows'] if r['inventory_entry']['catalog']=='realworld_development'}
        title=rows['article-title-151']
        self.assertEqual(title['observed_legacy_attempts'][0]['terminal_kind'],'missing_evidence')
        self.assertEqual(len(title['isolated_database_observations']),1)
        self.assertIn('legacy_requirement_policy_unresolved',title['retained_outcome_limits'])
        full=rows['article-update-duplicate-full']['observed_legacy_attempts'][0]
        self.assertEqual(full['terminal_kind'],'incomparable_observation')
        self.assertEqual(full['retrospective_comparison']['derived_kind'],'clean_observation')
        for cid in ('article-title-whitespace','article-update-duplicate-partial'):
            self.assertEqual(rows[cid]['observed_legacy_attempts'][0]['retrospective_comparison']['derived_kind'],'incomparable_observation')
        self.assertEqual(len(rows['article-valid']['observed_legacy_attempts']),2)
        for cid in ('comment-native-control','profile-native-control'):
            self.assertEqual(rows[cid]['entry_kind'],'singleton')
            self.assertEqual(rows[cid]['observed_legacy_attempts'][0]['channels'],['ui'])

    def test_source_cardinality_and_scope_tampering_rejected(self):
        for mode in ('source','channel','scope','duplicate','lost'):
            with self.subTest(mode=mode):
                attempts=deepcopy(self.attempts)
                if mode=='source':attempts[0]['spec']['prefix_payload']['title']='changed'
                elif mode=='channel':attempts[0]['channels']=['ui']
                elif mode=='scope':attempts[0]['new_primary_samples']=1
                elif mode=='duplicate':attempts.append(deepcopy(attempts[0]))
                else:attempts.pop()
                with self.assertRaises(ValueError):self.result(attempts=attempts)

    def test_database_policy_change_or_promotion_rejected(self):
        for field,value in [('requirement_policy',{}),('candidate_id','foreign')]:
            diagnostics=deepcopy(self.diagnostics);diagnostics[0]['measurement'][field]=value
            with self.assertRaises(ValueError):self.result(diagnostics=diagnostics)
        diagnostics=deepcopy(self.diagnostics);diagnostics[0]['primary_freeze_complete']=True
        with self.assertRaises(ValueError):self.result(diagnostics=diagnostics)

    def test_unrelated_generated_and_quartz_rows_unchanged(self):
        new=self.result()['rows']
        for old,row in zip(self.previous['rows'],new):
            if old['path_family'] in ('realworld_generated','quartz_terminal'):
                for key in old:self.assertEqual(row[key],old[key])
