"""Synthetic lifecycle evidence checks; live qualification runs separately."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'scripts/ci'))
from validate_quartz_lifecycle import validate_failure
from run_quartz_lifecycle import browser_checkpoint


def records(stage='case_deadline'):
    adapter={'pid':12,'start_ticks':'100','state':'S'}
    record={'returncode':1,'elapsed_s':84,'checkpoint':{'adapter':adapter},'exit_after_signal_s':2,
            'injection':{'signal':'SIGSTOP','target':'owned_adapter','suspended_identity':{**adapter,'state':'T'}}}
    execution={'exit_confirmed':True,'successful_exit':False,'hard_kill':False,'timed_out':False,'interrupted':False}
    campaign={'status':'halted_executor_error','dispatches':[{'job':{'job_id':'initial-000'},'error':'RuntimeError: incomplete runner'}],'initial':[],'repeated':[]}
    branch={'completed':False,'status':'interrupted','application_port_released':True,'browser_process_absent':True,
            'node_cleanup':{'ok':True},'java_cleanup':{'ok':True},'browser_cleanup':{'ok':True},
            'timed_out':True,'child_exit':{'signal':'SIGKILL'},'elapsed_ms':83000}
    summary={'mode':'controls','status':'incomplete','cases':[branch],'case_count':2,
             'effective_options':{'case_timeout_ms':75000},'validation_interrupt_at':None}
    if stage=='external_sigterm':
        record['injection']={'signal':'SIGTERM','target':'campaign'};execution['interrupted']=True;summary['interruption']='SIGTERM'
    return record,campaign,execution,summary


class FailureEvidenceTests(unittest.TestCase):
    def test_declared_deadline_and_external_stop_records_pass(self):
        for stage in ('case_deadline','external_sigterm'):validate_failure(stage,*records(stage))

    def test_special_validation_pause_does_not_qualify_real_deadline(self):
        r,c,e,s=records();s['validation_interrupt_at']='after-browser'
        with self.assertRaises(ValueError):validate_failure('case_deadline',r,c,e,s)

    def test_shorter_deadline_cannot_replace_registered_deadline(self):
        r,c,e,s=records();s['effective_options']['case_timeout_ms']=10000
        with self.assertRaises(ValueError):validate_failure('case_deadline',r,c,e,s)

    def test_early_or_excessive_branch_time_rejected(self):
        for duration in (74000,106000):
            r,c,e,s=records();s['cases'][0]['elapsed_ms']=duration
            with self.assertRaises(ValueError):validate_failure('case_deadline',r,c,e,s)

    def test_second_branch_or_followup_invalidates_stop(self):
        r,c,e,s=records();s['cases'].append(deepcopy(s['cases'][0]))
        with self.assertRaises(ValueError):validate_failure('case_deadline',r,c,e,s)
        r,c,e,s=records();c['followup_plan']={}
        with self.assertRaises(ValueError):validate_failure('case_deadline',r,c,e,s)

    def test_pid_reuse_cannot_establish_suspension(self):
        r,c,e,s=records();r['injection']['suspended_identity']['start_ticks']='other'
        with self.assertRaises(ValueError):validate_failure('case_deadline',r,c,e,s)

    def test_outer_hard_kill_is_not_clean_deadline_qualification(self):
        r,c,e,s=records();e['hard_kill']=True
        with self.assertRaises(ValueError):validate_failure('case_deadline',r,c,e,s)

    def test_missing_cleanup_cannot_qualify(self):
        r,c,e,s=records();s['cases'][0]['browser_cleanup']['ok']=False
        with self.assertRaises(ValueError):validate_failure('case_deadline',r,c,e,s)

    def test_successful_result_cannot_replace_interrupted_attempt(self):
        r,c,e,s=records();s['cases'][0]['completed']=True
        with self.assertRaises(ValueError):validate_failure('case_deadline',r,c,e,s)

    def test_external_signal_requires_runner_signal_evidence(self):
        r,c,e,s=records('external_sigterm');s['interruption']='SIGINT'
        with self.assertRaises(ValueError):validate_failure('external_sigterm',r,c,e,s)


class CheckpointTests(unittest.TestCase):
    def test_only_owned_marker_matched_browser_qualifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage=Path(tmp);case=stage/'initial-000/run/001-ui-api';case.mkdir(parents=True)
            (case/'browser-pid.json').write_text(json.dumps({'pid':13,'marker':'--codex-study-case=fixture'}))
            def p(pid,cmd):return {'pid':pid,'ppid':1,'start_ticks':str(pid),'state':'S','command':cmd}
            table={12:p(12,'node quartz_generated_case.mjs --output '+str(case)),13:p(13,'chrome --codex-study-case=fixture'),14:p(14,'java org.springframework.boot.loader.launch.PropertiesLauncher')}
            with patch('run_quartz_lifecycle.port_open',return_value=True):
                self.assertIsNotNone(browser_checkpoint(stage,table,table))
                self.assertIsNone(browser_checkpoint(stage,table,{12:table[12],14:table[14]}))
                table[13]['command']='chrome --codex-study-case=unrelated'
                self.assertIsNone(browser_checkpoint(stage,table,table))

    def test_closed_port_prevents_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('run_quartz_lifecycle.port_open',return_value=False):
                self.assertIsNone(browser_checkpoint(Path(tmp),{},{}))
