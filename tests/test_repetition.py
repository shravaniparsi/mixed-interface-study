from copy import deepcopy
import unittest
from mixed_interface.repetition import build_plan, digest, followups, summarize


def pair(name='control', intervention='route_only', producer='api'):
    return {'pair_id': name, 'workflow_id': 'fixture.workflow', 'producer_interface': producer,
            'case_ids': {'api': name+'-api', 'ui': name+'-ui'}, 'intervention': intervention, 'mutation': None if intervention == 'route_only' else {'kind': 'omit'}}


def outcome(job, failure=False):
    return {'job_id': job['job_id'], 'execution': 'complete', 'prefix': 'accepted',
            'channel_discrepancy': False, 'check_failure': failure, 'cleanup_confirmed': True,
            'observation_signature': {'observed': 'failed' if failure else 'passed'}}


class RepetitionTests(unittest.TestCase):
    def setUp(self):
        self.plan = build_plan([pair(), pair('candidate', 'payload_mutation')])
        self.initial = [outcome(j, i == 1) for i, j in enumerate(self.plan['initial_jobs'])]

    def repeats(self):
        return [outcome(j, j['role'] == 'candidate_repeat') for j in followups(self.plan, self.initial)['jobs']]

    def test_two_repeats_each_with_control_and_independent_branches(self):
        jobs = followups(self.plan, self.initial)['jobs']
        self.assertEqual([j['role'] for j in jobs], ['candidate_repeat', 'reference_control']*2)
        self.assertEqual(len({j['job_id'] for j in jobs}), 4)
        self.assertTrue(all(b['fresh_reset_required'] for j in jobs for b in j['branches']))
        self.assertEqual(sum(len(j['branches']) for j in jobs), 8)

    def test_clean_sweep_adds_no_repeats(self):
        self.assertEqual(followups(self.plan, [outcome(j) for j in self.plan['initial_jobs']])['jobs'], [])

    def test_partial_sweep_halts_without_resume(self):
        result = followups(self.plan, self.initial[:1])
        self.assertEqual(result['status'], 'halted_incomplete_sweep'); self.assertFalse(result['resume_allowed'])

    def test_unconfirmed_cleanup_halts(self):
        self.initial[-1]['cleanup_confirmed'] = False
        self.assertEqual(followups(self.plan, self.initial)['status'], 'halted_unconfirmed_cleanup')

    def test_missing_or_unknown_outcome_fields_rejected(self):
        for key in ('execution', 'check_failure', 'observation_signature'):
            values = deepcopy(self.initial); del values[1][key]
            with self.assertRaises(ValueError): followups(self.plan, values)
        values = deepcopy(self.initial); values[1]['unknown'] = False
        with self.assertRaises(ValueError): followups(self.plan, values)

    def test_duplicate_or_reordered_outcomes_rejected(self):
        for values in (self.initial[::-1], [self.initial[0], self.initial[0]]):
            with self.assertRaises(ValueError): followups(self.plan, values)

    def test_incomplete_execution_triggers_diagnostics(self):
        self.initial[1].update(execution='incomplete', prefix='unobserved', check_failure=None, channel_discrepancy=None, observation_signature=None)
        self.assertIn('unresolved_execution', followups(self.plan, self.initial)['triggers']['candidate'])

    def test_clean_rejection_does_not_invent_continuation_failure(self):
        self.initial[1] = outcome(self.plan['initial_jobs'][1]); self.initial[1]['prefix'] = 'rejected'
        self.assertEqual(followups(self.plan, self.initial)['jobs'], [])

    def test_same_workflow_different_producer_cannot_supply_control(self):
        with self.assertRaisesRegex(ValueError, 'Missing'): build_plan([pair(), pair('candidate', 'payload_mutation', 'ui')])

    def test_ambiguous_control_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Ambiguous'): build_plan([pair(), pair('other')])

    def test_rehashed_changed_schedule_still_rejected(self):
        self.plan['initial_jobs'][0]['branches'].reverse()
        self.plan['plan_sha256'] = digest({k:v for k,v in self.plan.items() if k != 'plan_sha256'})
        with self.assertRaisesRegex(ValueError, 'schedule'): followups(self.plan, self.initial)

    def test_stable_observations_do_not_adjudicate_defect(self):
        row = summarize(self.plan, self.initial, self.repeats())['pairs'][0]
        self.assertEqual(row['status'], 'stable_observations'); self.assertFalse(row['defect_adjudicated'])
        self.assertEqual(row['candidate_attempts_observed'], 3)

    def test_changed_repeat_retains_variability(self):
        repeated = self.repeats(); repeated[0]['observation_signature'] = {'observed': 'different'}
        row = summarize(self.plan, self.initial, repeated)['pairs'][0]
        self.assertEqual(row['status'], 'variable_observations'); self.assertTrue(row['variability_observed'])

    def test_failed_reference_control_blocks_interpretation(self):
        repeated = self.repeats(); repeated[1]['check_failure'] = True
        self.assertEqual(summarize(self.plan, self.initial, repeated)['pairs'][0]['status'], 'unresolved_control_failure')

    def test_missing_repeat_cannot_be_stable(self):
        self.assertEqual(summarize(self.plan, self.initial, self.repeats()[:2])['pairs'][0]['status'], 'incomplete_repeats')

    def test_incomplete_attempt_cannot_be_replaced_by_later_pass(self):
        repeated = self.repeats(); repeated[0].update(execution='incomplete', observation_signature=None)
        self.assertEqual(summarize(self.plan, self.initial, repeated)['pairs'][0]['status'], 'unresolved_execution')

    def test_observations_and_plan_not_mutated(self):
        before = deepcopy((self.plan, self.initial)); followups(self.plan, self.initial)
        self.assertEqual((self.plan, self.initial), before)

    def test_stable_mixed_prefixes_remain_unresolved(self):
        self.initial[1]['prefix'] = 'mixed'
        repeated = self.repeats()
        for i in (0, 2): repeated[i]['prefix'] = 'mixed'
        self.assertEqual(summarize(self.plan, self.initial, repeated)['pairs'][0]['status'], 'unresolved_execution')

    def test_truthy_strings_cannot_confirm_cleanup(self):
        self.initial[1]['cleanup_confirmed'] = 'false'
        with self.assertRaises(ValueError): followups(self.plan, self.initial)
