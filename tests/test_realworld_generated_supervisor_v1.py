"""Complete raw-trace fixtures and actual bounded synthetic worker lifecycles."""
from copy import deepcopy
from pathlib import Path
import json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from generated_positive_fixture_v1 import complete
from realworld_generated_bindings_v1 import plan
from realworld_generated_terminal_v1 import compare,classify
from realworld_generated_loader_v1 import load,sha
from realworld_generated_supervisor_v1 import run_branch
from test_realworld_generated_loader_v1 import bundle,put,seal


class GeneratedSupervisorTests(unittest.TestCase):
    def pair(self,producer):
        branches={}
        for channel in ('api','ui'):
            raw,run,spec=complete(producer,channel);branches[channel]=(raw,run)
        job=next(j for j in plan()['jobs'] if spec['case_id'] in j['pair']['case_ids'].values())
        return job,branches

    def test_complete_raw_traces_on_all_four_routes(self):
        for producer in ('api','ui'):
            job,branches=self.pair(producer)
            value=compare(job,branches,{'synthetic':'0'*64})
            self.assertEqual(value['terminal']['kind'],'clean_observation')
            self.assertTrue(all(value['comparability'].values()))

    def test_positive_bundle_reconstructs_and_resealed_bad_trace_does_not(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bundle(root);job,branches=self.pair('api')
            for channel,(raw,run) in branches.items():
                run['reset_sha256']=sha(root/'fixture.bin');put(root/channel/'raw.json',raw);put(root/channel/'run.json',run)
            seal(root);self.assertEqual(load(root)['terminal']['kind'],'clean_observation')
            raw=branches['ui'][0];e=next(e for e in raw['trace'] if e['type']=='ui_response');e['capture_request_id']='foreign'
            put(root/'ui/raw.json',raw);seal(root)
            self.assertEqual(load(root)['terminal']['kind'],'missing_evidence')

    def test_missing_write_wrong_parent_and_changed_reset_fail_closed(self):
        for mode in ('write','parent','reset'):
            job,branches=self.pair('api');raw,run=branches['ui']
            if mode=='write':raw['trace']=[e for e in raw['trace'] if e.get('method')!='PUT']
            elif mode=='parent':
                e=next(e for e in raw['trace'] if e['type']=='ui_response' and e.get('method')=='GET' and '/created' in e.get('path',''));e['data']['article']['slug']='wrong'
            else:run['reset_sha256']='b'*64
            self.assertNotEqual(compare(job,branches,{'synthetic':'0'*64})['terminal']['kind'],'clean_observation')

    def test_real_synthetic_worker_success_failure_and_timeout(self):
        job,branches=self.pair('api')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'input';source.mkdir();(source/'fixture.bin').write_bytes(b'explicit synthetic reset')
            put(source/'raw.json',branches['api'][0])
            for mode,expected in [('success','validated_synthetic_branch'),('failure','worker_failure'),('timeout','case_timeout')]:
                value=run_branch(job,'api',source,root/mode,mode=mode,deadline_s=1 if mode=='timeout' else 5)
                self.assertEqual(value['status'],expected)
                self.assertTrue(value['cleanup']['exit_confirmed'])
                self.assertGreater(value['branch_total_s'],0)
                self.assertAlmostEqual(value['branch_total_s'],value['branch_finished_monotonic']-value['branch_started_monotonic'])
                self.assertFalse(value['runtime_dispatch_qualified'])
                self.assertEqual((root/mode/'reset.bin').read_bytes(),(source/'fixture.bin').read_bytes())
            with self.assertRaises(FileExistsError):run_branch(job,'api',source,root/'success')
