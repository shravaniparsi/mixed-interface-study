"""Independent verification of source and runtime inside a completed build artifact."""
import argparse,hashlib,io,json,pathlib,tarfile,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
FREEZE='b69cdd8cb572f66a7c9629a66a96e0e1c2a24001'
def require(ok,label):
 if not ok:raise ValueError(label)
def hash_stream(stream):
 h=hashlib.sha256();n=0
 for b in iter(lambda:stream.read(1048576),b''):h.update(b);n+=len(b)
 return h.hexdigest(),n
def verify(archive,out,extract_jar=None):
 archive=pathlib.Path(archive);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
 with archive.open('rb') as f:artifact_hash,artifact_bytes=hash_stream(f)
 with zipfile.ZipFile(archive) as z:
  names=z.namelist();require(len(names)==len(set(names)),'duplicate artifact members')
  require(all(not n.startswith('/') and '..' not in pathlib.PurePosixPath(n).parts for n in names),'unsafe artifact member')
  require(z.read('freeze.txt').decode().strip()==FREEZE,'implementation freeze')
  r=json.loads(z.read('result.json'));require(r['status']=='build_succeeded' and r['application_started'] is False and r['scientific_cases']==0,'successful build-only scope')
  tree=json.load(open(ROOT/'results/editability-repairability-repository-metadata-v1/14/3.json'))['tree'];expected={x['path']:x for x in tree if x['type']=='blob'}
  for member,key in [('original-source.tar.gz','source_archive_sha256'),('application.jar','jar_sha256'),('runtime-image.tar','runtime_archive_sha256')]:
   with z.open(member) as f:sha,n=hash_stream(f)
   require(sha==r[key],'artifact digest '+member)
   if member=='runtime-image.tar':require(n==r['runtime_archive_bytes'],'runtime byte count')
  seen=set();total=0
  with z.open('original-source.tar.gz') as f,tarfile.open(fileobj=f,mode='r|gz') as tf:
   for m in tf:
    require(m.isfile() and m.name.startswith('source/'),'regular source file')
    rel=m.name[len('source/'):];require(rel in expected and rel not in seen,'expected unique source')
    e=expected[rel];require(m.size==e['size'],'source size');require(bool(m.mode&0o111)==(e['mode']=='100755'),'source mode')
    h=hashlib.sha1(b'blob '+str(m.size).encode()+b'\0');content=tf.extractfile(m)
    for b in iter(lambda:content.read(1048576),b''):h.update(b)
    require(h.hexdigest()==e['sha'],'source blob '+rel);seen.add(rel);total+=m.size
  require(seen==set(expected) and len(seen)==1970 and total==95998919,'complete original source')
  require(z.getinfo('application.jar').file_size<=512*1024**2,'jar memory ceiling')
  jar=z.read('application.jar');inventory=json.loads(z.read('jar-inventory.json'))
  with zipfile.ZipFile(io.BytesIO(jar)) as j:
   jnames=[n for n in j.namelist() if not n.endswith('/')];require(len(jnames)==len(set(jnames)) and set(jnames)==set(inventory),'jar inventory completeness')
   require(all(not n.startswith('/') and '..' not in pathlib.PurePosixPath(n).parts for n in jnames),'safe jar member paths')
   for n in jnames:
    with j.open(n) as f:sha,size=hash_stream(f)
    require({'bytes':size,'sha256':sha}==inventory[n],'jar member '+n)
  image=json.loads(z.read('runtime-identity.json'));require(len(image)==1 and image[0]['Id']==r['image_id'],'runtime image identity')
  require(not r['build_modified_original_paths'],'unchanged original source')
  if extract_jar is not None:pathlib.Path(extract_jar).write_bytes(jar)
  for n in names:
   if n.endswith('/') or z.getinfo(n).file_size>2*1024**2:continue
   require(len(pathlib.PurePosixPath(n).parts)==1,'receipt top-level member')
   (out/n).write_bytes(z.read(n))
  result=dict(status='independently_verified',artifact_sha256=artifact_hash,artifact_bytes=artifact_bytes,source_files=len(seen),source_bytes=total,jar_members=len(inventory),jar_sha256=r['jar_sha256'],image_id=r['image_id'],runtime_archive_sha256=r['runtime_archive_sha256'],implementation_freeze=FREEZE,application_executed=False,scientific_cases=0)
  (out/'independent-verification.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--out',required=True);p.add_argument('--extract-jar');a=p.parse_args();print(json.dumps(verify(a.archive,a.out,a.extract_jar)))
