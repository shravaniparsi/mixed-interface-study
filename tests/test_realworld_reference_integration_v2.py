"""Prospective terminal/driver wiring preserves incomplete paths and frozen evidence."""
from copy import deepcopy
from pathlib import Path
import sys,tempfile,shutil,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from realworld_reference_terminal_v2 import extract
from replay_realworld_references_v1 import inputs
from realworld_terminal_campaign import read
from realworld_legacy_jobs_v8 import selection
from realworld_legacy_jobs_v10 import read_job
from realworld_legacy_campaign_v10 import drive,outcome_decision
from validate_realworld_legacy_campaign_v10 import verify_accounting
from mixed_interface.terminal_outcomes import decision
ARCHIVE=ROOT/'results/realworld-fresh-legacy-ci-20261109/realworld-legacy-v9'

class ReferenceIntegrationTests(unittest.TestCase):
    def test_proof_changes_terminal_signature_and_dispatch_decision(self):
        args=inputs(ARCHIVE/'legacy-006');before=deepcopy(args);v=extract(*args)
        self.assertEqual(args,before)
        self.assertEqual(v['literal_terminal']['kind'],'incomparable_observation')
        self.assertEqual(v['terminal']['kind'],'clean_observation')
        self.assertEqual(v['terminal']['outcome']['execution'],'complete')
        self.assertEqual(v['terminal']['outcome']['observation_signature']['gates'],v['comparability'])
        self.assertTrue(all(v['comparability'].values()))
        self.assertFalse(decision(v['terminal'])['repeat'])
        self.assertTrue(decision(v['literal_terminal'])['repeat'])
        self.assertEqual(outcome_decision(args[0],v)['kind'],'clean_observation')

    def test_failed_references_and_lifecycle_failures_keep_original_terminal(self):
        for jid in ('legacy-004','legacy-005'):
            v=extract(*inputs(ARCHIVE/jid))
            self.assertEqual(v['terminal'],v['literal_terminal'])
            self.assertEqual(v['terminal']['kind'],'incomparable_observation')
        for mode,kind in [('cleanup','cleanup_unconfirmed'),('timeout','case_timeout'),('exit','environment_failure'),('reset','incomparable_observation')]:
            args=list(deepcopy(inputs(ARCHIVE/'legacy-006')))
            if mode=='cleanup':args[5]=False
            elif mode=='timeout':args[1]['ui'][1]['timed_out']=True
            elif mode=='exit':args[1]['ui'][1]['exit_code']=7
            else:args[1]['ui'][1]['reset_sha256']='different'
            v=extract(*args);self.assertEqual(v['terminal']['kind'],kind)
            self.assertEqual(v['terminal'],v['literal_terminal'])

    def test_loader_driver_and_independent_accounting_replay(self):
        registry=selection();observations={}
        def execute(job):
            d=ARCHIVE/job['job_id'];v=read_job(d,job,registry,read(d/'execution.json'));observations[job['job_id']]=v
            if job['entry_kind']=='singleton':self.assertEqual(v,read(d/'observations.json'))
            return v
        report=drive(registry,execute,lambda _:None)
        self.assertEqual(verify_accounting(registry,report,observations),report)
        self.assertEqual([d['kind'] for d in report['decisions']],['clean_observation','clean_observation','incomparable_observation','incomparable_observation','clean_observation','clean_observation','clean_observation'])
        self.assertTrue(all(not d['repeat_dispatched'] for d in report['decisions']))
        altered=deepcopy(report);altered['decisions'][4]['kind']='incomparable_observation'
        with self.assertRaises(ValueError):verify_accounting(registry,altered,observations)
        altered=deepcopy(observations);altered['extra']=altered['legacy-006']
        with self.assertRaises(ValueError):verify_accounting(registry,report,altered)

    def test_loader_rejects_tampered_transport_before_reference_comparison(self):
        original=ARCHIVE/'legacy-006';job=read(original/'job.json')
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)/'job';shutil.copytree(original,d)
            (d/'job.json').write_text('{}')
            with self.assertRaises(ValueError):read_job(d,job,selection(),read(d/'execution.json'))
