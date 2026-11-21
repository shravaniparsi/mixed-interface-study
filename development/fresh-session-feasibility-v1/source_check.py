#!/usr/bin/env python3
"""Verify pinned source without installing dependencies or starting applications."""
import hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
SOURCES=[
 ('zipline','diced/zipline','49b81a290dfa59906c4d2a69f729460fc6357134','results/editability-repairability-repository-metadata-v1/02/3.json'),
 ('shlink','shlinkio/shlink','2aae1740043c3ab9c53f76467273883ac1a32be8','results/editability-repairability-repository-metadata-v1/11/3.json'),
 ('shlink-client','shlinkio/shlink-web-client','1f5acdfe6867c7e9b248b5846028aec6a3405e10','results/evaluation-source-11-client-metadata/3.json')]
def require(ok,check,**details):
 if not ok: raise ValueError(json.dumps(dict(check=check,**details),sort_keys=True))
def blob(raw): return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def validate_rows(rows):
 seen={}
 for r in rows:
  name=r['path'];p=pathlib.PurePosixPath(name)
  require(bool(name) and not p.is_absolute() and not set(p.parts)&{'..','.git'} and str(p)==name,'safe_path',path=name)
  require(name not in seen,'duplicate_path',path=name)
  require((r['type'],r['mode']) in [('blob','100644'),('blob','100755'),('tree','040000')],'supported_entry',path=name)
  require(len(r['sha'])==40 and all(c in '0123456789abcdef' for c in r['sha']),'valid_sha',path=name)
  seen[name]=r
 for name in seen:
  p=pathlib.PurePosixPath(name).parent
  require(str(p)=='.' or (str(p) in seen and seen[str(p)]['type']=='tree'),'parent_tree',path=name)
 return seen

def tree_identity(rows):
 validate_rows(rows);parents={}
 for r in rows: parents.setdefault(str(pathlib.PurePosixPath(r['path']).parent),[]).append(r)
 def visit(parent):
  body=b''
  for r in sorted(parents.get(parent,[]),key=lambda x:pathlib.PurePosixPath(x['path']).name.encode()+(b'/' if x['type']=='tree' else b'')):
   if r['type']=='tree': require(visit(r['path'])==r['sha'],'subtree_hash',path=r['path'])
   body+=r['mode'].lstrip('0').encode()+b' '+pathlib.PurePosixPath(r['path']).name.encode()+b'\0'+bytes.fromhex(r['sha'])
  return hashlib.sha1(b'tree '+str(len(body)).encode()+b'\0'+body).hexdigest()
 return visit('.')

def verify(root,rows):
 validate_rows(rows);expected={r['path']:r for r in rows if r['type']=='blob'}
 actual=set()
 for p in root.rglob('*'):
  rel=p.relative_to(root)
  if rel.parts[0]=='.git': continue
  require(not p.is_symlink(),'no_symlink',path=str(rel))
  if p.is_file():actual.add(str(rel))
 require(actual==set(expected),'complete_checkout',missing=sorted(set(expected)-actual),extra=sorted(actual-set(expected)))
 total=0
 for name,r in expected.items():
  p=root/name;raw=p.read_bytes()
  require(len(raw)==r['size'],'file_size',path=name)
  require(blob(raw)==r['sha'],'blob_hash',path=name)
  require(bool(p.stat().st_mode&0o111)==(r['mode']=='100755'),'executable_mode',path=name)
  total+=len(raw)
 return dict(files=len(expected),bytes=total,tree_sha=tree_identity(rows))

def main(base):
 base=pathlib.Path(base);base.mkdir(parents=True,exist_ok=True)
 out=ROOT/'results/fresh-session-source-preflight-v1';out.mkdir(parents=True,exist_ok=True)
 report=dict(application_started=False,dependencies_installed=False,sources=[])
 for name,repo,rev,metadata in SOURCES:
  row=dict(name=name,repository=repo,revision=rev,status='checking');report['sources'].append(row)
  try:
   dest=base/name;require(not dest.exists(),'fresh_destination',path=str(dest))
   subprocess.run(['git','init','-q',str(dest)],check=True,timeout=10)
   git=['git','-c','core.hooksPath=/dev/null','-C',str(dest)]
   with (out/(name+'-fetch.log')).open('w') as log:
    subprocess.run(git+['fetch','--depth=1','--no-tags','https://github.com/'+repo+'.git',rev],check=True,timeout=90,stdout=log,stderr=subprocess.STDOUT)
   run=lambda *args:subprocess.check_output(git+list(args),text=True,timeout=20).strip()
   require(run('rev-parse','FETCH_HEAD')==rev,'exact_commit')
   tree=json.loads((ROOT/metadata).read_text());require(tree.get('truncated') is False,'complete_metadata')
   require(run('rev-parse','FETCH_HEAD^{tree}')==tree_identity(tree['tree']),'commit_tree_identity')
   subprocess.run(git+['checkout','--detach','--quiet','FETCH_HEAD'],check=True,timeout=30)
   row.update(verify(dest,tree['tree']),status='verified',metadata_sha256=hashlib.sha256((ROOT/metadata).read_bytes()).hexdigest())
  except Exception as e:
   row.update(status='unavailable',error_type=type(e).__name__,error=str(e));raise
  finally:(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__': main(sys.argv[1])
