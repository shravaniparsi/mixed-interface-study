import importlib.util,pathlib,tempfile,hashlib,unittest
spec=importlib.util.spec_from_file_location('build',pathlib.Path(__file__).with_name('build.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Verify(unittest.TestCase):
 def test_identity_and_adversarial_changes(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);p=root/'original';p.write_bytes(b'abc');p.chmod(0o644)
   tree=[dict(path='original',type='blob',mode='100644',size=3,sha=hashlib.sha1(b'blob 3\0abc').hexdigest())]
   self.assertEqual(m.verify(root,tree)['bytes'],3)
   p.write_bytes(b'abd')
   with self.assertRaisesRegex(ValueError,'blob_identity'):m.verify(root,tree)
   p.write_bytes(b'abc');p.chmod(0o755)
   with self.assertRaisesRegex(ValueError,'executable_mode'):m.verify(root,tree)
   p.chmod(0o644);(root/'extra').write_text('x')
   with self.assertRaisesRegex(ValueError,'complete_checkout'):m.verify(root,tree)
   (root/'extra').unlink();p.unlink();p.symlink_to('/dev/null')
   with self.assertRaisesRegex(ValueError,'regular_file'):m.verify(root,tree)
if __name__=='__main__':unittest.main()
