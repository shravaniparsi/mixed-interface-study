from copy import deepcopy
import json
import subprocess
import sys
import unittest
from mixed_interface import campaign_v2 as campaign
from mixed_interface.terminal_outcomes import POLICY, decision, terminal, validate
from test_repetition import pair, outcome


def record(job, kind='clean_observation'):
    o = outcome(job, kind == 'completed_mismatch')
    if kind == 'matched_rejection': o['prefix'] = 'rejected'
    if kind in ('application_response_failure', 'incomparable_observation'):
        o.update(execution='incomplete', check_failure=None, channel_discrepancy=None)
    if kind == 'cleanup_unconfirmed': o['cleanup_confirmed'] = False
    return terminal(o, kind, {'fixture': 'a' * 64})


class TerminalCampaignTests(unittest.TestCase):
    def setUp(self):
        self.plan = campaign.build_plan([pair(), pair('candidate', 'payload_mutation')])
        self.events = []

    def run_kind(self, kind):
        return campaign.drive(self.plan, lambda j: record(j, kind if j['pair_id'] == 'candidate' else 'clean_observation'), self.events.append)

    def test_each_terminal_driver_planner_agree(self):
        for kind, (action, repeat, semantic) in POLICY.items():
            with self.subTest(kind=kind):
                state = self.run_kind(kind)
                self.assertEqual(len(state['dispatches']), 6 if repeat else 2)
                self.assertEqual(state['status'], 'halted_terminal_outcome' if action == 'halt' else 'completed_observations')
                schedule = campaign.followups(self.plan, state['initial'])
                self.assertEqual(len(schedule['jobs']), 4 if repeat else 0)
                self.assertEqual(decision(state['initial'][-1])['semantic_evidence_complete'], semantic)

    def test_response_failure_retained_never_promoted_to_stable(self):
        state = self.run_kind('application_response_failure')
        row = state['repeat_summary']['pairs'][0]
        self.assertEqual(row['status'], 'unresolved_execution')
        self.assertEqual(row['terminal_kinds'], ['application_response_failure'] * 3)
        self.assertFalse(row['defect_adjudicated'])

    def test_complete_mismatch_stable_but_not_defect(self):
        row = self.run_kind('completed_mismatch')['repeat_summary']['pairs'][0]
        self.assertEqual(row['status'], 'stable_observations')
        self.assertFalse(row['defect_adjudicated'])

    def test_followups_do_not_expand_recursively(self):
        def execute(j):
            return record(j, 'completed_mismatch' if j['pair_id'] == 'candidate' or j['role'] == 'reference_control' else 'clean_observation')
        state = campaign.drive(self.plan, execute, self.events.append)
        self.assertEqual(len(state['dispatches']), 6)
        self.assertEqual(state['repeat_summary']['pairs'][0]['status'], 'unresolved_control_failure')

    def test_halt_during_repeat_preserves_failed_attempt(self):
        def execute(j):
            return record(j, 'case_timeout' if j['role'] == 'candidate_repeat' else 'completed_mismatch' if j['pair_id'] == 'candidate' else 'clean_observation')
        state = campaign.drive(self.plan, execute, self.events.append)
        self.assertEqual(len(state['dispatches']), 3)
        self.assertEqual(state['repeated'][0]['kind'], 'case_timeout')
        self.assertNotIn('repeat_summary', state)

    def test_job_identity_rejected_before_recording(self):
        def execute(j):
            r = record(j); r['outcome']['job_id'] = 'foreign'; return r
        with self.assertRaisesRegex(ValueError, 'another job'):
            campaign.drive(self.plan, execute, self.events.append)
        self.assertEqual(self.events[-1]['initial'], [])
        self.assertEqual(self.events[-1]['dispatches'][0]['status'], 'started')

    def test_cleanup_cannot_be_hidden_by_success(self):
        r = record(self.plan['schedule']['initial_jobs'][0]); r['outcome']['cleanup_confirmed'] = False
        with self.assertRaisesRegex(ValueError, 'precedence'): validate(r)

    def test_policy_hash_and_schema_enforced(self):
        for key, value in [('policy_sha256', '0' * 64), ('schema_version', 1), ('kind', 'unknown')]:
            r = record(self.plan['schedule']['initial_jobs'][0]); r[key] = value
            with self.assertRaises(ValueError): validate(r)

    def test_invalid_evidence_references_rejected(self):
        for refs in ({}, {'trace': True}, {'trace': 'not-a-hash'}):
            r = record(self.plan['schedule']['initial_jobs'][0]); r['evidence'] = refs
            with self.assertRaises(ValueError): validate(r)

    def test_mismatch_cannot_be_hidden_as_policy(self):
        r = record(self.plan['schedule']['initial_jobs'][0], 'completed_mismatch'); r['kind'] = 'unresolved_policy'
        with self.assertRaisesRegex(ValueError, 'precedence'): validate(r)

    def test_reordered_initials_rejected(self):
        records = [record(j) for j in self.plan['schedule']['initial_jobs']]
        with self.assertRaises(ValueError): campaign.followups(self.plan, records[::-1])

    def test_partial_sweep_has_no_followups(self):
        r = record(self.plan['schedule']['initial_jobs'][0], 'completed_mismatch')
        result = campaign.followups(self.plan, [r])
        self.assertEqual(result['status'], 'halted_incomplete_sweep'); self.assertFalse(result['resume_allowed'])

    def test_rehashed_modified_plan_rejected(self):
        from mixed_interface.repetition import digest
        plan = deepcopy(self.plan); plan['schedule']['initial_jobs'][0]['branches'].reverse()
        plan['plan_sha256'] = digest({k: v for k, v in plan.items() if k != 'plan_sha256'})
        with self.assertRaises(ValueError): campaign.validate_plan(plan)

    def test_checkpoint_failure_prevents_dispatch(self):
        calls = []
        def checkpoint(state): raise OSError('fixture disk full')
        with self.assertRaises(OSError): campaign.drive(self.plan, calls.append, checkpoint)
        self.assertEqual(calls, [])

    def test_executor_interrupt_records_intent(self):
        def execute(job): raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt): campaign.drive(self.plan, execute, self.events.append)
        self.assertEqual(self.events[-1]['status'], 'halted_executor_error')
        self.assertEqual(len(self.events[-1]['dispatches']), 1)

    def test_bounded_subprocess_dispatch_preserves_nonzero_observation(self):
        """Engineering transport fixture, no application/network or boundary data."""
        calls = []
        def execute(job):
            self.assertEqual(self.events[-1]['dispatches'][-1]['status'], 'started')
            value = record(job, 'application_response_failure' if job['pair_id'] == 'candidate' else 'clean_observation')
            code = 7 if job['pair_id'] == 'candidate' else 0
            child = subprocess.run([sys.executable, '-c', 'import sys; print(sys.stdin.read()); sys.exit(int(sys.argv[1]))', str(code)],
                                   input=json.dumps(value), text=True, capture_output=True, timeout=5)
            calls.append((job['job_id'], child.returncode))
            # Classification follows retained evidence, not an automatic exception on nonzero exit.
            return json.loads(child.stdout)
        state = campaign.drive(self.plan, execute, self.events.append)
        self.assertEqual(len(calls), 6)
        self.assertEqual([c for _, c in calls], [0, 7, 7, 0, 7, 0])
        self.assertEqual(len(set(j for j, _ in calls)), 6)
        self.assertEqual(state['repeat_summary']['pairs'][0]['status'], 'unresolved_execution')


if __name__ == '__main__': unittest.main()
