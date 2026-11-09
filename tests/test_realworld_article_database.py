"""Committed article projections, exact selection, and diagnostic routing."""
from copy import deepcopy
import json,sqlite3,tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from realworld_article_db_state_v1 import project,backup,readback_paths,summarize_states,validate_selection
from test_realworld_identity_database import fixture


class ArticleDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.db=self.root/'active.sqlite3';fixture(self.db)
        self.before=project(self.db);self.payload={'title':'T'*151,'description':'description','body':'body','tagList':['pilot']}

    def insert(self,db):
        db.execute('INSERT INTO articles_article VALUES(13,?,?,?,?,7)',('new-title',self.payload['title'],'description','body'))

    def test_uncommitted_insert_invisible_then_commit_visible_in_independent_backup(self):
        writer=sqlite3.connect(self.db);self.insert(writer)
        try:
            self.assertEqual(backup(self.db,self.root/'before.sqlite3')['projection'],self.before)
            writer.commit()
        finally:writer.close()
        saved=backup(self.db,self.root/'after.sqlite3')
        self.assertEqual(len(saved['projection']['articles']),4)
        self.assertEqual(saved['projection']['articles'][-1]['title'],'T'*151)
        self.assertEqual(project(self.root/'after.sqlite3'),saved['projection'])

    def test_requested_insert_and_preservation_are_separate_measurements(self):
        with sqlite3.connect(self.db) as db:self.insert(db)
        after=project(self.db)
        states={'before':self.before,**{s:deepcopy(after) for s in ('immediate','after_stop','after_restart')}}
        value=summarize_states(states,self.payload)
        self.assertTrue(value['requested_article_fields_observed']);self.assertTrue(value['fixture_articles_preserved'])
        self.assertTrue(value['post_response_selected_state_survives_restart'])
        states['after_restart']['articles'][0]['body']='changed'
        value=summarize_states(states,self.payload)
        self.assertTrue(value['requested_article_fields_observed']);self.assertFalse(value['fixture_articles_preserved'])
        self.assertFalse(value['post_response_selected_state_survives_restart'])

    def test_absence_of_insert_is_not_imputed_from_http_status(self):
        states={s:deepcopy(self.before) for s in ('before','immediate','after_stop','after_restart')}
        value=summarize_states(states,self.payload)
        self.assertFalse(value['requested_article_fields_observed']);self.assertTrue(value['selected_state_unchanged'])
        self.assertNotIn('prefix_status',value)

    def test_removal_and_extra_rows_remain_observable(self):
        with sqlite3.connect(self.db) as db:
            self.insert(db);db.execute('DELETE FROM articles_article WHERE id=10')
            db.execute("INSERT INTO articles_article VALUES(14,'extra','extra','extra','extra',7)")
        after=project(self.db);states={'before':self.before,**{s:after for s in ('immediate','after_stop','after_restart')}}
        value=summarize_states(states,self.payload)
        self.assertEqual(len(value['new_article_rows']),2);self.assertFalse(value['fixture_articles_preserved'])
        self.assertFalse(value['requested_article_fields_observed'])

    def test_readback_paths_derive_from_snapshot_and_preserve_fixture_order(self):
        with sqlite3.connect(self.db) as db:self.insert(db)
        paths=readback_paths(['three','one','two'],project(self.db))
        self.assertEqual(paths,['/api/user','/api/articles?author=pilotresearch','/api/articles',
                               '/api/articles/three','/api/articles/one','/api/articles/two','/api/articles/new-title'])

    def test_exact_selection_rejects_changed_payload_policy_or_order(self):
        selection=json.loads((ROOT/'manifests/realworld-article-database-diagnostic-v1.json').read_bytes())
        validate_selection(ROOT,selection)
        for edit in (lambda s:s['cases'].reverse(),lambda s:s['cases'][2]['prefix_payload'].update(title='repaired'),
                     lambda s:s['cases'][2]['expectation'].update(outcome='reject')):
            changed=deepcopy(selection);edit(changed)
            with self.assertRaises(ValueError):validate_selection(ROOT,changed)

    def test_existing_snapshot_cannot_be_overwritten(self):
        path=self.root/'snapshot.sqlite3';backup(self.db,path)
        with self.assertRaises(ValueError):backup(self.db,path)

    def test_actual_pinned_schema_is_supported(self):
        m=json.loads((ROOT/'manifests/realworld-identity-db-fixture-failure.json').read_bytes())
        value=project(ROOT/m['evidence_directory']/'fixture.sqlite3')
        self.assertEqual(len(value['articles']),3)
        self.assertEqual(value['article_column_mapping'],{'description':'summary','body':'content'})
        self.assertNotIn('password',value['user'])
