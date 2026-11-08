from copy import deepcopy
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from quartz_repeat_outcomes import pair_outcome
from test_quartz_oracle_components import positive, find_check, check
from test_repetition import pair, outcome
from mixed_interface.repetition import build_plan
from mixed_interface.campaign import drive


def fixtures():
    branches={}; registered={}
    business={'jobKeyDTO':{'name':'pilot-job','group':'RESEARCH'},'jobClassName':'fixture.Job','description':'before',
              'durable':True,'requestsRecovery':False,'jobDataMap':{},'triggerKeys':[]}
    for i,c in enumerate(('api','ui')):
        raw,run=positive('api-'+c)
        spec={'case_id':raw['case_id'],'intervention':'route_only','operations':[{'interface':'api','input':{'description':'before'}},{'interface':c,'input':{'description':'after'}}], 'expectation':{'outcome':'accept','category':'implementation_control'}}
        raw.update(registered_inputs=spec['operations'],expected_producer=spec['expectation'],stored_prefix=deepcopy(business),final_job={**business,'description':'after'})
        raw['producer']['request']={'description':'before'}; raw['bindings']['command']={'description':'after'}
        run['server_pid']=100+i
        branches[c]=(raw,run);registered[c]=spec
    return branches,registered


class OutcomeBridgeTests(unittest.TestCase):
    def test_clean_pair_maps_to_no_followup(self):
        branches,reg=fixtures();r=pair_outcome({'job_id':'j'},branches,reg)
        self.assertEqual(r['outcome']['execution'],'complete',r)
        self.assertFalse(r['outcome']['check_failure']);self.assertFalse(r['outcome']['channel_discrepancy'])

    def test_shared_failure_triggers_repeat_without_exclusive_credit(self):
        branches,reg=fixtures();find_check(branches['ui'][0],'fresh_native_final_read')['passed']=False
        o=pair_outcome({'job_id':'j'},branches,reg)['outcome']
        self.assertEqual(o['execution'],'complete');self.assertTrue(o['check_failure']);self.assertFalse(o['channel_discrepancy'])

    def test_assigned_failure_sets_channel_discrepancy(self):
        branches,reg=fixtures();find_check(branches['ui'][0],'continuation_status')['passed']=False
        o=pair_outcome({'job_id':'j'},branches,reg)['outcome']
        self.assertEqual(o['execution'],'complete');self.assertTrue(o['channel_discrepancy'])

    def test_payload_difference_is_unresolved(self):
        branches,reg=fixtures();find_check(branches['ui'][0],'native_PUT_payload_matches_bound_intent')['passed']=False
        o=pair_outcome({'job_id':'j'},branches,reg)['outcome']
        self.assertEqual(o['execution'],'incomplete');self.assertIsNone(o['channel_discrepancy'])

    def test_missing_branch_cannot_confirm_cleanup(self):
        branches,reg=fixtures();del branches['ui']
        o=pair_outcome({'job_id':'j'},branches,reg)['outcome']
        self.assertEqual(o['execution'],'incomplete');self.assertFalse(o['cleanup_confirmed'])

    def test_same_jvm_is_not_independent_reset(self):
        branches,reg=fixtures();branches['ui'][1]['server_pid']=100
        self.assertEqual(pair_outcome({'job_id':'j'},branches,reg)['outcome']['execution'],'incomplete')

    def test_actor_mismatch_is_unresolved(self):
        branches,reg=fixtures();branches['ui'][0]['api_actor']={'username':'another'}
        self.assertEqual(pair_outcome({'job_id':'j'},branches,reg)['outcome']['execution'],'incomplete')

    def test_unknown_check_is_unresolved(self):
        branches,reg=fixtures();branches['ui'][0]['checks'].append({'id':'unknown','scope':'requirement','passed':True})
        self.assertEqual(pair_outcome({'job_id':'j'},branches,reg)['outcome']['execution'],'incomplete')

    def test_matched_rejections_have_no_downstream_failure(self):
        branches,reg=fixtures()
        for c,(raw,run) in branches.items():
            for data in (raw,run):data.update(accepted_prefix=False,reached_continuation=False)
            raw.update(producer={'kind':'response','status':400,'request':{'description':'before'}},
                continuation={'attempted':False,'reason':'producer_not_accepted'},consumption_observations=[],ui_forms=[])
            reg[c]['expectation']={'outcome':'reject','category':'implementation_control'};raw['expected_producer']=reg[c]['expectation']
            raw['actors']=raw['actors'][:1]
            raw['checks']=[check(x) for x in ['initial_state_inactive_scheduler','post_producer_state_inactive_scheduler','no_unregistered_browser_request','rejected_prefix_left_empty_store','rejected_prefix_full_state_unchanged','producer_expectation']]
        o=pair_outcome({'job_id':'j'},branches,reg)['outcome']
        self.assertEqual(o['execution'],'complete');self.assertEqual(o['prefix'],'rejected')
        self.assertFalse(o['check_failure']);self.assertFalse(o['channel_discrepancy'])

    def test_policy_only_failure_does_not_become_requirement_signal(self):
        branches,reg=fixtures()
        for c,(raw,run) in branches.items():
            raw['policy_unresolved']=True;raw['status']=run['status']='policy_unresolved'
            reg[c]['expectation']['category']='unresolved';raw['expected_producer']=reg[c]['expectation']
            raw['checks'].append(check('raw_map_preservation_observation',False,'unresolved_policy'))
            if c=='ui':find_check(raw,'native_PUT_payload_matches_bound_intent')['scope']='unresolved_policy'
        o=pair_outcome({'job_id':'j'},branches,reg)['outcome']
        self.assertEqual(o['execution'],'complete');self.assertFalse(o['check_failure']);self.assertFalse(o['channel_discrepancy'])


