from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import quartz_terminal_outcomes as bridge
from mixed_interface.campaign_v2 import build_plan, drive
from mixed_interface.repetition import digest
from test_quartz_repeat_integration import fixtures
from test_quartz_oracle_components import check, find_check
from test_repetition import pair


def read_failure(branches, channel='ui', phase='final_read'):
    raw,run=branches[channel]
    raw.update(status='application_response_error',completed=False,phase='teardown',error={
        'name':'Error','message':'Native read returned 503 for '+bridge.reducer.JOB_PATH,
        'phase':phase,'observation_kind':'application_read_response','http_status':503})
    run.update(status=raw['status'],completed=False,child_exit={'code':1,'signal':None},final_state_sha256=None)
    for key in ('final_job','final_state','final_state_sha256'):raw.pop(key,None)
    remove={'final_business_state','update_response_matches_persisted','fresh_native_final_read','final_state_inactive_scheduler','final_single_resource','no_unregistered_browser_request'}
    raw['checks']=[c for c in raw['checks'] if c['id'] not in remove]
    raw['ui_forms']=[x for x in raw['ui_forms'] if x['label']!='fresh_final_native_read']
    raw['actors']=[x for x in raw['actors'] if x.get('phase')!='final_read']
    for x in raw['trace']:
        x['status']=200
        if x['path'].endswith('/whoami'): x['response']=deepcopy(raw['api_actor'])
        if x['method']=='POST' and x['path']==bridge.reducer.JOB_PATH:
            x.update(status=raw['producer']['status'],request=deepcopy(raw['producer']['request']))
    raw['trace'].append({'source':'direct_api','method':'GET','path':bridge.reducer.JOB_PATH,'phase':phase,'status':503,'request':None,'response':{'error':'fixture'}})
    return raw,run


def outcome(branches,reg,job_id='j'):
    return bridge.pair_terminal({'job_id':job_id},branches,reg,{'fixture':digest(branches)})


