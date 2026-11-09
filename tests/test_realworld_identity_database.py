import sys,sqlite3,tempfile,unittest,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from realworld_identity_db_state_v1 import project,backup,connect
from run_realworld_identity_database_diagnostic import clean


def fixture(path):
    db=sqlite3.connect(path)
    db.executescript('''PRAGMA foreign_keys=ON;
    CREATE TABLE accounts_user(id INTEGER PRIMARY KEY,username TEXT,email TEXT,password TEXT,bio TEXT,image TEXT);
    CREATE TABLE articles_article(id INTEGER PRIMARY KEY,slug TEXT,title TEXT,description TEXT,body TEXT,author_id INTEGER REFERENCES accounts_user(id));
    INSERT INTO accounts_user VALUES(7,'pilotresearch','pilot@example.com','synthetic-hash','baseline',NULL);
    INSERT INTO articles_article VALUES(10,'one','one','description','body',7),(11,'two','two','description','body',7),(12,'three','three','description','body',7);
    ''');db.commit();db.close()


class IdentityDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.d=Path(self.tmp.name);self.db=self.d/'active.sqlite3';fixture(self.db)
    def test_projection_binds_ids_and_omits_credentials(self):
        value=project(self.db);self.assertEqual(value['user']['id'],7);self.assertEqual(len(value['articles']),3)
        self.assertNotIn('password',value['user']);self.assertEqual(value['read_uncommitted'],0);self.assertEqual(value['query_only'],1)
    def test_read_connection_cannot_mutate_fixture(self):
        db=connect(self.db)
        try:
            with self.assertRaises(sqlite3.OperationalError):db.execute("UPDATE accounts_user SET username='changed'")
        finally:db.close()
        self.assertEqual(project(self.db)['user']['username'],'pilotresearch')
    def test_uncommitted_write_is_invisible_but_committed_write_survives_reopen(self):
        writer=sqlite3.connect(self.db);writer.execute("UPDATE accounts_user SET username=?",('u'*61,))
        try:
            before=backup(self.db,self.d/'uncommitted.sqlite3');self.assertEqual(before['projection']['user']['username'],'pilotresearch')
            writer.commit()
        finally:writer.close()
        after=backup(self.db,self.d/'committed.sqlite3');self.assertEqual(after['projection']['user']['username'],'u'*61)
        self.assertEqual(project(self.d/'committed.sqlite3'),after['projection'])
    def test_snapshot_bytes_are_not_overwritten(self):
        destination=self.d/'snapshot.sqlite3';first=backup(self.db,destination)
        with self.assertRaises(ValueError):backup(self.db,destination)
        self.assertEqual(project(destination),first['projection'])
    def test_ambiguous_user_tables_are_rejected(self):
        with sqlite3.connect(self.db) as db:db.execute('CREATE TABLE other_user AS SELECT * FROM accounts_user')
        with self.assertRaisesRegex(ValueError,'Ambiguous'):project(self.db)
    def test_wrong_account_or_article_owner_is_rejected(self):
        with sqlite3.connect(self.db) as db:db.execute('UPDATE articles_article SET author_id=9 WHERE id=10')
        with self.assertRaisesRegex(ValueError,'ownership'):project(self.db)
    def test_missing_article_population_is_rejected(self):
        with sqlite3.connect(self.db) as db:db.execute('DELETE FROM articles_article WHERE id=10')
        with self.assertRaisesRegex(ValueError,'population'):project(self.db)
    def test_source_database_is_unchanged_by_backup(self):
        before=self.db.read_bytes();backup(self.db,self.d/'snapshot.sqlite3');self.assertEqual(self.db.read_bytes(),before)
    def test_redaction_keeps_username_but_excludes_login_material(self):
        value=clean({'user':{'username':'u'*61,'token':'secret','password':'secret'},'authorization':'secret'})
        self.assertEqual(value['user']['username'],'u'*61);self.assertNotIn('secret',json.dumps(value))
    def test_selection_matches_three_existing_registered_cases(self):
        selection=json.loads((ROOT/'manifests/realworld-identity-database-diagnostic-v1.json').read_bytes());registry=json.loads((ROOT/'manifests/realworld-boundary-registry-v1.json').read_bytes())
        self.assertEqual([c['candidate_id'] for c in selection['cases']],['profile-username-null','profile-username-length60','profile-username-length61'])
        for c in selection['cases']:self.assertEqual(c,next(x for x in registry['cases'] if x['candidate_id']==c['candidate_id']))
