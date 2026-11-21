import importlib.util,pathlib,tempfile,hashlib,unittest,subprocess,json
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
 def test_unsafe_metadata(self):
  with tempfile.TemporaryDirectory() as d:
   for path,kind in [('../escape','blob'),('/absolute','blob'),('.git/config','blob'),('nested','commit')]:
    with self.assertRaises(ValueError):m.verify(pathlib.Path(d),[dict(path=path,type=kind)])
 def test_tree_identity_against_git(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);subprocess.run(['git','init','-q',d],check=True)
   (root/'a').mkdir();(root/'a'/'child').write_text('nested')
   (root/'a.txt').write_text('flat');(root/'run').write_text('executable');(root/'run').chmod(0o755)
   subprocess.run(['git','-C',d,'add','.'],check=True)
   expected=subprocess.check_output(['git','-C',d,'write-tree'],text=True).strip()
   raw=subprocess.check_output(['git','-C',d,'ls-tree','-r','-t','-z',expected]);rows=[]
   for item in raw.split(b'\0'):
    if not item:continue
    meta,path=item.split(b'\t');mode,kind,sha=meta.decode().split();rows.append(dict(path=path.decode(),mode=mode,type=kind,sha=sha))
   self.assertEqual(m.tree_identity(rows),expected)
   rows[-1]['sha']='0'*40
   self.assertNotEqual(m.tree_identity(rows),expected)
if __name__=='__main__':unittest.main()