class QuartzTerminalTests(unittest.TestCase):
    def setUp(self):self.branches,self.reg=fixtures()
    def kind(self):return outcome(self.branches,self.reg)['terminal']['kind']

    def test_clean_pair(self):self.assertEqual(self.kind(),'clean_observation')

    def test_completed_nonzero_mismatch_is_retained(self):
        raw,run=self.branches['ui'];find_check(raw,'fresh_native_final_read')['passed']=False
        raw['status']=run['status']='source_expectation_mismatch';run['child_exit']['code']=1
        result=outcome(self.branches,self.reg)
        self.assertEqual(result['terminal']['kind'],'completed_mismatch')
        self.assertFalse(result['outcome']['channel_discrepancy'])
        self.assertEqual(run['child_exit']['code'],1)

    def test_wrong_exit_is_environment_failure(self):
        self.branches['api'][1]['child_exit']['code']=1
        self.assertEqual(self.kind(),'environment_failure')

    def test_trace_supported_response_failure_remains_partial(self):
        read_failure(self.branches)
        result=outcome(self.branches,self.reg)
        self.assertEqual(result['terminal']['kind'],'application_response_failure',result['branch_classifications'])
        self.assertEqual(result['outcome']['execution'],'incomplete')
        self.assertIsNone(result['outcome']['channel_discrepancy'])

    def test_response_status_alone_is_not_evidence(self):
        raw,run=read_failure(self.branches);raw['trace'].pop()
        self.assertEqual(self.kind(),'missing_evidence')

    def test_changed_trace_phase_status_path_or_message_is_rejected(self):
        base=deepcopy(self.branches)
        for target,key,value in [('trace','phase','authentication'),('trace','status',500),('trace','path','/other'),('error','message','unrelated')]:
            with self.subTest(key=key):
                self.branches=deepcopy(base);raw,_=read_failure(self.branches)
                (raw['trace'][-1] if target=='trace' else raw['error'])[key]=value
                self.assertEqual(self.kind(),'missing_evidence')

    def test_auth_or_reset_failure_does_not_trigger_diagnostic_repeats(self):
        raw,_=read_failure(self.branches,phase='reset_verification')
        self.assertEqual(self.kind(),'missing_evidence')

    def test_missing_pre_failure_evidence_rejected(self):
        raw,_=read_failure(self.branches)
        raw['checks']=[c for c in raw['checks'] if c['id']!='producer_business_fields']
        self.assertEqual(self.kind(),'missing_evidence')

    def test_tampered_initial_hash_rejected(self):
        raw,_=read_failure(self.branches);raw['initial_state_sha256']='0'*64
        self.assertEqual(self.kind(),'missing_evidence')

    def test_foreign_registered_input_rejected(self):
        raw,_=read_failure(self.branches);raw['registered_inputs']=[]
        self.assertEqual(self.kind(),'missing_evidence')

    def test_unknown_check_rejected(self):
        raw,_=read_failure(self.branches);raw['checks'].append(check('unknown'))
        self.assertEqual(self.kind(),'missing_evidence')

    def test_cleanup_precedes_response_failure(self):
        raw,run=read_failure(self.branches);run['browser_cleanup']['ok']=False
        self.assertEqual(self.kind(),'cleanup_unconfirmed')

    def test_timeout_and_interruption_halt(self):
        raw,run=read_failure(self.branches);run['timed_out']=True
        self.assertEqual(self.kind(),'case_timeout')
        run['timed_out']=False;raw['interruption']='SIGTERM'
        self.assertEqual(self.kind(),'interrupted')

    def test_missing_branch_has_explicit_missing_evidence(self):
        del self.branches['ui'];self.assertEqual(self.kind(),'missing_evidence')

    def test_missing_result_with_confirmed_cleanup_halts(self):
        self.branches['ui']=({},self.branches['ui'][1]);self.assertEqual(self.kind(),'missing_evidence')

    def test_mixed_prefixes_are_incomparable_not_clean(self):
        raw,run=self.branches['ui']
        for data in (raw,run):data.update(accepted_prefix=False,reached_continuation=False)
        raw.update(producer={'kind':'response','status':400,'request':{'description':'before'}},continuation={'attempted':False,'reason':'producer_not_accepted'},consumption_observations=[],ui_forms=[])
        self.reg['ui']['expectation']={'outcome':'reject','category':'implementation_control'};raw['expected_producer']=self.reg['ui']['expectation'];raw['actors']=raw['actors'][:1]
        raw['checks']=[check(x) for x in ['initial_state_inactive_scheduler','post_producer_state_inactive_scheduler','no_unregistered_browser_request','rejected_prefix_left_empty_store','rejected_prefix_full_state_unchanged','producer_expectation']]
        self.assertEqual(self.kind(),'incomparable_observation')

    def test_policy_only_nonzero_is_not_requirement_mismatch(self):
        for c,(raw,run) in self.branches.items():
            raw['policy_unresolved']=True;raw['status']=run['status']='policy_unresolved';run['child_exit']['code']=1
            self.reg[c]['expectation']['category']='unresolved';raw['expected_producer']=self.reg[c]['expectation']
            raw['checks'].append(check('raw_map_preservation_observation',False,'unresolved_policy'))
            if c=='ui':find_check(raw,'native_PUT_payload_matches_bound_intent').update(scope='unresolved_policy',passed=False)
        self.assertEqual(self.kind(),'unresolved_policy')
        find_check(self.branches['ui'][0],'final_business_state')['passed']=False
        self.assertEqual(self.kind(),'completed_mismatch')

    def test_source_shaped_failure_drives_fixed_followups(self):
        plan=build_plan([pair(),pair('candidate','payload_mutation')]);calls=[]
        def execute(job):
            branches,reg=fixtures()
            if job['pair_id']=='candidate':read_failure(branches)
            calls.append(job['job_id']);return outcome(branches,reg,job['job_id'])['terminal']
        state=drive(plan,execute,lambda state:None)
        self.assertEqual(len(calls),6)
        self.assertEqual(state['repeat_summary']['pairs'][0]['status'],'unresolved_execution')

    def test_bounded_real_classifier_subprocess(self):
        # Same CLI called by the Node runner; pinned registry/adapter checks execute.
        root=Path(__file__).resolve().parents[1]
        registry=json.loads((root/'manifests/quartz-job-generated-pool-v2.json').read_bytes())
        spec=next(c for c in registry['cases'] if c['intervention']=='route_only' and [o['interface'] for o in c['operations']]==['api','ui'])
        raw,run=read_failure(self.branches)
        raw.update(case_id=spec['case_id'],registered_inputs=spec['operations'],expected_producer=spec['expectation'])
        run['case_id']=spec['case_id'];raw['producer']['request']=spec['operations'][0]['input']
        raw['bindings']['command']['description']=spec['operations'][1]['input']['description']
        for x in raw['trace']:
            if x['method']=='POST' and x['path']==bridge.reducer.JOB_PATH:x['request']=spec['operations'][0]['input']
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            (folder/'result.json').write_text(json.dumps(raw));(folder/'run.json').write_text(json.dumps(run))
            child=subprocess.run([sys.executable,str(root/'scripts/quartz_terminal_outcomes.py'),'--branch',str(folder/'result.json'),'--run',str(folder/'run.json'),'--registry',str(root/'manifests/quartz-job-generated-pool-v2.json')],capture_output=True,text=True,timeout=10)
            self.assertEqual(child.returncode,0,child.stderr)
            self.assertEqual(json.loads(child.stdout)['action'],'continue',child.stdout)
            self.assertEqual(json.loads(child.stdout)['kind'],'application_response_failure')

    def test_partial_failure_cannot_hide_payload_guard_failure(self):
        raw,_=read_failure(self.branches);find_check(raw,'native_PUT_payload_matches_bound_intent')['passed']=False
        self.assertEqual(self.kind(),'missing_evidence')

    def test_failed_actor_trace_is_not_application_failure(self):
        raw,_=read_failure(self.branches)
        for event in raw['trace']:
            if event['path'].endswith('/whoami'):event['response']={'username':'other'}
        self.assertEqual(self.kind(),'missing_evidence')

    def test_rejected_pairs_remain_separate_from_continuations(self):
        for c,(raw,run) in self.branches.items():
            for data in (raw,run):data.update(accepted_prefix=False,reached_continuation=False)
            raw.update(producer={'kind':'response','status':400,'request':{'description':'before'}},continuation={'attempted':False,'reason':'producer_not_accepted'},consumption_observations=[],ui_forms=[])
            self.reg[c]['expectation']={'outcome':'reject','category':'implementation_control'};raw['expected_producer']=self.reg[c]['expectation'];raw['actors']=raw['actors'][:1]
            raw['checks']=[check(x) for x in ['initial_state_inactive_scheduler','post_producer_state_inactive_scheduler','no_unregistered_browser_request','rejected_prefix_left_empty_store','rejected_prefix_full_state_unchanged','producer_expectation']]
        self.assertEqual(self.kind(),'matched_rejection')

    def test_supported_earlier_read_failure_phases(self):
        for phase in ('producer_state','continuation'):
            with self.subTest(phase=phase):
                branches,reg=fixtures();raw,run=read_failure(branches,channel='api',phase=phase)
                raw.pop('continuation');raw['ui_forms']=[]
                raw['checks']=[c for c in raw['checks'] if c['id'] not in ('continuation_status','consumer_api_loaded_bound_state')]
                raw['trace']=[x for x in raw['trace'] if x['method']!='PUT']
                if phase=='producer_state':
                    raw['reached_continuation']=run['reached_continuation']=False
                    raw.pop('stored_prefix')
                    raw['checks']=[c for c in raw['checks'] if c['id'] not in ('producer_response_matches_persisted_job','producer_business_fields','single_stored_resource')]
                result=outcome(branches,reg)
                self.assertEqual(result['terminal']['kind'],'application_response_failure',result['branch_classifications'])

    def test_changed_bound_intent_rejected(self):
        raw,_=read_failure(self.branches);raw['bindings']['command']['description']='foreign intent'
        self.assertEqual(self.kind(),'missing_evidence')
