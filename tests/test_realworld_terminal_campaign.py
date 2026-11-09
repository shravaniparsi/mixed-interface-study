"""Pair extraction and scheduled-repeat fixtures; no applications executed."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import realworld_terminal_campaign as bridge
from mixed_interface.campaign_v2 import drive
from mixed_interface.terminal_outcomes import decision


class RealWorldCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive=ROOT/'results/realworld-paired-controls-ci-20261107'
        cls.registry=bridge.read(cls.archive/'registered-candidates.json')
        cls.summary=bridge.read(cls.archive/'summary.json')
        cls.fixture=bridge.read(cls.archive/'fixture-references.json')
        cls.plan=bridge.plan_for(cls.registry)

    def setUp(self):
        self.job=deepcopy(self.plan['schedule']['initial_jobs'][0])
        self.spec=deepcopy(bridge.validate_job(self.job,self.registry))
        self.branches={b['continuation']:(bridge.read(self.archive/b['evidence']),deepcopy(b))
                       for b in self.summary['branches'] if b['candidate_id']==self.job['pair_id']}

    def result(self,cleanup=True):
        return bridge.pair_result(self.job,self.branches,self.spec,self.fixture,self.summary['fixture_sha256'],cleanup,{'fixture':'a'*64})

    def test_four_baselines_alternate_order(self):
        self.assertEqual(len(self.plan['schedule']['initial_jobs']),4)
        self.assertEqual([b['continuation'] for b in self.plan['schedule']['initial_jobs'][1]['branches']],['ui','api'])

    def test_archive_pair_clean_and_json_stable(self):
        result=self.result()
        self.assertEqual(result['terminal']['kind'],'clean_observation')
        self.assertEqual(json.loads(json.dumps(result)),result)
        self.assertTrue(all(result['comparability'].values()))

    def test_all_baseline_pairs(self):
        for job in self.plan['schedule']['initial_jobs']:
            self.job=job;self.spec=bridge.validate_job(job,self.registry)
            self.branches={b['continuation']:(bridge.read(self.archive/b['evidence']),b) for b in self.summary['branches'] if b['candidate_id']==job['pair_id']}
            self.assertEqual(self.result()['terminal']['kind'],'clean_observation')

    def test_wrong_order_rejected(self):
        self.job['branches'].reverse()
        with self.assertRaises(ValueError):bridge.validate_job(self.job,self.registry)

    def test_foreign_job_rejected(self):
        self.job['pair_id']='profile-bio-null'
        with self.assertRaises(ValueError):bridge.validate_job(self.job,self.registry)

    def test_false_reset_flag_rejected(self):
        self.job['branches'][0]['fresh_reset_required']=False
        with self.assertRaises(ValueError):bridge.validate_job(self.job,self.registry)

    def test_wrong_repeat_number_rejected(self):
        self.job['repetition']=99
        with self.assertRaises(ValueError):bridge.validate_job(self.job,self.registry)

    def test_reset_difference_is_incomparable(self):
        self.branches['api'][1]['reset_sha256']='b'*64
        result=self.result()['terminal']
        self.assertEqual(result['kind'],'incomparable_observation')
        self.assertTrue(decision(result)['repeat'])
        self.assertEqual(result['outcome']['execution'],'incomplete')

    def test_missing_branch_halts(self):
        del self.branches['ui']
        self.assertEqual(self.result()['terminal']['kind'],'missing_evidence')

    def test_cleanup_precedence(self):
        del self.branches['ui']
        self.assertEqual(self.result(False)['terminal']['kind'],'cleanup_unconfirmed')

    def test_failed_backend_cleanup_precedence(self):
        self.branches['ui'][1]['backend_exit_confirmed']=False
        self.assertEqual(self.result()['terminal']['kind'],'cleanup_unconfirmed')

    def test_uncorroborated_verdict_not_a_pair_mismatch(self):
        self.branches['api'][0]['checks'][0]['passed']=False
        self.assertEqual(self.result()['terminal']['kind'],'missing_evidence')

    def test_scheduled_fixture_mismatch_repeats_with_controls(self):
        calls=[]
        def execute(job):
            bridge.validate_job(job,self.registry);calls.append(job)
            self.job=job;self.spec=deepcopy(bridge.validate_job(job,self.registry))
            self.branches={b['continuation']:(bridge.read(self.archive/b['evidence']),deepcopy(b)) for b in self.summary['branches'] if b['candidate_id']==job['pair_id']}
            if job['pair_id']==bridge.BASELINES[0] and job['role']!='reference_control':
                self.spec['expectation']['outcome']='reject'
                for raw,run in self.branches.values():raw['expectation']=deepcopy(self.spec['expectation'])
            return self.result()['terminal']
        state=drive(self.plan,execute,lambda _:None)
        self.assertEqual(len(calls),8)
        self.assertEqual([j['role'] for j in calls[4:]],['candidate_repeat','reference_control']*2)
        # Initial baseline itself was flagged; repeated clean controls cannot erase it.
        self.assertEqual(state['repeat_summary']['pairs'][0]['status'],'unresolved_control_failure')

    def test_halt_stops_later_jobs(self):
        calls=[]
        def execute(job):
            calls.append(job);self.job=job
            return self.result(False)['terminal']
        state=drive(self.plan,execute,lambda _:None)
        self.assertEqual(len(calls),1)
        self.assertEqual(state['status'],'halted_terminal_outcome')

    def make_job_directory(self,root):
        import shutil
        directory=root/'initial-000';directory.mkdir()
        run=directory/'run'/'attempt';run.mkdir(parents=True)
        bridge.write(directory/'job.json',self.job)
        execution={'exit_confirmed':True,'errors':[],'returncode':0}
        bridge.write(directory/'execution.json',execution)
        summary=deepcopy(self.summary)
        summary.update(job=self.job,job_sha256=bridge.sha(directory/'job.json'),
                       schedule=[{'candidate_id':self.job['pair_id'],'order':['api','ui']}],
                       branches=[b for b in summary['branches'] if b['candidate_id']==self.job['pair_id']])
        summary['source_sha256'].pop('run_realworld_paired_controls.py')
        summary['source_sha256']['run_realworld_pair_job_v2.py']=bridge.sha(ROOT/'scripts/run_realworld_pair_job_v2.py')
        for name in summary['source_sha256']:
            source=ROOT/('src/mixed_interface/normalization.py' if name=='normalization.py' else 'scripts/'+name)
            shutil.copyfile(source,run/name)
        for name in ('registered-candidates.json','fixture-references.json'):
            shutil.copyfile(self.archive/name,run/name)
        for b in summary['branches']:shutil.copyfile(self.archive/b['evidence'],run/b['evidence'])
        bridge.write(run/'summary.json',summary)
        return directory,run,execution

    def test_file_backed_job_extraction(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            directory,run,execution=self.make_job_directory(Path(tmp))
            self.assertEqual(bridge.read_job(directory,self.job,self.registry,execution)['terminal']['kind'],'clean_observation')

    def test_file_backed_source_change_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            directory,run,execution=self.make_job_directory(Path(tmp))
            (run/'realworld_paired_case.mjs').write_text('altered')
            with self.assertRaises(ValueError):bridge.read_job(directory,self.job,self.registry,execution)

    def test_file_backed_branch_reordering_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            directory,run,execution=self.make_job_directory(Path(tmp))
            summary=bridge.read(run/'summary.json');summary['branches'].reverse();bridge.write(run/'summary.json',summary)
            with self.assertRaises(ValueError):bridge.read_job(directory,self.job,self.registry,execution)
