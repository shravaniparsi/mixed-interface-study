"""Exposed representation controls and synthetic reference-repeat counterexamples."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import realworld_expanded_campaign as bridge
from mixed_interface.campaign_v2 import drive
from mixed_interface.repetition import job as make_job


class ExpandedRealWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive=ROOT/'results/realworld-paired-controls-ci-20261107'
        cls.registry=bridge.read(cls.archive/'registered-candidates.json')
        cls.summary=bridge.read(cls.archive/'summary.json')
        cls.fixture=bridge.read(cls.archive/'fixture-references.json')
        cls.plan=bridge.plan_for(cls.registry)

    def extract(self,job,mismatch=False,cleanup=True):
        spec=deepcopy(bridge.validate_job(job,self.registry))
        branches={b['continuation']:(bridge.read(self.archive/b['evidence']),deepcopy(b))
                  for b in self.summary['branches'] if b['candidate_id']==job['pair_id']}
        if mismatch:
            spec['expectation']['outcome']='reject'
            for raw,run in branches.values():raw['expectation']=deepcopy(spec['expectation'])
        return bridge.pair_result(job,branches,spec,self.fixture,self.summary['fixture_sha256'],cleanup,{'fixture':'a'*64})['terminal']

    def test_all_seven_archived_pairs_are_clean(self):
        self.assertEqual(len(self.plan['schedule']['initial_jobs']),7)
        for job in self.plan['schedule']['initial_jobs']:
            with self.subTest(pair=job['pair_id']):self.assertEqual(self.extract(job)['kind'],'clean_observation')

    def test_variations_have_prespecified_baseline_references(self):
        for p in self.plan['schedule']['pairs']:
            if p['pair_id'] in bridge.VARIATIONS:
                self.assertEqual(p['reference_control'],bridge.VARIATIONS[p['pair_id']][0])
                self.assertEqual(p['intervention'],'payload_mutation')
            else:self.assertEqual(p['reference_control'],p['pair_id'])

    def test_changed_payload_rejected(self):
        registry=deepcopy(self.registry);registry['cases'][5]['prefix_payload']={'bio':'unregistered'}
        with self.assertRaises(ValueError):bridge.plan_for(registry)

    def test_registry_reordering_rejected(self):
        registry=deepcopy(self.registry);registry['cases'].reverse()
        with self.assertRaises(ValueError):bridge.plan_for(registry)

    def test_removed_reference_rejected(self):
        registry=deepcopy(self.registry);registry['cases']=[c for c in registry['cases'] if c['candidate_id']!='profile-bio-valid']
        with self.assertRaises(ValueError):bridge.plan_for(registry)

    def test_variation_cannot_be_its_own_reference(self):
        p=self.plan['schedule']['pairs'][5]
        bad=make_job(p,'control-005-r2','reference_control',p['pair_id'],2)
        with self.assertRaises(ValueError):bridge.validate_job(bad,self.registry)

    def test_wrong_workflow_reference_rejected(self):
        p=self.plan['schedule']['pairs'][0]
        bad=make_job(p,'control-005-r2','reference_control','profile-bio-null',2)
        with self.assertRaises(ValueError):bridge.validate_job(bad,self.registry)

    def test_reference_identity_and_target_are_separate(self):
        p=self.plan['schedule']['pairs'][2]
        good=make_job(p,'control-005-r2','reference_control','profile-bio-null',2)
        self.assertEqual(bridge.validate_job(good,self.registry)['candidate_id'],'profile-bio-valid')

    def test_stable_fixture_mismatch_requires_three_clean_reference_attempts(self):
        calls=[]
        def execute(job):
            calls.append(job)
            return self.extract(job,mismatch=job['pair_id']=='profile-bio-null')
        state=drive(self.plan,execute,lambda _:None)
        self.assertEqual(len(calls),11)
        self.assertEqual([j['pair_id'] for j in calls[7:]],['profile-bio-null','profile-bio-valid']*2)
        row=state['repeat_summary']['pairs'][0]
        self.assertEqual(row['status'],'stable_observations')
        self.assertEqual(row['candidate_attempts_observed'],3)
        self.assertEqual(row['control_attempts_observed'],3)
        self.assertFalse(row['defect_adjudicated'])

    def test_changed_repeat_remains_variable(self):
        def execute(job):
            return self.extract(job,mismatch=job['pair_id']=='profile-bio-null' and job['repetition']!=2)
        state=drive(self.plan,execute,lambda _:None)
        self.assertEqual(state['repeat_summary']['pairs'][0]['status'],'variable_observations')

    def test_failed_reference_cannot_support_stability(self):
        def execute(job):
            return self.extract(job,mismatch=job['pair_id']=='profile-bio-null' or job['role']=='reference_control')
        state=drive(self.plan,execute,lambda _:None)
        self.assertEqual(state['repeat_summary']['pairs'][0]['status'],'unresolved_control_failure')

    def test_cleanup_failure_halts_reference_sequence(self):
        calls=[]
        def execute(job):
            calls.append(job)
            return self.extract(job,mismatch=job['pair_id']=='profile-bio-null',cleanup=job['role']!='reference_control')
        state=drive(self.plan,execute,lambda _:None)
        self.assertEqual(len(calls),9)
        self.assertEqual(state['status'],'halted_terminal_outcome')
        self.assertNotIn('repeat_summary',state)
