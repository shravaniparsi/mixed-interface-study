"""Promote only this synthetic test's bounded receipts to the uploader account."""
import argparse,hashlib,json,os,pathlib,re,stat
FIXED={'result.json','before.json','changed.json','restored.json','backup.json','tools.json','freeze.txt','network-interfaces.json','network-routes.json'}
def publish(source,dest,uid,gid):
 assert source.is_dir() and not source.is_symlink() and not dest.exists()
 files=list(source.iterdir());assert len(files)<=40
 prepared=[];total=0
 for p in sorted(files):
  assert p.is_file() and not p.is_symlink()
  assert p.name in FIXED or re.fullmatch(r'[0-9]{2}-[a-z0-9_-]+\.json',p.name)
  raw=p.read_bytes();total+=len(raw);assert len(raw)<=512*1024 and total<=4*1024**2
  if p.suffix=='.json':
   value=json.loads(raw)
   if p.name[:2].isdigit():assert value['arguments_retained'] is False and value['environment_retained'] is False and value['captured_bytes']<=65536
  prepared.append((p.name,raw))
 dest.mkdir(mode=0o700)
 def own(p):
  if (p.stat().st_uid,p.stat().st_gid)!=(uid,gid):os.chown(p,uid,gid)
 manifest={'scope':'synthetic infrastructure receipts only','files':[]}
 for name,raw in prepared:
  p=dest/name;fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'wb') as f:f.write(raw)
  own(p);manifest['files'].append({'name':name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
 p=dest/'publication.json';p.write_text(json.dumps(manifest,indent=2)+'\n');p.chmod(0o600);own(p);own(dest)
 return manifest
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('source',type=pathlib.Path);ap.add_argument('dest',type=pathlib.Path);ap.add_argument('uid',type=int);ap.add_argument('gid',type=int);a=ap.parse_args();publish(a.source,a.dest,a.uid,a.gid)
