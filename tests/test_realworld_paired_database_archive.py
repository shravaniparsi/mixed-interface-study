import sys,json,unittest
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from verify_realworld_paired_database_archive import verify
from validate_identity_database_capture_v2 import validate


class PairedDatabaseArchiveTests(unittest.TestCase):
    def test_live_browser_and_committed_error_evidence_reconstruct(self):
        result=verify()
        self.assertEqual((result['pairs'],result['branches'],result['database_backups']),(4,8,20))
        rows={r['candidate_id']:r for r in result['results']}
        for cid in ('profile-bio-valid','profile-username-length60'):
            for channel,m in rows[cid]['measurements'].items():
                self.assertEqual(m['measurement']['continuation']['interface'],channel)
                self.assertTrue(all(m['measurement']['continuation']['checks'].values()))
                self.assertEqual(m['continuation_database']['projection']['bio'],'Bio after meaningful continuation.')
        failed=rows['profile-username-length61']
        self.assertEqual(failed['terminal_kind'],'missing_evidence')
        for m in failed['measurements'].values():
            self.assertEqual(m['measurement']['http']['status'],500)
            self.assertEqual(m['measurement']['persistence']['selected_change'],'requested_patch_observed')
            self.assertEqual(len(m['measurement']['persistence']['immediate']['projection']['username']),61)
            self.assertEqual(sum(r['status']==500 for r in m['measurement']['readbacks'].values()),4)
            self.assertEqual(m['measurement']['continuation']['state'],'not_executed_prefix_unsuccessful')
            self.assertEqual(m['requirement_policy']['outcome'],'unknown')
            self.assertFalse(m['restart_observed'])
    def test_actual_trace_cannot_move_backup_after_readbacks(self):
        manifest=json.loads((ROOT/'manifests/realworld-paired-database-integration.json').read_bytes())
        root=ROOT/manifest['evidence_directory'];summary_path=next((root/'initial-004/run').glob('*/summary.json'))
        summary=json.loads(summary_path.read_bytes());branch=summary['branches'][0]
        raw=json.loads((summary_path.parent/branch['evidence']).read_bytes())
        fixture=json.loads((summary_path.parent/'fixture-references.json').read_bytes())
        moved=[e for e in raw['trace'] if e['type'].startswith('database_snapshot_') and e['stage']=='after_prefix']
        raw['trace']=[e for e in raw['trace'] if e not in moved]+moved
        for i,event in enumerate(raw['trace']):event['sequence']=i+1
        with self.assertRaisesRegex(ValueError,'immediately after'):
            validate(raw,summary_path.parent/(branch['case_id']+'-database'),fixture)


if __name__=='__main__':unittest.main()
