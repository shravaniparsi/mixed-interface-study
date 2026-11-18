#!/usr/bin/env python3
import hashlib,json,os,pathlib,tarfile,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
BASE=pathlib.Path(os.environ['ORDINARY_BASE']);archive=BASE/'build.zip';out=BASE/'evidence';out.mkdir(exist_ok=True)
def digest(f):
 h=hashlib.sha256()
 for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
 return h.hexdigest()
verified=json.loads((ROOT/'results/redesign-gomodel-build-v1/verification.json').read_text())
with archive.open('rb') as f:assert digest(f)==verified['artifact_zip_sha256']
with zipfile.ZipFile(archive) as z:
 result=json.loads(z.read('result.json'));expected={e['path']:e for e in result['outputs']};seen=set()
 with z.open('executable.tar.gz') as f:assert digest(f)==result['executable_archive_sha256']
 with z.open('executable.tar.gz') as f,tarfile.open(fileobj=f,mode='r|gz') as tf:
  for e in tf:
   assert e.isfile() and e.name in expected and e.name not in seen
   rel=pathlib.PurePosixPath(e.name);assert not rel.is_absolute() and '..' not in rel.parts
   raw=tf.extractfile(e).read();assert len(raw)==expected[e.name]['bytes'] and hashlib.sha256(raw).hexdigest()==expected[e.name]['sha256']
   target=BASE/'executable'/e.name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);target.chmod(0o755 if e.name=='bin/gomodel' else 0o644);seen.add(e.name)
 assert seen==set(expected)
(out/'executable-verification.json').write_text(json.dumps({'build_run':44400417320,'artifact':14470959785,'files':len(seen),'binary_sha256':verified['binary_sha256'],'status':'verified'},indent=2)+'\n')
