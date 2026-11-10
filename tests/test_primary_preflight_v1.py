"""Source, environment and freeze gates before any untouched dispatch."""
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import primary_preflight_v1 as p

class PreflightTests(unittest.TestCase):
    def test_smoke_is_exposed_and_primary_requires_actual_freeze(self):
        value=p.read(p.PREPARATION);p.sources(value);smoke=p.units('smoke');self.assertEqual(len(smoke),4)
        for unit in smoke:
            self.assertEqual(len(unit['jobs']),2)
            self.assertEqual(unit['jobs'][0]['runtime'],unit['jobs'][1]['runtime'])
            self.assertNotEqual(unit['jobs'][0]['attempt_id'],unit['jobs'][1]['attempt_id'])
        with tempfile.TemporaryDirectory() as temp,patch.object(p,'FREEZE',Path(temp)/'absent.json'):
            with self.assertRaises(FileNotFoundError):p.units('initial')
    def test_source_or_environment_changes_are_rejected(self):
        value=p.read(p.PREPARATION);altered=deepcopy(value);altered['source_sha256'][next(iter(altered['source_sha256']))]='0'*64
        with self.assertRaises(ValueError):p.sources(altered)
        folder=ROOT/'results/common-generated-ci-42775240013';v=p.read(folder/'runtime-versions.json');b=p.read(folder/'browser.json');boot=p.read(folder/'realworld-bootstrap.json')
        p.environment(value,'realworld',v,b,boot)
        alternate=ROOT/'results/primary-smoke-ci-42777715374/primary-smoke-smoke-petclinic_v4-42777715374-1'
        av=p.read(alternate/'runtime-versions.json')
        p.environment(value,'petclinic',av,p.read(alternate/'browser.json'),p.read(alternate/'petclinic-bootstrap.json'))
        av['platform']=v['platform']
        with self.assertRaises(ValueError):p.environment(value,'petclinic',av,p.read(alternate/'browser.json'),p.read(alternate/'petclinic-bootstrap.json'))
        for mode in ('image','node','browser','application'):
            x,y,z=deepcopy(v),deepcopy(b),deepcopy(boot)
            if mode=='image':x['runner']['ImageVersion']='foreign'
            elif mode=='node':x['node']['output']='foreign'
            elif mode=='browser':y['executable_sha256']='0'*64
            else:z['application_source_modified']=True
            with self.assertRaises(ValueError):p.environment(value,'realworld',x,y,z)
