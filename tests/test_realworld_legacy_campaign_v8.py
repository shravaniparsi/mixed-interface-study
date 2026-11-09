"""Bounded orchestration and independent report reconstruction; no application launch."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import realworld_legacy_campaign_v8 as campaign
from mixed_interface.terminal_outcomes import terminal
from validate_realworld_legacy_campaign_v8 import verify_accounting


def result(job,kind='clean_observation'):
    evidence={'synthetic':'a'*64}
    if job['entry_kind']=='singleton':
        return {'entry_kind':'singleton','job_id':job['job_id'],
                'branch':{'kind':kind,'components':{'execution_evidence_complete':True}},
                'channel_discrepancy':None,'paired_comparison_eligible':False,
                'evidence_sha256':evidence,'primary_freeze_complete':False}
    outcome={'job_id':job['job_id'],'execution':'complete' if kind in ('clean_observation','unresolved_policy') else 'incomplete',
             'prefix':'accepted','channel_discrepancy':False if kind in ('clean_observation','unresolved_policy') else None,
             'check_failure':False if kind in ('clean_observation','unresolved_policy') else None,
             'cleanup_confirmed':kind!='cleanup_unconfirmed','observation_signature':{'synthetic':True}}
    return {'entry_kind':'pair','terminal':terminal(outcome,kind,evidence)}


class LegacyCampaignTests(unittest.TestCase):
    def setUp(self):
        self.registry=campaign.selection();self.jobs=campaign.plan_for(self.registry)['jobs']

    def run_sweep(self,kind_by_index=None):
        values={};checkpoints=[];kind_by_index=kind_by_index or {}
        def execute(job):
            i=self.jobs.index(job);value=result(job,kind_by_index.get(i,'clean_observation'))
            values[job['job_id']]=value;return value
        report=campaign.drive(self.registry,execute,checkpoints.append)
        return report,values,checkpoints

    def test_exact_sweep_and_separate_singletons(self):
        report,values,checkpoints=self.run_sweep()
        self.assertEqual(report['status'],'completed_bounded_diagnostic')
        self.assertEqual(len(report['started_jobs']),9)
        self.assertEqual(sum(len(j['branches']) for j in self.jobs),16)
        self.assertEqual(verify_accounting(self.registry,report,values),report)
        self.assertTrue(all(not d['repeat_dispatched'] for d in report['decisions']))
        self.assertEqual(checkpoints[1]['started_jobs'],['legacy-000'])
        self.assertEqual(checkpoints[1]['completed_jobs'],[])

    def test_unknown_policy_continues_without_repeat(self):
        report,values,_=self.run_sweep({2:'unresolved_policy'})
        self.assertEqual(len(values),9)
        self.assertFalse(report['decisions'][2]['semantic_evidence_complete'])

    def test_unclean_reference_stops_before_mutations(self):
        report,values,_=self.run_sweep({0:'unresolved_policy'})
        self.assertEqual(report['status'],'halted_terminal_outcome')
        self.assertEqual(len(values),1)
        verify_accounting(self.registry,report,values)

    def test_singleton_halt_including_last_job_is_not_completion(self):
        for index in (7,8):
            report,values,_=self.run_sweep({index:'cleanup_unconfirmed'})
            self.assertEqual(report['status'],'halted_terminal_outcome')
            self.assertEqual(len(values),index+1)
            verify_accounting(self.registry,report,values)

    def test_forged_summary_and_extra_attempt_rejected(self):
        report,values,_=self.run_sweep({2:'missing_evidence'})
        altered=deepcopy(report);altered['status']='completed_bounded_diagnostic'
        with self.assertRaises(ValueError):verify_accounting(self.registry,altered,values)
        values['legacy-003']=result(self.jobs[3])
        with self.assertRaises(ValueError):verify_accounting(self.registry,report,values)

    def test_executor_exception_checkpoint_preserves_started_attempt(self):
        checkpoints=[]
        def fail(job):raise RuntimeError('synthetic launch failure')
        with self.assertRaises(RuntimeError):campaign.drive(self.registry,fail,checkpoints.append)
        self.assertEqual(checkpoints[-1]['status'],'halted_executor_error')
        self.assertEqual(checkpoints[-1]['started_jobs'],['legacy-000'])
        self.assertEqual(checkpoints[-1]['completed_jobs'],[])

    def test_singleton_promotion_and_wrong_job_rejected(self):
        job=self.jobs[-1]
        for field,value in [('paired_comparison_eligible',True),('job_id','foreign'),('channel_discrepancy',False)]:
            observed=result(job);observed[field]=value
            with self.assertRaises(ValueError):campaign.outcome_decision(job,observed)

    def test_outer_budget_covers_all_worker_and_cleanup_limits(self):
        self.assertGreater(campaign.OUTER_TIMEOUT_S,len(self.jobs)*(campaign.JOB_TIMEOUT_S+9)+120)
