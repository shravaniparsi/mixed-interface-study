import pathlib,sqlite3,tempfile,unittest
from shlink_sqlite import snapshot,backup
class SQLiteObservation(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.db=self.root/'database.sqlite'
  self.con=sqlite3.connect(self.db)
  self.con.executescript('''PRAGMA foreign_keys=ON;
CREATE TABLE parent(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE);
CREATE TABLE child(id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id), payload BLOB, amount REAL, note TEXT);
CREATE INDEX child_parent ON child(parent_id);
CREATE VIEW child_view AS SELECT * FROM child;
INSERT INTO parent(name) VALUES ('ordinary');
INSERT INTO child VALUES (1,1,X'00FF80',1.5,NULL);
PRAGMA user_version=7;''');self.con.commit()
 def tearDown(self):self.con.close();self.tmp.cleanup()
 def test_types_schema_and_backup(self):
  before=snapshot(self.db);r=before['tables']['child']['rows'][0]
  self.assertEqual([v['type'] for v in r],['integer','integer','blob','real','null'])
  self.assertEqual(r[2]['value'],'AP+A');self.assertEqual(before['pragmas']['user_version'],7)
  self.assertTrue(any(r[0]=='view' for r in before['schema']));self.assertIn('sqlite_sequence',before['tables'])
  target=self.root/'backup.sqlite';backup(self.db,target);self.assertEqual(snapshot(target),before)
  self.con.execute("UPDATE child SET note='later'");self.con.commit();self.assertNotEqual(snapshot(self.db),snapshot(target))
 def test_sequence_index_trigger_and_pragma_changes_observed(self):
  for sql in ["UPDATE sqlite_sequence SET seq=9 WHERE name='parent'",'DROP INDEX child_parent','CREATE TRIGGER audit_child AFTER UPDATE ON child BEGIN UPDATE parent SET name=name; END','PRAGMA user_version=8']:
   before=snapshot(self.db);self.con.execute(sql);self.con.commit();self.assertNotEqual(snapshot(self.db),before)
 def test_foreign_key_violation_refused(self):
  self.con.execute('PRAGMA foreign_keys=OFF');self.con.execute('UPDATE child SET parent_id=999');self.con.commit()
  with self.assertRaisesRegex(ValueError,'foreign_key_violations'):snapshot(self.db)
 def test_missing_database_and_unsafe_destination_refused(self):
  with self.assertRaises(ValueError):snapshot(self.root/'missing')
  self.assertFalse((self.root/'missing').exists())
  with self.assertRaises(ValueError):backup(self.db,self.db)
  link=self.root/'link';link.symlink_to(self.root/'missing')
  with self.assertRaises(ValueError):backup(self.db,link)
 def test_database_symlink_refused(self):
  p=self.root/'link';p.symlink_to(self.db)
  with self.assertRaises(ValueError):snapshot(p)
if __name__=='__main__':unittest.main()
