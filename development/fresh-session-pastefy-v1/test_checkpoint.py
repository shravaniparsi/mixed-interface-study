import pathlib,sqlite3,subprocess,sys,tempfile,unittest
from checkpoint import State
class Checkpoints(unittest.TestCase):
 def fixture(self,parent):
  state=State(pathlib.Path(parent)/'state');con=sqlite3.connect(state.live/'study.sqlite');con.execute('CREATE TABLE records(id INTEGER PRIMARY KEY, title TEXT, body BLOB)');con.execute('INSERT INTO records VALUES(1,?,?)',('ordinary',b'\x00\xff'));con.commit();con.close();(state.live/'asset').write_text('original');return state
 def test_restore_all_rows_and_extra_files(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=self.fixture(tmp);saved=s.checkpoint();con=sqlite3.connect(s.live/'study.sqlite');con.execute('UPDATE records SET title=NULL');con.commit();con.close();(s.live/'extra').write_text('extra');(s.live/'asset').unlink();s.restore();self.assertEqual(s.observe(s.live),saved);self.assertFalse((s.live/'extra').exists());s.restore()
 def test_live_writer_refused(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=self.fixture(tmp);p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)']);s.track(p)
   try:
    with self.assertRaises(ValueError):s.checkpoint()
   finally:p.terminate();p.wait(timeout=3)
   s.checkpoint()
 def test_tampered_checkpoint_and_symlink_refused(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=self.fixture(tmp);s.checkpoint();(s.base/'checkpoint'/'asset').write_text('changed')
   with self.assertRaises(ValueError):s.restore()
   (s.live/'link').symlink_to(s.base/'checkpoint'/'asset')
   with self.assertRaises(ValueError):s.observe(s.live)
if __name__=='__main__':unittest.main()
