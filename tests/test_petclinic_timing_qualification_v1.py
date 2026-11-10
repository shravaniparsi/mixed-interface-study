"""Independent timing validation and exposed qualification scheduling contracts."""
from copy import deepcopy
from pathlib import Path
import sys,unittest,tempfile,shutil,json,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from petclinic_branch_cost_validation_v1 import validate_cost
from petclinic_timing_qualification_v1 import plan,drive
from validate_petclinic_timing_qualification_v1 import replay_schedule
import petclinic_timed_jobs_v4 as p
import test_petclinic_expanded_campaign as expanded

class TimedQualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        expanded.PetClinicExpandedTests.setUpClass();cls.helper=expanded.PetClinicExpandedTests()
    def fixture(self,d,slot):
        ex=self.helper.fixture(d,slot['job'],slot['batch']);run=d/'run';s=p.read(run/'summary.json')
        s.update(kind='petclinic_timed_pair_v4',common_browser_startup_s=.25)
        for archived,live,key in [('executed_boundary_slice.mjs',p.RUNNER,'runner_sha256'),('petclinic_branch_cost_v1.mjs','scripts/petclinic_branch_cost_v1.mjs','branch_cost_helper_sha256')]:
            shutil.copyfile(ROOT/live,run/archived);s[key]=p.sha(run/archived)
        for i,b in enumerate(s['branches']):
            raw=p.read(run/b['result']);raw.update(context_cleanup_confirmed=True);p.write(run/b['result'],raw)
            cost={'schema_version':1,'scope':'petclinic_branch_reset_through_raw_validation_and_owned_cleanup_v1',
                'candidate_id':raw['candidate_id'],'oracle':raw['oracle'],'started_monotonic_s':10+i*4,
                'finished_monotonic_s':13+i*4,'observed_elapsed_s':3,'branch_total_s':3,
                'raw_sha256':p.sha(run/b['result']),'measurement_status':'complete_interval','incomplete_reason':None}
            name=b['result'][:-5]+'-cost.json';p.write(run/name,cost);b.update(cost_record=name,branch_total_s=3,cost_status='complete_interval')
        p.write(run/'summary.json',s);return ex
    def result(self,d,slot,ex):return p.read_job(d,slot['job'],ex,slot['batch'])

    def test_all_six_pairs_timing_semantics_and_ledger_reconstruct(self):
        observations={}
        with tempfile.TemporaryDirectory() as temp:
            def execute(slot):
                d=Path(temp)/slot['slot_id'];d.mkdir();ex=self.fixture(d,slot);v=self.result(d,slot,ex)
                self.assertEqual(v['terminal']['kind'],slot['expected_kind']);self.assertEqual(set(v['branch_costs']),{'api','ui'})
                observations[slot['slot_id']]=v;return v
            report=drive(execute,lambda _:None)
            self.assertEqual(replay_schedule(observations,report),report)
            self.assertEqual(report['status'],'completed_bounded_diagnostic');self.assertEqual(len(observations),6)
            altered=deepcopy(report);altered['decisions'][0]['repeat_dispatched']=True
            with self.assertRaises(ValueError):replay_schedule(observations,altered)
            extra=deepcopy(observations);extra['cost-999']=extra['cost-000']
            with self.assertRaises(ValueError):replay_schedule(extra,report)

    def test_source_raw_cost_identity_cleanup_and_order_tampering_rejected(self):
        slot=plan()['slots'][0]
        for mode in ('source','hash','identity','duration','cleanup','missing','extra','overlap'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temp:
                d=Path(temp);ex=self.fixture(d,slot);run=d/'run';s=p.read(run/'summary.json');b=s['branches'][0];cp=run/b['cost_record'];c=p.read(cp)
                if mode=='source':(run/'petclinic_branch_cost_v1.mjs').write_text('altered')
                elif mode=='hash':c['raw_sha256']='0'*64;p.write(cp,c)
                elif mode=='identity':c['candidate_id']='foreign';p.write(cp,c)
                elif mode=='duration':c['branch_total_s']=1;p.write(cp,c)
                elif mode=='cleanup':
                    raw=p.read(run/b['result']);raw['context_cleanup_confirmed']=False;p.write(run/b['result'],raw);c['raw_sha256']=p.sha(run/b['result']);p.write(cp,c)
                elif mode=='missing':cp.unlink()
                elif mode=='extra':p.write(run/'foreign-cost.json',c)
                else:
                    second=run/s['branches'][1]['cost_record'];x=p.read(second);x.update(started_monotonic_s=11,finished_monotonic_s=14);p.write(second,x)
                with self.assertRaises((ValueError,FileNotFoundError)):self.result(d,slot,ex)

    def test_incomplete_clock_is_retained_without_completed_cost(self):
        base={'schema_version':1,'scope':'petclinic_branch_reset_through_raw_validation_and_owned_cleanup_v1','candidate_id':'x','oracle':'fresh_ui',
            'started_monotonic_s':2,'finished_monotonic_s':None,'observed_elapsed_s':None,'branch_total_s':None,'raw_sha256':None,
            'measurement_status':'incomplete_interval','incomplete_reason':'end_not_observed'}
        self.assertEqual(validate_cost(base),base)
        changed=deepcopy(base);changed['branch_total_s']=0
        with self.assertRaises(ValueError):validate_cost(changed)
        for clock in (True,float('nan'),float('inf'),-1):
            changed=deepcopy(base);changed['started_monotonic_s']=clock
            with self.assertRaises(ValueError):validate_cost(changed)

    def test_node_written_complete_and_cleanup_incomplete_records_validate_in_python(self):
        script="""import {beginBranch,finishBranch} from './scripts/petclinic_branch_cost_v1.mjs';
const id={candidate_id:'cross-language-fixture',oracle:'fresh_ui'};
console.log(JSON.stringify([true,false].map(ok=>{const bytes=Buffer.from(JSON.stringify({...id,status:'runner_or_assertion_failure',backend_cleanup:{confirmed:true},context_cleanup_confirmed:ok}));return {raw:bytes.toString(),cost:finishBranch(beginBranch(id,()=>10),bytes,()=>13.25)};})));"""
        values=json.loads(subprocess.check_output(['node','--input-type=module','-e',script],cwd=ROOT,text=True))
        for value in values:validate_cost(value['cost'],value['raw'].encode())
        self.assertEqual([v['cost']['branch_total_s'] for v in values],[3.25,None])

    def test_unexpected_control_result_stops_without_retries(self):
        observations={}
        with tempfile.TemporaryDirectory() as temp:
            def execute(slot):
                d=Path(temp)/slot['slot_id'];d.mkdir();ex=self.fixture(d,slot);v=self.result(d,slot,ex)
                if slot['slot_id']=='cost-001':
                    v['terminal']['kind']='unresolved_policy';v['terminal']['outcome'].update(check_failure=False,channel_discrepancy=False)
                observations[slot['slot_id']]=v;return v
            report=drive(execute,lambda _:None)
            self.assertEqual(report['status'],'halted_terminal_outcome');self.assertEqual(len(observations),2)
            self.assertEqual(replay_schedule(observations,report),report)
