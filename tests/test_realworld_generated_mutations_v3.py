"""Synthetic mutation outcomes and bounded driver accounting; no app runs."""
from copy import deepcopy
from pathlib import Path
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from realworld_generated_mutations_v3 import plan,drive,IDS
from realworld_generated_terminal_v3 import classify,compare
from realworld_generated_runtime_v3 import branch
from realworld_generated_bindings_v1 import case_for
from realworld_generated_loader_v1 import sha
from generated_positive_fixture_v1 import complete
from generated_mutation_fixture_v3 import accepted,rejected
from test_realworld_generated_loader_v1 import put


def outcome(job,mode='expected'):
    branches={}
    for channel in ('api','ui'):
        if job['job_id']=='generated-001':raw,run,_=complete('api',channel)
        elif mode=='missing':raw,run=rejected(job,channel,500,False)
        elif job['job_id'] in ('generated-002','generated-003','generated-004') and mode=='expected':raw,run=rejected(job,channel)
        else:raw,run=accepted(job,channel)
        branches[channel]=(raw,run)
    return compare(job,branches,{'synthetic':'0'*64})


class GeneratedMutationTests(unittest.TestCase):
    def test_exact_plan_and_policies(self):
        value=plan();self.assertEqual(tuple(j['job_id'] for j in value['jobs']),IDS)
        self.assertEqual(value['branches'],16);self.assertFalse(value['automatic_repeats'])
        self.assertEqual([case_for(j,'api')['expectation']['outcome'] for j in value['jobs']],['accept','reject','reject','reject','accept','accept','unknown','unknown'])

    def test_all_fourteen_accepted_mutation_branches(self):
        expected=['completed_mismatch']*3+['clean_observation']*2+['unresolved_policy']*2
        for job,kind in zip(plan()['jobs'][1:],expected):
            for channel in ('api','ui'):
                with self.subTest(job=job['job_id'],channel=channel):
                    raw,run=accepted(job,channel);before=deepcopy(raw)
                    self.assertEqual(classify(job,channel,raw,run)['kind'],kind)
                    self.assertEqual(raw,before)
            self.assertEqual(outcome(job,'accepted')['terminal']['kind'],kind)

    def test_expected_rejection_and_unreadable_rejection(self):
        for job in plan()['jobs'][1:4]:
            self.assertEqual(outcome(job)['terminal']['kind'],'matched_rejection')
            self.assertEqual(outcome(job,'missing')['terminal']['kind'],'missing_evidence')

    def test_continuation_after_rejection_is_never_complete(self):
        job=plan()['jobs'][1];raw,run=rejected(job,'api')
        raw['trace'].append({'sequence':len(raw['trace'])+1,'type':'request','source':'api','phase':'consumer','method':'PUT','path':'/api/articles/unexpected','payload':{}})
        value=classify(job,'api',raw,run)
        self.assertEqual(value['kind'],'missing_evidence');self.assertIn('continuation_trace_after_unsuccessful_prefix',value['issues'])

    def test_sweep_keeps_unknown_policy_and_dispatches_no_repeats(self):
        observed=[]
        def execute(job):observed.append(job['job_id']);return outcome(job)
        result=drive(execute,lambda _:None)
        self.assertEqual(result['status'],'completed_bounded_diagnostic');self.assertEqual(observed,list(IDS))
        self.assertEqual([d['kind'] for d in result['decisions']][-2:],['unresolved_policy']*2)
        self.assertTrue(all(d['repeat_dispatched'] is False for d in result['decisions']))

    def test_missing_evidence_halts_early_and_at_final_job(self):
        for halted in ('generated-002','generated-008'):
            snapshots=[]
            result=drive(lambda j:outcome(j,'missing' if j['job_id']==halted else 'expected'),snapshots.append)
            self.assertEqual(result['status'],'halted_terminal_outcome')
            self.assertEqual(result['completed_jobs'],list(IDS[:IDS.index(halted)+1]))
            self.assertEqual(result['decisions'][-1]['kind'],'missing_evidence')
            self.assertEqual(snapshots[-1],result)

    def test_reference_failure_and_executor_exception_stop_dispatch(self):
        snapshots=[]
        def fail(job):raise ValueError('synthetic executor failure')
        with self.assertRaises(ValueError):drive(fail,snapshots.append)
        self.assertEqual(snapshots[-1]['started_jobs'],['generated-001']);self.assertEqual(snapshots[-1]['completed_jobs'],[])
        def bad_control(job):
            raw,run,_=complete('api','api');other,other_run,_=complete('api','ui');other_run['reset_sha256']='b'*64
            return compare(job,{'api':(raw,run),'ui':(other,other_run)},{'synthetic':'0'*64})
        result=drive(bad_control,lambda _:None);self.assertEqual(result['completed_jobs'],['generated-001'])
        self.assertEqual(result['status'],'halted_terminal_outcome')

    def test_transport_loader_preserves_semantically_incomplete_evidence(self):
        job=plan()['jobs'][-1];raw,run=rejected(job,'api',500,False)
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);put(d/'case.json',case_for(job,'api'));put(d/'observation.json',raw)
            (d/'reset.sqlite3').write_bytes(b'synthetic reset');h=sha(d/'reset.sqlite3')
            put(d/'reset.json',{'sha256':h,'independent_offline_reset':True})
            run.update(raw_sha256=sha(d/'observation.json'),reset_sha256=h,timed_out=False,started_monotonic=1.,finished_monotonic=2.,branch_total_s=1.)
            put(d/'run.json',run);put(d/'execution.json',{'exit_confirmed':True,'returncode':0,'errors':[]})
            for file in ('cleanup.json','parent-browser-cleanup.json'):put(d/file,{'ok':True})
            put(d/'port-check.json',{'backend_port_closed':True})
            loaded=branch(d,job,'api',h)
            self.assertEqual(classify(job,'api',*loaded)['kind'],'missing_evidence')
