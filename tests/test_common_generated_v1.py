"""Historical raw replay tests, explicitly not fresh application evidence."""
from pathlib import Path
from copy import deepcopy
import sys,tempfile,shutil,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from common_generated_adapter_v1 import Adapter
from common_generated_qualification_v1 import plan,drive
from mixed_interface.common_bindings_v1 import bind_job
from mixed_interface.common_execution_v1 import read,write,sha,translate
from mixed_interface.terminal_outcomes import observation_signature

class CommonGeneratedTests(unittest.TestCase):
    def test_both_qualified_loaders_preserve_semantics_with_different_outer_identity(self):
        registry=read(ROOT/'manifests/common-bindings-v1.json')['registry'];checked=plan()['preflight'];values={}
        for job in checked['campaign']['schedule']['initial_jobs']:
            bound=bind_job(registry,checked,job);profile=registry['profiles'][bound['runtime_profile']]
            m=read(ROOT/profile['evidence_manifest']);folder='realworld-generated-v2' if bound['runtime_profile']=='generated_control_v2' else 'realworld-generated-v3'
            archive=ROOT/m['archive_root']/folder;original=archive/bound['runtime_job']['job_id']
            with tempfile.TemporaryDirectory() as tmp:
                d=Path(tmp)/'fixture';shutil.copytree(original,d)
                write(d/'dispatch.json',{'binding_sha256':bound['binding_sha256'],'job':bound['runtime_job'],'profile':bound['runtime_profile']})
                adapter=Adapter(bound['runtime_profile'],fixture_sha=sha(archive/'fixture.sqlite3'))
                loaded=adapter.load(d,bound);self.assertEqual(loaded,read(original/'observations.json'))
                outer=translate(bound,loaded,'a'*64);values[job['job_id']]=outer
                self.assertNotEqual(outer['outcome']['job_id'],loaded['terminal']['outcome']['job_id'])
                self.assertEqual(observation_signature(outer),observation_signature(loaded['terminal']))
                dispatch=read(d/'dispatch.json');dispatch['profile']='foreign';write(d/'dispatch.json',dispatch)
                with self.assertRaises(ValueError):adapter.load(d,bound)
        state=drive(lambda j:values[j['job_id']],lambda _:None)
        self.assertEqual(state['status'],'completed_bounded_diagnostic');self.assertEqual(len(state['completed']),2)
    def test_missing_or_foreign_runtime_identity_cannot_be_mapped(self):
        registry=read(ROOT/'manifests/common-bindings-v1.json')['registry'];checked=plan()['preflight']
        bound=bind_job(registry,checked,checked['campaign']['schedule']['initial_jobs'][0])
        m=read(ROOT/'manifests/realworld-generated-runtime-integration.json')
        loaded=read(ROOT/m['archive_root']/'realworld-generated-v2/generated-000/observations.json')
        loaded['terminal']['outcome']['job_id']='foreign'
        with self.assertRaises(ValueError):translate(bound,loaded,'a'*64)
