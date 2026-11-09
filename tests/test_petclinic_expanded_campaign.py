from copy import deepcopy
from pathlib import Path
import sys,unittest,tempfile,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import petclinic_expanded_campaign as p
import test_petclinic_terminal_campaign as old
import test_petclinic_prefix_outcomes_v3 as prefix_fixtures
from mixed_interface.campaign_v2 import drive
from petclinic_prefix_outcomes_v3 import pair_terminal

class PetClinicExpandedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batches=p.read(ROOT/p.CONTROL)['batches'];prefix_fixtures.PetClinicPrefixTests.setUpClass();cls.f=prefix_fixtures.PetClinicPrefixTests()
    def fixture(self,d,job,batch):
        helper=old.PetClinicCampaignTests();helper.setUp();ex=helper.fixture(d,job);run=d/'run';s=p.read(run/'summary.json')
        s.update(kind='petclinic_terminal_pair_v3',batch=batch,controls_sha256=p.CONTROL_SHA)
        shutil.copyfile(ROOT/p.CONTROL,run/'controls.json')
        for archived,live,key in [('executed_boundary_slice.mjs',p.RUNNER,'runner_sha256'),('petclinic_job_binding_v3.mjs',p.BINDING,'binding_sha256')]:
            shutil.copyfile(ROOT/live,run/archived);s[key]=p.sha(run/archived)
        p.write(run/'summary.json',s);return ex
    def test_exact_exposed_inventory_and_duplicate_control_accounting(self):
        all_ids=[cid for b in self.batches.values() for cid in b['candidate_ids']]
        self.assertEqual(len(all_ids),19);self.assertEqual(len(set(all_ids)),18)
        self.assertEqual(set(all_ids),{c['id'] for c in self.f.registry['candidates']})
        self.assertEqual(all_ids.count('owner_telephone_10'),2)
    def test_all_jobs_bind_to_batch_and_positive_reference(self):
        for name in self.batches:
            c=p.contract(name);pairs={r['pair_id']:r for r in c['plan']['schedule']['pairs']}
            for j in c['allowed_jobs']:self.assertEqual(p.validate_job(j,name)['id'],j['pair_id'])
            for pair in pairs.values():
                ref=pairs[pair['reference_control']];self.assertEqual(ref['intervention'],'route_only');self.assertEqual(ref['workflow_id'],pair['workflow_id'])
    def test_cross_batch_foreign_order_and_reset_changes_rejected(self):
        j=deepcopy(self.batches['pets']['plan']['schedule']['initial_jobs'][0])
        with self.assertRaises(ValueError):p.validate_job(j,'visits')
        with self.assertRaises(ValueError):p.validate_job(j,'foreign')
        j['branches'].reverse()
        with self.assertRaises(ValueError):p.validate_job(j,'pets')
    def test_qualified_control_evidence_reconstructs_with_new_binding(self):
        ids={'owner_telephone_10','owner_omit_firstName','pet_valid','pet_omit_name','visit_valid','visit_omit_date'}
        for batch,b in self.batches.items():
            for job in b['plan']['schedule']['initial_jobs']:
                if job['pair_id'] not in ids:continue
                with tempfile.TemporaryDirectory() as tmp:
                    d=Path(tmp);ex=self.fixture(d,job,batch);result=p.read_job(d,job,ex,batch)
                    self.assertIn(result['terminal']['kind'],('clean_observation','matched_rejection'))
    def test_wrong_recorded_batch_rejected(self):
        batch='owner_required';job=self.batches[batch]['plan']['schedule']['initial_jobs'][0]
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);ex=self.fixture(d,job,batch);s=p.read(d/'run/summary.json');s['batch']='owner_formats';p.write(d/'run/summary.json',s)
            with self.assertRaises(ValueError):p.read_job(d,job,ex,batch)
    def test_runner_failure_retains_checkpoint(self):
        saved=[]
        def fail(job):raise TimeoutError('fixture')
        with self.assertRaises(TimeoutError):drive(self.batches['pets']['plan'],fail,saved.append)
        self.assertEqual(saved[-1]['status'],'halted_executor_error');self.assertEqual(len(saved[-1]['dispatches']),1)
    def test_synthetic_format_batch_keeps_server_errors_unresolved_and_mismatch_repeats(self):
        plan=self.batches['owner_formats']['plan']
        def execute(job):
            cid=job['pair_id']
            if cid in ('owner_telephone_9','owner_telephone_11'):
                a=self.f.rejected(cid,500,'api_semantic');u=self.f.rejected(cid,500)
            elif cid in ('owner_city_whitespace','owner_first_name_hyphen'):
                a=self.f.accepted_variation(cid,'api_semantic');u=self.f.accepted_variation(cid,'fresh_ui',True)
            else:a=self.f.fixture.record(cid,'api_semantic');u=self.f.fixture.record(cid,'fresh_ui')
            return pair_terminal(job['job_id'],{'api':a,'ui':u},self.f.spec(cid),self.f.registry,cleanup_confirmed=True,evidence={'synthetic':'e'*64})['terminal']
        state=drive(plan,execute,lambda _:None)
        self.assertEqual(len(state['initial']),5);self.assertEqual(len(state['repeated']),12)
        results={r['pair_id']:r for r in state['repeat_summary']['pairs']}
        self.assertEqual(results['owner_first_name_hyphen']['status'],'stable_observations')
        for cid in ('owner_telephone_9','owner_telephone_11'):self.assertEqual(results[cid]['status'],'unresolved_execution')
        self.assertNotIn('owner_city_whitespace',results)
    def test_deadline_contract_is_bounded(self):
        for b in self.batches.values():self.assertEqual((b['pair_timeout_s'],b['campaign_timeout_s']),(120,900))
