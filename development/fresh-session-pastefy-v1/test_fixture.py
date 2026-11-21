import json,pathlib,sqlite3,stat,tempfile,unittest
from fixture import seed
class Fixture(unittest.TestCase):
 def database(self,root):
  p=pathlib.Path(root)/'study.sqlite';c=sqlite3.connect(p)
  c.executescript('CREATE TABLE pastefy_users(id TEXT PRIMARY KEY,name TEXT,unique_name TEXT,email TEXT,auth_id TEXT,auth_provider TEXT,type TEXT,created_at TEXT,updated_at TEXT);CREATE TABLE pastefy_auth_keys(id INTEGER PRIMARY KEY AUTOINCREMENT,key TEXT,user_id TEXT REFERENCES pastefy_users(id),type TEXT,created_at TEXT,updated_at TEXT);CREATE TABLE pastefy_pastes(id INTEGER PRIMARY KEY,title TEXT);');c.close();return p
 def test_seed_private_identity_only_and_refuse_repeat(self):
  with tempfile.TemporaryDirectory() as tmp:
   db=self.database(tmp);out=pathlib.Path(tmp)/'credentials.json';result=seed(db,out);self.assertEqual(result['application_records_created'],0);self.assertEqual(stat.S_IMODE(out.stat().st_mode),0o600);self.assertEqual(len(json.loads(out.read_text())['api_key']),60)
   with sqlite3.connect(db) as c:self.assertEqual(c.execute('SELECT count(*) FROM pastefy_pastes').fetchone()[0],0)
   with self.assertRaises(ValueError):seed(db,pathlib.Path(tmp)/'other.json')
 def test_existing_application_data_refused(self):
  with tempfile.TemporaryDirectory() as tmp:
   db=self.database(tmp)
   with sqlite3.connect(db) as c:c.execute('INSERT INTO pastefy_pastes VALUES(1,"existing")')
   with self.assertRaises(ValueError):seed(db,pathlib.Path(tmp)/'credentials.json')
if __name__=='__main__':unittest.main()
