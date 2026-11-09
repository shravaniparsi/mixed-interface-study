import sys,tempfile,unittest,shutil
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import petclinic_terminal_campaign as p
from mixed_interface.campaign_v2 import drive

class PetClinicCampaignTests(unittest.TestCase):
    def setUp(self):self.contract=p.contract();self.job=deepcopy(self.contract['plan']['schedule']['initial_jobs'][0])
    def test_six_controls_and_alternating_order(self):
        jobs=self.contract['plan']['schedule']['initial_jobs'];self.assertEqual(len(jobs),6)
        for i,j in enumerate(jobs):self.assertEqual([b['continuation'] for b in j['branches']],['api','ui'] if i%2==0 else ['ui','api'])
    def test_reference_is_positive_same_workflow(self):
        pairs=self.contract['plan']['schedule']['pairs'];by={x['pair_id']:x for x in pairs}
        for c in pairs:
            ref=by[c['reference_control']];self.assertEqual(ref['workflow_id'],c['workflow_id']);self.assertEqual(ref['intervention'],'route_only')
    def test_every_declared_followup_validates(self):
        for j in self.contract['allowed_jobs']:self.assertEqual(p.validate_job(j)['id'],j['pair_id'])
    def test_changed_order_rejected(self):
        self.job['branches'].reverse()
        with self.assertRaises(ValueError):p.validate_job(self.job)
    def test_foreign_candidate_rejected(self):
        self.job['pair_id']='owner_telephone_11'
        with self.assertRaises(ValueError):p.validate_job(self.job)
    def test_reused_job_id_rejected(self):
        self.job['job_id']='initial-001'
        with self.assertRaises(ValueError):p.validate_job(self.job)
    def fixture(self,d,job):
        run=d/'run';run.mkdir();p.write(d/'job.json',job);p.write(run/'job.json',job)
        shutil.copyfile(ROOT/p.CONTROL,run/'controls.json');shutil.copyfile(ROOT/p.REGISTRY,run/'registered-candidates.json')
        s={'kind':'petclinic_terminal_pair_v2','job':job,'job_sha256':p.sha(d/'job.json'),'controls_sha256':p.CONTROL_SHA,'registry_sha256':self.contract['registry_sha256'],'finished_at':'fixture','backend_stopped':True,'branches':[]}
        for archived,live,key in [('executed_boundary_slice.mjs',p.RUNNER,'runner_sha256'),('petclinic_job_binding.mjs',p.BINDING,'binding_sha256'),('petclinic_integrity.mjs','scripts/petclinic_integrity.mjs','integrity_helper_sha256'),('petclinic_response_capture.mjs','scripts/petclinic_response_capture.mjs','capture_helper_sha256'),('petclinic_cleanup.mjs','scripts/petclinic_cleanup.mjs','cleanup_helper_sha256')]:
            shutil.copyfile(ROOT/live,run/archived);s[key]=p.sha(run/archived)
        for b in job['branches']:
            oracle={'api':'api_semantic','ui':'fresh_ui'}[b['continuation']];name=job['pair_id']+'-'+oracle+'.json'
            shutil.copyfile(ROOT/'results/petclinic-integrity-ci-20261107/observations'/name,run/name)
            raw=p.read(run/name);s['branches'].append({'candidate_id':job['pair_id'],'oracle':oracle,'status':raw['status'],'result':name})
        p.write(run/'summary.json',s);execution={'exit_confirmed':True,'returncode':0,'errors':[]};p.write(d/'execution.json',execution)
        return execution
    def test_all_controls_reconstruct_in_declared_order(self):
        for job in self.contract['plan']['schedule']['initial_jobs']:
            with tempfile.TemporaryDirectory() as tmp:
                d=Path(tmp);ex=self.fixture(d,job);result=p.read_job(d,job,ex)
                self.assertEqual(result['terminal']['kind'],'clean_observation' if p.validate_job(job)['prefix_status']==201 else 'matched_rejection')
    def test_reordered_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);ex=self.fixture(d,self.job);s=p.read(d/'run/summary.json');s['branches'].reverse();p.write(d/'run/summary.json',s)
            with self.assertRaises(ValueError):p.read_job(d,self.job,ex)
    def test_source_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);ex=self.fixture(d,self.job);(d/'run/executed_boundary_slice.mjs').write_text('altered')
            with self.assertRaises(ValueError):p.read_job(d,self.job,ex)
    def test_cleanup_failure_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);ex=self.fixture(d,self.job);ex['exit_confirmed']=False
            with self.assertRaises(ValueError):p.read_job(d,self.job,ex)
    def test_halt_checkpoint_retained(self):
        history=[]
        def fail(job):raise RuntimeError('runner failed')
        with self.assertRaises(RuntimeError):drive(self.contract['plan'],fail,history.append)
        self.assertEqual(history[-1]['status'],'halted_executor_error');self.assertEqual(len(history[-1]['dispatches']),1)
if __name__=='__main__':unittest.main()
