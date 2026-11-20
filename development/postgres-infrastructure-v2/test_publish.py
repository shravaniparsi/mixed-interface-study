import os,pathlib,tempfile,unittest
from publish import publish
class Tests(unittest.TestCase):
 def test_identity_and_private_modes(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t);s=p/'source';s.mkdir();(s/'result.json').write_text('{"status":"synthetic"}');r=publish(s,p/'public',os.getuid(),os.getgid());self.assertEqual((p/'public/result.json').read_bytes(),(s/'result.json').read_bytes());self.assertEqual((p/'public/result.json').stat().st_mode&0o777,0o600);self.assertEqual((p/'public').stat().st_mode&0o777,0o700);self.assertEqual(len(r['files']),1)
 def test_unknown_file_fails_before_publication(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t);s=p/'source';s.mkdir();(s/'database.dump').write_bytes(b'not public')
   with self.assertRaises(AssertionError):publish(s,p/'public',os.getuid(),os.getgid())
   self.assertFalse((p/'public').exists())
 def test_symlink_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t);s=p/'source';s.mkdir();(p/'private').write_text('not public');(s/'result.json').symlink_to(p/'private')
   with self.assertRaises(AssertionError):publish(s,p/'public',os.getuid(),os.getgid())
if __name__=='__main__':unittest.main(verbosity=2)
