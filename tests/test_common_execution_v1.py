"""Fresh common attempts with synthetic raw PetClinic fixtures, not application samples."""
from copy import deepcopy
from pathlib import Path
import tempfile,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import test_petclinic_timing_qualification_v1 as timed
from common_petclinic_adapter_v1 import Adapter
from common_petclinic_qualification_v1 import plan,drive
from mixed_interface.common_execution_v1 import execute,replay,read,write
from mixed_interface.common_bindings_v1 import bind_job
from mixed_interface.campaign_v2 import followups
from mixed_interface.terminal_outcomes import terminal,observation_signature

class FixtureAdapter(Adapter):
    def execute(self,d,bound):
        slot={'job':bound['runtime_job'],'batch':bound['runtime_context']['batch']}
        helper=timed.TimedQualificationTests();helper.fixture(d,slot)
        write(d/'dispatch.json',{'binding_sha256':bound['binding_sha256'],**slot})

class ExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        timed.TimedQualificationTests.setUpClass()
        cls.registry=read(ROOT/'manifests/common-bindings-v1.json')['registry'];cls.checked=plan()['preflight']
        cls.jobs=cls.checked['campaign']['schedule']['initial_jobs']
    def run_job(self,d,j,initial=None):return execute(d,self.registry,self.checked,j,FixtureAdapter(),'synthetic-test:1',initial)
    def replay_job(self,d,j,initial=None):return replay(Path(d)/j['job_id'],self.registry,self.checked,j,Adapter(),'synthetic-test:1',initial)

    def test_two_paths_reconstruct_and_preserve_original_semantics(self):
        with tempfile.TemporaryDirectory() as temp:
            values={}
            def run(j):values[j['job_id']]=self.run_job(temp,j);return values[j['job_id']]
            state=drive(run,lambda _:None)
            self.assertEqual(state['status'],'completed_bounded_diagnostic')
            for j in self.jobs:
                v=self.replay_job(temp,j);original=read(Path(temp)/j['job_id']/'runtime-observations.json')['terminal']
                self.assertEqual(v,values[j['job_id']]);self.assertEqual(observation_signature(v),observation_signature(original))
            self.assertEqual([v['kind'] for v in values.values()],['clean_observation','matched_rejection'])

    def test_existing_attempt_and_failed_attempt_cannot_be_replaced(self):
        class Broken(FixtureAdapter):
            def execute(self,d,b):write(d/'partial.json',{'synthetic':True});raise RuntimeError('injected interruption')
        with tempfile.TemporaryDirectory() as temp:
            job=self.jobs[0]
            with self.assertRaises(RuntimeError):execute(temp,self.registry,self.checked,job,Broken(),'synthetic-test:1')
            d=Path(temp)/job['job_id'];self.assertTrue((d/'failure.json').exists());self.assertTrue((d/'runtime/partial.json').exists())
            with self.assertRaises(FileExistsError):self.run_job(temp,job)
            with self.assertRaises(ValueError):self.replay_job(temp,job)

    def test_receipt_binding_terminal_raw_and_extra_file_tampering_rejected(self):
        for mode in ('binding','receipt','terminal','raw','extra','run'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temp:
                job=self.jobs[0];self.run_job(temp,job);d=Path(temp)/job['job_id']
                if mode=='extra':write(d/'extra.json',{})
                elif mode=='raw':(d/'runtime/runner-extra.log').write_text('added')
                else:
                    name={'binding':'binding.json','receipt':'receipt.json','terminal':'terminal.json','run':'started.json'}[mode]
                    value=read(d/name)
                    if mode=='binding':value['campaign_job']['repetition']=2
                    elif mode=='receipt':value['finished_monotonic_s']=float('inf')
                    elif mode=='terminal':value['outcome']['job_id']='foreign'
                    else:value['run_identity']='foreign:1'
                    write(d/name,value)
                with self.assertRaises(ValueError):self.replay_job(temp,job)

    def test_authorized_followups_execute_in_distinct_namespaces_with_outer_identity(self):
        # Synthetic trigger exercises orchestration only, not a claimed application mismatch.
        initial=[]
        for i,j in enumerate(self.jobs):
            o={'job_id':j['job_id'],'execution':'complete','prefix':'accepted','channel_discrepancy':i==1,
               'check_failure':i==1,'cleanup_confirmed':True,'observation_signature':{'synthetic_trigger':True}}
            initial.append(terminal(o,'completed_mismatch' if i else 'clean_observation',{'synthetic':'a'*64}))
        jobs=followups(self.checked['campaign'],initial)['jobs'];self.assertEqual(len(jobs),4)
        with tempfile.TemporaryDirectory() as temp:
            attempts=[]
            for j in jobs:
                value=self.run_job(temp,j,initial);self.assertEqual(value,self.replay_job(temp,j,initial))
                self.assertEqual(value['outcome']['job_id'],j['job_id'])
                d=Path(temp)/j['job_id'];attempts.append(read(d/'started.json')['attempt_id'])
                original=read(d/'runtime-observations.json')['terminal']
                self.assertEqual(original['outcome']['job_id'],bind_job(self.registry,self.checked,j,initial)['runtime_job']['job_id'])
                self.assertNotEqual(original['outcome']['job_id'],j['job_id'])
            self.assertEqual(len(set(attempts)),4)

    def test_unexpected_terminal_stops_qualification_without_repeat(self):
        calls=[]
        with tempfile.TemporaryDirectory() as temp:
            def run(j):
                calls.append(j);value=self.run_job(temp,j)
                # Only schedule behavior is synthetic; do not rewrite retained raw evidence.
                o=deepcopy(value['outcome']);o.update(channel_discrepancy=True,check_failure=True)
                return terminal(o,'completed_mismatch',value['evidence'])
            state=drive(run,lambda _:None)
            self.assertEqual(state['status'],'halted_terminal_outcome');self.assertEqual(len(calls),1)
