"""Immutable live archive replay and corruption rejection."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from verify_realworld_article_database_archive import verify,read,MANIFEST


class ArticleDatabaseArchiveTests(unittest.TestCase):
    def test_live_creation_commit_survives_failed_response_and_restart(self):
        result=verify();case=result['cases'][-1]
        self.assertEqual(case['prefix_status'],500)
        self.assertEqual((case['before_article_count'],case['immediate_article_count']),(3,4))
        self.assertTrue(case['post_response_selected_state_survives_restart'])
        for stage in ('readback','restart_readback'):
            statuses=case['readback_statuses'][stage]
            self.assertEqual(statuses['/api/user'],200)
            self.assertEqual(statuses['/api/articles'],500)
            self.assertEqual(statuses['/api/articles?author=pilotresearch'],500)
            self.assertEqual(list(statuses.values()).count(500),3)

    def test_changed_backup_digest_fails_before_replay(self):
        manifest=deepcopy(read(MANIFEST))
        key=next(k for k in manifest['files_sha256'] if k.endswith('.sqlite3'))
        manifest['files_sha256'][key]='0'*64
        with self.assertRaises(ValueError):verify(manifest)
