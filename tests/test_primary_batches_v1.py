"""Registered independent-unit scheduling, halt scope and follow-up eligibility."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from primary_catalog_v1 import templates
from mixed_interface.primary_batches_v1 import plan,drive,followups
from mixed_interface.terminal_outcomes import terminal

class PrimaryBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.plan=plan(templates())
    def observation(self,job,kind='clean_observation'):
        base={'attempt_id':job['attempt_id'],'entry_kind':job['entry_kind']}
        if job['entry_kind']=='singleton':return {**base,'paired_comparison_eligible':False}
        incomplete=kind=='missing_evidence';mismatch=kind=='completed_mismatch'
        o={'job_id':job['attempt_id'],'execution':'incomplete' if incomplete else 'complete','prefix':'accepted',
           'channel_discrepancy':None if incomplete else mismatch,'check_failure':None if incomplete else mismatch,
           'cleanup_confirmed':True,'observation_signature':{'synthetic_scheduler_fixture':True}}
        return {**base,'terminal':terminal(o,kind,{'synthetic':'a'*64})}
    def initial(self,flag=None,kind='completed_mismatch'):
        return {u['batch_id']:drive(u,lambda j:self.observation(j,kind if u['batch_id']==flag and j['role']=='candidate' else 'clean_observation'),lambda _:None) for u in self.plan['initial_batches']}
    def test_full_inventory_and_distinct_attempts(self):
        units=self.plan['initial_batches'];self.assertEqual(len(units),75)
        ids=[j['attempt_id'] for u in units for j in u['jobs']];self.assertEqual(len(ids),137);self.assertEqual(len(set(ids)),137)
        self.assertEqual(len(followups(self.plan,self.initial(),2)['batches']),0)
    def test_flag_gets_two_repetitions_only_after_clean_references(self):
        u=next(u for u in self.plan['initial_batches'] if len(u['jobs'])==2)
        initial=self.initial(u['batch_id']);second=followups(self.plan,initial,2)['batches'];self.assertEqual(len(second),1)
        previous={u['batch_id']:drive(u,lambda j:self.observation(j),lambda _:None) for u in second}
        self.assertEqual(len(followups(self.plan,initial,3,previous)['batches']),1)
        previous[second[0]['batch_id']]=drive(second[0],lambda j:self.observation(j,'missing_evidence'),lambda _:None)
        self.assertEqual(followups(self.plan,initial,3,previous)['batches'],[])
    def test_halt_keeps_reference_unstarted_and_does_not_rewrite_other_units(self):
        u=next(u for u in self.plan['initial_batches'] if len(u['jobs'])==2);initial=self.initial(u['batch_id'],'missing_evidence')
        self.assertEqual(initial[u['batch_id']]['status'],'halted_terminal_outcome');self.assertEqual(len(initial[u['batch_id']]['started']),1)
        self.assertEqual(len(initial),75);self.assertEqual(followups(self.plan,initial,2)['batches'],[])
    def test_missing_foreign_or_replaced_batch_rejected(self):
        initial=self.initial();initial.pop(next(iter(initial)))
        with self.assertRaises(ValueError):followups(self.plan,initial,2)
        initial=self.initial();r=next(iter(initial.values()));r['observations'][0]['attempt_id']='foreign'
        with self.assertRaises(ValueError):followups(self.plan,initial,2)
    def test_control_failure_blocks_repeat_and_singleton_never_becomes_pair(self):
        u=next(u for u in self.plan['initial_batches'] if len(u['jobs'])==2);initial=self.initial(u['batch_id'])
        initial[u['batch_id']]=drive(u,lambda j:self.observation(j,'completed_mismatch'),lambda _:None)
        f=followups(self.plan,initial,2);self.assertEqual(f['batches'],[]);self.assertEqual(len(f['blocked']),1)
        singleton=next(u for u in self.plan['initial_batches'] if u['jobs'][0]['entry_kind']=='singleton')
        self.assertEqual(len(singleton['jobs']),1)
