"""Adversarial binding and cardinality checks; no application executions."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import realworld_legacy_jobs_v8 as p


class LegacyJobTests(unittest.TestCase):
    def setUp(self):
        self.registry = p.selection()
        self.plan = p.plan_for(self.registry)

    def test_source_specs_and_unknown_policies_preserved(self):
        source = {c['candidate_id']: c for c in p.read(ROOT / p.SOURCE)['cases']}
        for spec in self.registry['cases']:
            self.assertEqual(spec, source[spec['candidate_id']])
        for spec in self.registry['cases'][2:5]:
            self.assertEqual(spec['expectation']['outcome'], 'unknown')

    def test_five_pairs_two_references_two_singletons(self):
        jobs = self.plan['jobs']
        self.assertEqual(len(jobs), 9)
        self.assertEqual(sum(len(j['branches']) for j in jobs), 16)
        self.assertEqual([j['candidate_id'] for j in jobs[-2:]],
                         ['comment-native-control', 'profile-native-control'])
        for job in jobs[-2:]:
            self.assertEqual(job['entry_kind'], 'singleton')
            self.assertIsNone(job['reference_control'])
            self.assertEqual([b['continuation'] for b in job['branches']], ['ui'])

    def test_fabricated_singleton_api_branch_rejected(self):
        job = deepcopy(self.plan['jobs'][-1])
        job['branches'].append({'case_id': 'profile-native-control-api-r1',
                                'continuation': 'api', 'fresh_reset_required': True})
        with self.assertRaises(ValueError): p.validate_job(job, self.registry)
        original = self.plan['jobs'][-1]
        with self.assertRaises(ValueError):
            p.extract(original, {'api': ({}, {}), 'ui': ({}, {})},
                      self.registry['cases'][-1], {}, 'x', True, {})

    def test_changed_payload_policy_or_route_rejected(self):
        for key, value in [('prefix_payload', {'title': 'repaired'}),
                           ('expectation', {'outcome': 'accept'}),
                           ('continuations', ['ui'])]:
            changed = deepcopy(self.registry); changed['cases'][2][key] = value
            with self.assertRaises(ValueError): p.plan_for(changed)

    def test_reorder_repeat_and_reference_substitution_rejected(self):
        for mutate in (lambda j: j['branches'].reverse(),
                       lambda j: j.update(repetition=2),
                       lambda j: j.update(reference_control='profile-native-control')):
            job = deepcopy(self.plan['jobs'][2]); mutate(job)
            with self.assertRaises(ValueError): p.validate_job(job, self.registry)

    def test_missing_singleton_evidence_remains_unpaired_and_incomplete(self):
        job = self.plan['jobs'][-1]; spec = p.validate_job(job, self.registry)
        result = p.extract(job, {'ui': ({}, {'backend_exit_confirmed': True})},
                           spec, {}, 'x', True, {'synthetic': 'a' * 64})
        self.assertEqual(result['branch']['kind'], 'missing_evidence')
        self.assertIsNone(result['channel_discrepancy'])
        self.assertFalse(result['paired_comparison_eligible'])
        self.assertNotIn('terminal', result)

    def test_cleanup_failure_takes_precedence_for_singletons(self):
        job = self.plan['jobs'][-2]; spec = p.validate_job(job, self.registry)
        result = p.extract(job, {'ui': ({}, {})}, spec, {}, 'x', False, {})
        self.assertEqual(result['branch']['kind'], 'cleanup_unconfirmed')
        self.assertIsNone(result['channel_discrepancy'])

    def test_missing_pair_branch_cannot_become_singleton(self):
        job = self.plan['jobs'][2]; spec = p.validate_job(job, self.registry)
        with self.assertRaises(ValueError):
            p.extract(job, {'ui': ({}, {})}, spec, {}, 'x', True, {})

    def test_all_pair_references_match_workflow_and_producer(self):
        by = {c['candidate_id']: c for c in self.registry['cases']}
        for job in self.plan['jobs'][:-2]:
            spec = by[job['candidate_id']]; ref = by[job['reference_control']]
            self.assertEqual(spec['workflow'], ref['workflow'])
            self.assertEqual(spec['prefix_interface'], ref['prefix_interface'])
            self.assertEqual(ref['expectation']['outcome'], 'accept')

    def test_no_primary_or_repeat_authority(self):
        self.assertFalse(self.plan['primary_freeze_complete'])
        self.assertFalse(self.plan['campaign_dispatch_qualified'])
        self.assertFalse(self.plan['automatic_repeats'])


if __name__ == '__main__': unittest.main()
