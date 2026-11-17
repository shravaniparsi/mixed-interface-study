"""Synthetic adversarial reconstruction checks, not application observations."""
import json,tempfile,unittest
from pathlib import Path
import verify_benchmark_gitlab_members_controls_v3 as v
from test_benchmark_gitlab_members_verifier_v2 import MembershipEvidenceTests

class TripleEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='synthetic-members-v3-',dir=v.ROOT)
        self.root=Path(self.tmp.name)
        fixture=MembershipEvidenceTests();fixture.setUp();template=fixture.row
        jobs=[]
        for i,branch in enumerate(v.BRANCHES):
            folder=self.root/f'gitlab-members-control-v3-{branch}-{v.RUN}';folder.mkdir()
            row=json.loads(json.dumps(template));row.update(kind='benchmark_gitlab_members_control_v3',branch=branch)
            if branch=='native_native':row['project_form_before_submit']={'name':'llm_bulk_inference','path':'llm_bulk_inference','private':True,'readme':False,'sast':False}
            (folder/'members-control.json').write_text(json.dumps(row))
            for name,text in {'head.txt':v.HEAD,'version.txt':'15.7.5','image-identity.txt':'image@sha256:'+v.DIGEST,'readiness.json':'{"ready":true}','container-id.txt':str(i+1)*64}.items():(folder/name).write_text(text)
            jobs.append({'name':f'qualify ({branch})','status':'completed','conclusion':'success','startedAt':'2026-11-17T00:00:00Z','completedAt':'2026-11-17T00:01:00Z'})
        (self.root/'run.json').write_text(json.dumps({'databaseId':v.RUN,'headSha':v.HEAD,'status':'completed','jobs':jobs}))
    def tearDown(self):self.tmp.cleanup()
    def mutate(self,branch,callback):
        p=self.root/f'gitlab-members-control-v3-{branch}-{v.RUN}'/'members-control.json';row=json.loads(p.read_text());callback(row);p.write_text(json.dumps(row))
    def test_complete_synthetic_triple(self):
        r=v.reconstruct(self.root);self.assertTrue(r['ordinary_triple_qualified']);self.assertEqual(r['job_seconds'],180)
    def test_green_branches_with_mismatched_producers_do_not_qualify(self):
        def change(row):
            for key in ('producer_state','final_state'):row[key]['description']=''
        self.mutate('api_native',change)
        r=v.reconstruct(self.root);self.assertTrue(all(b['qualified'] for b in r['branches']));self.assertFalse(r['ordinary_triple_qualified'])
    def test_missing_native_form_readback_fails(self):
        self.mutate('native_native',lambda r:r.pop('project_form_before_submit'))
        self.assertFalse(v.reconstruct(self.root)['ordinary_triple_qualified'])
    def test_shared_container_identity_fails(self):
        for b in v.BRANCHES:(self.root/f'gitlab-members-control-v3-{b}-{v.RUN}'/'container-id.txt').write_text('a'*64)
        self.assertFalse(v.reconstruct(self.root)['ordinary_triple_qualified'])
    def test_missing_branch_observation_fails(self):
        (self.root/f'gitlab-members-control-v3-api_native-{v.RUN}'/'members-control.json').unlink()
        self.assertFalse(v.reconstruct(self.root)['ordinary_triple_qualified'])
if __name__=='__main__':unittest.main()