class DriverTests(unittest.TestCase):
    def setUp(self):self.plan=build_plan([pair(),pair('candidate','payload_mutation')]);self.events=[]
    def test_intent_saved_before_execute_and_followup_order_preserved(self):
        calls=[]
        def execute(job):
            self.assertEqual(self.events[-1]['dispatches'][-1]['status'],'started')
            self.assertEqual(self.events[-1]['dispatches'][-1]['job'],job)
            calls.append(job)
            return outcome(job,job['pair_id']=='candidate')
        result=drive(self.plan,execute,self.events.append)
        self.assertEqual(result['status'],'completed_observations');self.assertEqual(len(calls),6)
        self.assertEqual([j['role'] for j in calls[2:]],['candidate_repeat','reference_control']*2)
        self.assertEqual(len({j['job_id'] for j in calls}),6)

    def test_incomplete_pair_stops_before_next_dispatch(self):
        calls=[]
        def execute(job):
            calls.append(job);o=outcome(job);o.update(execution='incomplete',prefix='unobserved',observation_signature=None);return o
        result=drive(self.plan,execute,self.events.append)
        self.assertEqual(result['status'],'halted_execution_or_cleanup');self.assertEqual(len(calls),1)

    def test_uncertain_cleanup_stops(self):
        def execute(job):o=outcome(job);o['cleanup_confirmed']=False;return o
        self.assertEqual(drive(self.plan,execute,self.events.append)['status'],'halted_execution_or_cleanup')
        self.assertEqual(len(self.events[-1]['dispatches']),1)

    def test_executor_error_preserves_started_job(self):
        def execute(job):raise RuntimeError('fixture failure')
        with self.assertRaises(RuntimeError):drive(self.plan,execute,self.events.append)
        self.assertEqual(self.events[-1]['status'],'halted_executor_error')
        self.assertIn('fixture failure',self.events[-1]['dispatches'][-1]['error'])

    def test_foreign_outcome_is_not_merged(self):
        def execute(job):o=outcome(job);o['job_id']='foreign';return o
        with self.assertRaisesRegex(ValueError,'another job'):drive(self.plan,execute,self.events.append)
        self.assertEqual(self.events[-1]['initial'],[])
