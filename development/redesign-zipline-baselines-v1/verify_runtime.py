import hashlib,json,os,pathlib,zipfile
base=pathlib.Path(os.environ['ORDINARY_BASE']);root=base/'runtime'
with zipfile.ZipFile(base/'build.zip') as z:expected=json.loads(z.read('result.json'))['outputs']
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
for row in expected:
 p=root/row['path']
 if row['type']=='symlink':assert p.is_symlink() and os.readlink(p)==row['target']
 elif row['type']=='directory':assert p.is_dir() and not p.is_symlink()
 else:assert p.is_file() and not p.is_symlink() and p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
 if 'mode' in row:assert p.stat().st_mode&0o777==row['mode']
actual=set()
for name in ['build','node_modules','drizzle','package.json','pnpm-lock.yaml','pnpm-workspace.yaml','mimes.json','code.json']:
 p=root/name;actual.add(name)
 if p.is_dir():actual.update(str(x.relative_to(root)) for x in p.rglob('*'))
assert actual=={r['path'] for r in expected}
print(json.dumps({'status':'verified_unchanged','entries':len(expected),'runtime_archive_sha256':'dbf090816575df888722ba852a3337b9c1bb98f8a29da56141a34ed4c54a20e8'}))
