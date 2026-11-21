import json,pathlib,tempfile,unittest
from verify_dependencies import verify_frontend,verify_maven
class Dependencies(unittest.TestCase):
 def test_frontend_rejects_lock_or_integrity_change_and_missing_required(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp);pkg={'version':'1.0.0','resolved':'https://example.test/x','integrity':'sha512-example'};lock={'packages':{'':{},'node_modules/x':pkg}}
   for n in ['original','final','installed']:(p/n).write_text(json.dumps(lock))
   self.assertEqual(verify_frontend(p/'original',p/'final',p/'installed')['packages_checked'],1)
   for altered in [{'packages':{}},{'packages':{'node_modules/x':dict(pkg,integrity='different')}},{'packages':{'node_modules/y':pkg}}]:
    (p/'installed').write_text(json.dumps(altered))
    with self.assertRaises(ValueError):verify_frontend(p/'original',p/'final',p/'installed')
   (p/'final').write_text('{}')
   with self.assertRaises(ValueError):verify_frontend(p/'original',p/'final',p/'original')
 def test_vendor_resolution_requires_identical_bytes(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp);v=p/'vendor';a=p/'resolved';v.mkdir();a.mkdir();(v/'x.jar').write_bytes(b'original');(a/'x.jar').write_bytes(b'original')
   self.assertEqual(len(verify_maven(v,a)),1)
   (a/'x.jar').write_bytes(b'changed')
   with self.assertRaises(ValueError):verify_maven(v,a)
   (a/'x.jar').unlink()
   with self.assertRaises(ValueError):verify_maven(v,a)
if __name__=='__main__':unittest.main()
