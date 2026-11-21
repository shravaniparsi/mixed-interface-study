import importlib.util,json,pathlib,subprocess,tempfile,unittest
spec=importlib.util.spec_from_file_location('source_check',pathlib.Path(__file__).with_name('source_check.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class SourceCheck(unittest.TestCase):
 def fixture(self,root):
  subprocess.run(['git','init','-q',str(root)],check=True)
  (root/'a').mkdir();(root/'a'/'x').write_bytes(b'nested');(root/'a.txt').write_bytes(b'flat');(root/'run').write_bytes(b'executable');(root/'run').chmod(0o755)
  subprocess.run(['git','-C',str(root),'add','.'],check=True)
  sha=subprocess.check_output(['git','-C',str(root),'write-tree'],text=True).strip()
  raw=subprocess.check_output(['git','-C',str(root),'ls-tree','-r','-t','-z',sha]);rows=[]
  for item in raw.split(b'\0'):
   if not item:continue
   meta,name=item.split(b'\t');mode,kind,h=meta.decode().split();r=dict(path=name.decode(),mode=mode,type=kind,sha=h)
   if kind=='blob':r['size']=(root/r['path']).stat().st_size
   rows.append(r)
  return rows,sha
 def test_real_git_and_tampering(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);rows,sha=self.fixture(p)
   self.assertEqual(m.verify(p,rows)['tree_sha'],sha)
   (p/'a.txt').write_bytes(b'evil')
   with self.assertRaisesRegex(ValueError,'blob_hash'):m.verify(p,rows)
   (p/'a.txt').write_bytes(b'flat');(p/'run').chmod(0o644)
   with self.assertRaisesRegex(ValueError,'executable_mode'):m.verify(p,rows)
   (p/'run').chmod(0o755);(p/'extra').write_text('x')
   with self.assertRaisesRegex(ValueError,'complete_checkout'):m.verify(p,rows)
   (p/'extra').unlink();(p/'a.txt').unlink();(p/'a.txt').symlink_to('/dev/null')
   with self.assertRaisesRegex(ValueError,'no_symlink'):m.verify(p,rows)
 def test_unsafe_metadata(self):
  for name in ['../escape','/absolute','.git/config','a/../b','a//b','']:
   with self.assertRaises(ValueError):m.validate_rows([dict(path=name,type='blob',mode='100644',sha='0'*40)])
  with tempfile.TemporaryDirectory() as d:
   rows,sha=self.fixture(pathlib.Path(d))
   with self.assertRaisesRegex(ValueError,'duplicate_path'):m.tree_identity(rows+rows[:1])
   changed=json.loads(json.dumps(rows));next(r for r in changed if r['path']=='a/x')['sha']='0'*40
   with self.assertRaisesRegex(ValueError,'subtree_hash'):m.tree_identity(changed)
   with self.assertRaisesRegex(ValueError,'parent_tree'):m.tree_identity([r for r in rows if r['path']!='a'])
if __name__=='__main__':unittest.main()
