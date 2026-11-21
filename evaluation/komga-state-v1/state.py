"""Typed three-store backup/restore; original JDBC supplies integrity semantics."""
import hashlib,importlib.util,json,os,pathlib,sqlite3,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('typed_sqlite',ROOT/'evaluation/relaticle-state-v1/sqlite_state.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
snapshot=base.snapshot
canonical=base.canonical
class Observer:
 def __init__(self,classpath,work):
  self.classpath=classpath;self.work=pathlib.Path(work);self.work.mkdir(parents=True,exist_ok=True)
 def jdbc(self,mode,db,script='-'):
  with tempfile.TemporaryDirectory(dir=self.work) as tmp:
   out=pathlib.Path(tmp)/'result.txt';log=pathlib.Path(tmp)/'java.log'
   with log.open('wb') as f:cp=subprocess.run(['java','-cp',self.classpath,'OriginalJdbc',mode,str(db),str(script),str(out)],stdout=f,stderr=subprocess.STDOUT,timeout=20)
   if cp.returncode!=0:raise RuntimeError('original JDBC '+mode+' failed: '+log.read_text()[-2500:])
   result=out.read_text();assert result.startswith('integrity_ok\n' if mode=='integrity' else 'fixture_complete\n');return result
 def backup(self,source,target):
  source=pathlib.Path(source);target=pathlib.Path(target);assert source.is_file() and not target.exists()
  before=snapshot(source);self.jdbc('integrity',source)
  src=sqlite3.connect('file:'+str(source.resolve())+'?mode=ro',uri=True,timeout=3);dst=sqlite3.connect(str(target))
  try:src.backup(dst)
  finally:dst.close();src.close()
  self.jdbc('integrity',target)
  assert before==snapshot(source)==snapshot(target),'backup mismatch/concurrent write'
  return hashlib.sha256(canonical(before)).hexdigest()
 def capture(self,stores,dest):
  """Caller must quiesce ALL writers; double observation checks but does not replace it."""
  assert set(stores)=={'main','tasks','sessions'}
  dest=pathlib.Path(dest);dest.mkdir();before={k:snapshot(p) for k,p in stores.items()}
  hashes={k:self.backup(p,dest/(k+'.sqlite')) for k,p in stores.items()}
  assert before=={k:snapshot(p) for k,p in stores.items()},'incoherent multi-store capture'
  manifest={'logical_sha256':hashes,'file_sha256':{k:hashlib.sha256((dest/(k+'.sqlite')).read_bytes()).hexdigest() for k in stores}}
  (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return before
 def restore(self,backup,stores):
  """All writers stopped; reject stale handles/sidecars through caller + file gates."""
  backup=pathlib.Path(backup);m=json.load(open(backup/'manifest.json'));assert set(stores)==set(m['logical_sha256'])=={'main','tasks','sessions'}
  # Verify the complete checkpoint before altering any destination.
  expected={}
  for k,p in stores.items():
   src=backup/(k+'.sqlite');assert hashlib.sha256(src.read_bytes()).hexdigest()==m['file_sha256'][k],'corrupt backup'
   expected[k]=snapshot(src);assert hashlib.sha256(canonical(expected[k])).hexdigest()==m['logical_sha256'][k]
   self.jdbc('integrity',src);p=pathlib.Path(p);assert not p.is_symlink()
   assert all(not pathlib.Path(str(p)+s).exists() for s in ['-wal','-shm','-journal']),'live or stale sidecar'
  staged=[]
  try:
   for k,p in stores.items():
    p=pathlib.Path(p);stage=p.with_name(p.name+'.restore-stage');assert not stage.exists();self.backup(backup/(k+'.sqlite'),stage);staged.append((stage,p))
    if p.exists():os.chmod(stage,p.stat().st_mode&0o777)
   for stage,p in staged:os.replace(stage,p)
   actual={k:snapshot(p) for k,p in stores.items()};assert actual==expected,'complete restore mismatch'
   for p in stores.values():self.jdbc('integrity',p)
   return actual
  finally:
   for stage,p in staged:
    if stage.exists():stage.unlink()
