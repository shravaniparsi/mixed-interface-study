import os,pathlib,sqlite3,tempfile,unittest
from shlink_files import inventory,compare_non_database
class StateFiles(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);(self.root/'data').mkdir();(self.root/'config').mkdir();self.db=self.root/'data/database.sqlite';con=sqlite3.connect(self.db);con.execute('CREATE TABLE example(id INTEGER)');con.commit();con.close();(self.root/'config/generated.php').write_text('ordinary fixture')
 def tearDown(self):self.tmp.cleanup()
 def test_full_inventory_and_declared_database_partition(self):
  value=inventory(self.root);self.assertEqual(len(value['database_physical']),1);self.assertTrue(any(r['path']=='config/generated.php' and 'sha256' in r for r in value['files']))
  before=value;con=sqlite3.connect(self.db);con.execute('INSERT INTO example VALUES(1)');con.commit();con.close();after=inventory(self.root)
  self.assertNotEqual(before['database_physical'],after['database_physical']);compare_non_database(before,after)
 def test_unrelated_content_mode_and_creation_changes(self):
  for kind in ['content','mode','new_file']:
   before=inventory(self.root)
   if kind=='content':(self.root/'config/generated.php').write_text('changed')
   elif kind=='mode':(self.root/'config/generated.php').chmod(0o700)
   else:(self.root/'data/unexpected').write_bytes(b'new')
   with self.subTest(kind=kind),self.assertRaises(ValueError):compare_non_database(before,inventory(self.root))
 def test_symlink_fifo_and_missing_db_refused(self):
  path=self.root/'data/extra';path.symlink_to(self.root/'config')
  with self.assertRaises(ValueError):inventory(self.root)
  path.unlink();os.mkfifo(path)
  with self.assertRaises(ValueError):inventory(self.root)
  path.unlink();self.db.unlink()
  with self.assertRaises(ValueError):inventory(self.root)
if __name__=='__main__':unittest.main()
