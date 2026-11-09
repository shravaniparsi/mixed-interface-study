import sys,unittest,json,shutil,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from validate_realworld_identity_database_diagnostic import validate


class IdentityDatabaseArchiveTests(unittest.TestCase):
    def setUp(self):self.archive=ROOT/'results/realworld-identity-database-ci-20261109'
    def test_archived_failed_response_has_restart_persistent_committed_username(self):
        value=validate(self.archive);cases={c['candidate_id']:c for c in value['cases']}
        failed=cases['profile-username-length61'];self.assertEqual(failed['prefix_status'],500)
        self.assertTrue(failed['requested_username_observed']);self.assertTrue(failed['post_response_state_survives_restart']);self.assertEqual(len(failed['immediate_username']),61)
        self.assertTrue(cases['profile-username-null']['selected_state_unchanged']);self.assertEqual(cases['profile-username-length60']['prefix_status'],200)
    def test_snapshot_cannot_be_reordered_to_after_readbacks(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)/'archive';shutil.copytree(self.archive,d)
            p=d/'report.json';report=json.loads(p.read_bytes());trace=report['cases'][2]['trace']
            i=next(i for i,e in enumerate(trace) if e['type']=='database_snapshot' and e['stage']=='immediate')
            event=trace.pop(i);trace.insert(i+2,event)
            for i,e in enumerate(trace):e['sequence']=i+1
            p.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError,'event order'):validate(d)
