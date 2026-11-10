"""Historical raw-fixture checks of every native loader, not fresh observations."""
from pathlib import Path
from copy import deepcopy
import sys,tempfile,shutil,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from primary_catalog_v1 import templates
from primary_runtime_v1 import load
from primary_attempt_v1 import normalized
from mixed_interface.common_execution_v1 import read,write,sha
from mixed_interface.primary_batches_v1 import attempt

ARCHIVES={
 'rw_expanded':'results/realworld-expanded-integration-ci-20261109',
 'rw_field':'results/realworld-field-integration-ci-20261109',
 'rw_rejection':'results/realworld-rejection-integration-ci-20261109',
 'rw_identity':'results/realworld-paired-database-ci-20261109',
 'rw_legacy':'results/realworld-reference-runtime-ci-20261110/realworld-legacy-v10',
 'quartz_v2':'results/quartz-terminal-integration-ci-20261109'}

class NativeRuntimeTests(unittest.TestCase):
    def test_all_native_profiles_and_singletons_reconstruct_without_semantic_promotion(self):
        bindings=templates()['bindings']
        for profile,folder in ARCHIVES.items():
            with self.subTest(profile=profile),tempfile.TemporaryDirectory() as tmp:
                b=next(b for b in bindings if b['runtime']['profile']==profile)
                a=attempt(b,1,control=True);r=a['runtime'];original=ROOT/folder/r['job']['job_id'];d=Path(tmp)/'runtime';shutil.copytree(original,d)
                if profile!='quartz_v2':
                    registry=r.get('registry') or read(ROOT/r['registry_path']);write(d/'registry.json',registry)
                    write(d/'dispatch.json',{'attempt_id':a['attempt_id'],'job':r['job'],'command':['historical-fixture']})
                else:
                    dispatch=read(d/'dispatch.json');dispatch['attempt_id']=a['attempt_id'];write(d/'dispatch.json',dispatch)
                loaded=load(d,a);value=normalized(a,loaded,{'synthetic_receipt':True})
                self.assertEqual(value['terminal']['kind'],'clean_observation');self.assertEqual(value['terminal']['outcome']['job_id'],a['attempt_id'])
                self.assertEqual(set(value['branch_total_s']),{'api','ui'})
                self.assertEqual(value['terminal']['outcome']['observation_signature'],loaded['runtime_result']['terminal']['outcome']['observation_signature'])
        for b in [b for b in bindings if b['entry_kind']=='singleton']:
            with self.subTest(singleton=b['entry']['pair_id']),tempfile.TemporaryDirectory() as tmp:
                a=attempt(b,1);r=a['runtime'];d=Path(tmp)/'runtime';shutil.copytree(ROOT/ARCHIVES['rw_legacy']/r['job']['job_id'],d)
                write(d/'registry.json',r['registry']);write(d/'dispatch.json',{'attempt_id':a['attempt_id'],'job':r['job'],'command':['historical-fixture']})
                value=normalized(a,load(d,a),{'synthetic_receipt':True});self.assertFalse(value['paired_comparison_eligible']);self.assertNotIn('terminal',value)
