"""Repeated observations remain separate from independent defect adjudication."""
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import test_primary_batches_v1 as fixtures
from mixed_interface.primary_batches_v1 import followups,drive
from summarize_primary_units_v1 import summarize

class SummaryTests(unittest.TestCase):
    def test_complete_stable_repeats_are_not_confirmed_defects(self):
        fixtures.PrimaryBatchTests.setUpClass();f=fixtures.PrimaryBatchTests();p=f.plan
        unit=next(u for u in p['initial_batches'] if len(u['jobs'])==2);initial=f.initial(unit['batch_id'])
        def execute(j):return f.observation(j,'completed_mismatch' if j['role']=='candidate' else 'clean_observation')
        second={u['batch_id']:drive(u,execute,lambda _:None) for u in followups(p,initial,2)['batches']}
        third={u['batch_id']:drive(u,execute,lambda _:None) for u in followups(p,initial,3,second)['batches']}
        result=summarize({'plan':p},initial,second,third);row=next(r for r in result['rows'] if r['pair_id']==unit['target_pair_id'])
        self.assertEqual(row['repetition_status'],'stable_observations');self.assertEqual(row['candidate_attempts_observed'],3)
        self.assertFalse(row['independent_defect_adjudicated']);self.assertIsNone(result['defects_confirmed'])
        self.assertEqual(result['counts']['pairs'],73);self.assertEqual(result['counts']['singletons'],2)
    def test_missing_repetition_remains_incomplete(self):
        fixtures.PrimaryBatchTests.setUpClass();f=fixtures.PrimaryBatchTests();p=f.plan
        unit=next(u for u in p['initial_batches'] if len(u['jobs'])==2);initial=f.initial(unit['batch_id'])
        row=next(r for r in summarize({'plan':p},initial)['rows'] if r['pair_id']==unit['target_pair_id'])
        self.assertEqual(row['repetition_status'],'incomplete_or_blocked');self.assertEqual(row['candidate_attempts_observed'],1)
