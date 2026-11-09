"""Fresh selection and stop-policy tests; no application launches."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import realworld_legacy_campaign_v9 as campaign
from realworld_legacy_jobs_v8 import plan_for as worker_plan
from validate_realworld_legacy_campaign_v9 import verify_accounting
from test_realworld_legacy_campaign_v8 import result


class FreshLegacyCampaignTests(unittest.TestCase):
    def setUp(self):
        self.registry=campaign.selection();self.plan=campaign.plan_for(self.registry)

    def test_exact_seven_jobs_twelve_branches_and_no_title_replay(self):
        jobs=self.plan['jobs']
        self.assertEqual(tuple(j['candidate_id'] for j in jobs),campaign.FRESH_IDS)
        self.assertEqual(len(jobs),7);self.assertEqual(sum(len(j['branches']) for j in jobs),12)
        self.assertFalse(self.plan['prior_attempt_resumed'])
        self.assertFalse(self.plan['primary_freeze_complete'])
        for j in jobs:self.assertIn(j,worker_plan(self.registry)['jobs'])

    def sweep(self,halt=None):
        observations={};checkpoints=[]
        def execute(job):
            value=result(job,'missing_evidence' if job['candidate_id']==halt else 'clean_observation')
            observations[job['job_id']]=value;return value
        report=campaign.drive(self.registry,execute,checkpoints.append)
        return report,observations

    def test_complete_accounting_reconstructs_fresh_attempt(self):
        report,observations=self.sweep()
        self.assertEqual(report['status'],'completed_bounded_diagnostic')
        self.assertEqual(verify_accounting(self.registry,report,observations),report)
        self.assertEqual(len(observations),7)

    def test_whitespace_halt_does_not_dispatch_remaining_cases(self):
        report,observations=self.sweep('article-title-whitespace')
        self.assertEqual(report['status'],'halted_terminal_outcome');self.assertEqual(len(observations),3)
        verify_accounting(self.registry,report,observations)

    def test_final_singleton_halt_is_not_completion(self):
        report,observations=self.sweep('profile-native-control')
        self.assertEqual(report['status'],'halted_terminal_outcome')
        self.assertEqual(len(observations),7)
        changed=deepcopy(report);changed['status']='completed_bounded_diagnostic'
        with self.assertRaises(ValueError):verify_accounting(self.registry,changed,observations)

    def test_previous_title_result_cannot_be_merged_into_fresh_attempt(self):
        report,observations=self.sweep()
        old=worker_plan(self.registry)['jobs'][2];observations[old['job_id']]=result(old)
        with self.assertRaises(ValueError):verify_accounting(self.registry,report,observations)

    def test_changed_payload_and_budget(self):
        changed=deepcopy(self.registry);changed['cases'][4]['prefix_payload']['title']='repaired'
        with self.assertRaises(ValueError):campaign.plan_for(changed)
        self.assertGreater(campaign.OUTER_TIMEOUT_S,7*(campaign.JOB_TIMEOUT_S+9)+120)
