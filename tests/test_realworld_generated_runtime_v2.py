"""Synthetic runtime envelopes exercise the new loader without application execution."""
from pathlib import Path
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from generated_positive_fixture_v1 import complete
from realworld_generated_runtime_v2 import jobs,branch
from realworld_generated_loader_v1 import sha
from test_realworld_generated_loader_v1 import put

class RuntimeLoaderTests(unittest.TestCase):
    def fixture(self,d,producer,channel):
        raw,run,spec=complete(producer,channel);job=next(j for j in jobs() if spec['case_id'] in j['pair']['case_ids'].values())
        put(d/'case.json',spec);put(d/'observation.json',raw);(d/'reset.sqlite3').write_bytes(b'synthetic reset bytes')
        h=sha(d/'reset.sqlite3');put(d/'reset.json',{'sha256':h,'independent_offline_reset':True})
        run.update(reset_sha256=h,raw_sha256=sha(d/'observation.json'),timed_out=False,started_monotonic=1.,finished_monotonic=2.,branch_total_s=1.)
        put(d/'run.json',run);put(d/'execution.json',{'exit_confirmed':True,'returncode':0,'errors':[]})
        for name in ('cleanup.json','parent-browser-cleanup.json'):put(d/name,{'ok':True,'worker_process_cleanup_errors':[]})
        put(d/'port-check.json',{'backend_port_closed':True})
        return job,h

    def test_all_four_routes_validate(self):
        for producer in ('api','ui'):
            for channel in ('api','ui'):
                with tempfile.TemporaryDirectory() as name:
                    d=Path(name);job,h=self.fixture(d,producer,channel);raw,run=branch(d,job,channel,h)
                    self.assertEqual(raw['route'],[producer,channel])

    def test_reset_cleanup_time_and_raw_tampering_rejected(self):
        import json
        for mode in ('reset','cleanup','time','raw','timeout'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as name:
                d=Path(name);job,h=self.fixture(d,'api','ui')
                if mode=='reset':(d/'reset.sqlite3').write_bytes(b'foreign')
                elif mode=='cleanup':put(d/'parent-browser-cleanup.json',{'ok':False})
                elif mode=='raw':put(d/'observation.json',{})
                else:
                    run=json.loads((d/'run.json').read_text());run['branch_total_s' if mode=='time' else 'timed_out']=99 if mode=='time' else True;put(d/'run.json',run)
                with self.assertRaises(ValueError):branch(d,job,'ui',h)

    def test_selection_excludes_every_mutation(self):
        self.assertEqual(len(jobs()),2)
        self.assertEqual({j['pair']['producer_interface'] for j in jobs()},{'api','ui'})
        self.assertTrue(all(j['pair']['intervention']=='route_only' for j in jobs()))
