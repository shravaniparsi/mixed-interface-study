"""Scoring exercised through independent real SQLite snapshots, without running Shlink."""
import copy,hashlib,pathlib,sqlite3,tempfile,unittest
from shlink_sqlite import snapshot
from shlink_database_score import creation,edit
class DatabaseScoring(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=pathlib.Path(self.tmp.name)/'fixture.sqlite';self.con=sqlite3.connect(self.db)
  self.con.executescript('''PRAGMA foreign_keys=ON;
CREATE TABLE api_keys(id INTEGER PRIMARY KEY);
INSERT INTO api_keys VALUES (1);
CREATE TABLE short_urls(id INTEGER PRIMARY KEY AUTOINCREMENT, original_url TEXT NOT NULL, long_url_hash BLOB NOT NULL, short_code TEXT UNIQUE, title TEXT, title_was_auto_resolved INTEGER NOT NULL, forward_query INTEGER NOT NULL, domain_id INTEGER, author_api_key_id INTEGER REFERENCES api_keys(id));
CREATE TABLE short_urls_in_tags(short_url_id INTEGER REFERENCES short_urls(id), tag_id INTEGER);
CREATE TABLE unrelated(id INTEGER PRIMARY KEY, value TEXT);
INSERT INTO unrelated VALUES(1,'unchanged');''');self.con.commit()
  self.body={'longUrl':'http://study-fixture:8089/ordinary','title':'Study ordinary title','tags':[],'forwardQuery':True};self.empty=snapshot(self.db)
  self.con.execute('INSERT INTO short_urls(original_url,long_url_hash,short_code,title,title_was_auto_resolved,forward_query,domain_id,author_api_key_id) VALUES (?,?,?,?,0,1,NULL,1)',(self.body['longUrl'],hashlib.sha256(self.body['longUrl'].encode()).digest(),'code',self.body['title']));self.con.commit();self.initial=snapshot(self.db)
 def tearDown(self):self.con.close();self.tmp.cleanup()
 def request(self,body):return dict(method='PATCH',path='/rest/v3/short-urls/code',body=body)
 def test_creation_and_sequence(self):
  creation(self.empty,self.initial,1,1,self.body)
  self.con.execute('UPDATE sqlite_sequence SET seq=99');self.con.commit()
  with self.assertRaises(ValueError):creation(self.empty,snapshot(self.db),1,1,self.body)
 def test_title_and_destination_edits(self):
  self.con.execute("UPDATE short_urls SET title='Edited'");self.con.commit();after=snapshot(self.db)
  edit(self.initial,after,1,1,{'/title':'Edited'},self.request({'title':'Edited'}))
  url='http://study-fixture:8089/edited';self.con.execute('UPDATE short_urls SET original_url=?,long_url_hash=?',(url,hashlib.sha256(url.encode()).digest()));self.con.commit()
  edit(after,snapshot(self.db),1,1,{'/longUrl':url},self.request({'longUrl':url}))
 def test_stale_hash_and_wrong_identity_refused(self):
  url='http://study-fixture:8089/edited';self.con.execute('UPDATE short_urls SET original_url=?',(url,));self.con.commit();after=snapshot(self.db)
  with self.assertRaises(ValueError):edit(self.initial,after,1,1,{'/longUrl':url},self.request({'longUrl':url}))
  with self.assertRaises(ValueError):edit(self.initial,after,2,1,{'/longUrl':url},self.request({'longUrl':url}))
 def test_unrelated_row_change_and_wrong_actor_refused(self):
  self.con.execute("UPDATE short_urls SET title='Edited'");self.con.execute("UPDATE unrelated SET value='changed'");self.con.commit();after=snapshot(self.db)
  for actor in [1,2]:
   with self.assertRaises(ValueError):edit(self.initial,after,1,actor,{'/title':'Edited'},self.request({'title':'Edited'}))
 def test_incomplete_snapshot_refused(self):
  after=copy.deepcopy(self.initial);del after['tables']['unrelated']
  with self.assertRaises(ValueError):edit(self.initial,after,1,1,{'/title':self.body['title']},self.request({'title':self.body['title']}))
if __name__=='__main__':unittest.main()
