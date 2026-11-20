#!/usr/bin/env python3
"""Bounded original OSS build; no study application server or inputs."""
import hashlib,json,os,pathlib,subprocess,tarfile,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
BASE=pathlib.Path(os.environ['RUNNER_TEMP'])/'evaluation-flagsmith-build-v2'
OUT=BASE/'evidence'; SRC=BASE/'source'
REV='dba691d4f82f69deac6e023ec17275752a7018af'
TREE=ROOT/'results/editability-repairability-repository-metadata-v1/09/3.json'
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def extract(archive, expected, destination):
 seen=set(); roots=set(); total=0
 with tarfile.open(archive,'r:gz') as tf:
  for m in tf:
   parts=pathlib.PurePosixPath(m.name).parts
   assert parts and not m.name.startswith('/') and '..' not in parts
   roots.add(parts[0]);assert len(roots)==1
   if m.isdir():continue
   assert m.isfile() and len(parts)>1
   rel='/'.join(parts[1:]);assert rel in expected and rel not in seen
   e=expected[rel];assert e['mode'] in ('100644','100755')
   assert m.size==e['size'] and bool(m.mode & 0o111)==(e['mode']=='100755')
   total+=m.size;assert total<=64*1024**2 and len(seen)<5000
   raw=tf.extractfile(m).read();assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==e['sha']
   p=destination/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);p.chmod(0o755 if e['mode']=='100755' else 0o644);seen.add(rel)
 assert seen==set(expected)
 return len(seen),total

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 report=dict(revision=REV,stage='archive',status='started',application_server_started=False,scientific_cases=0,commands=[])
 start=time.monotonic()
 def save(): (OUT/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 def run(args,log,timeout,cwd=None,env=None):
  row=dict(command=args,log=log);report['commands'].append(row);save();t=time.monotonic()
  with (OUT/log).open('wb') as f:
   try:
    cp=subprocess.run(args,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
    row.update(exit_code=cp.returncode,elapsed_seconds=time.monotonic()-t)
   except subprocess.TimeoutExpired:
    row.update(timed_out=True,elapsed_seconds=time.monotonic()-t);save();raise
  save();assert cp.returncode==0,log
 try:
  expected={e['path']:e for e in json.loads(TREE.read_text())['tree'] if e['type']=='blob'}
  assert len(expected)==4328 and sum(e['size'] for e in expected.values())==46582486
  report['tree_sha256']=digest(TREE)
  archive=BASE/'source.tar.gz'
  run(['curl','--fail','--location','--retry','0','--max-time','60','--max-filesize',str(64*1024**2),'--output',str(archive),'https://codeload.github.com/Flagsmith/flagsmith/tar.gz/'+REV],'archive-download.log',65)
  assert archive.stat().st_size<=64*1024**2
  assert digest(archive)=='cbb833de334044a0b1eb827fe00b1ad44f6645ab5153328b3eef8dc289e38efe', 'archive differs from first attempt'
  report.update(archive_sha256=digest(archive),archive_bytes=archive.stat().st_size,stage='verify_source')
  SRC.mkdir(exist_ok=False);count,total=extract(archive,expected,SRC)
  report.update(verified_files=count,verified_bytes=total)
  report['build_input_sha256']={p:digest(SRC/p) for p in ['Dockerfile','api/pyproject.toml','api/uv.lock','api/Makefile','frontend/package.json','frontend/package-lock.json','frontend/.npmrc']}
  run(['docker','version'],'docker-version.txt',30)
  run(['docker','buildx','version'],'buildx-version.txt',30)
  report['stage']='original_oss_build'
  run(['docker','buildx','create','--name','evaluation-flagsmith-v1','--driver','docker-container','--use'],'builder-create.log',30)
  run(['docker','buildx','build','--builder','evaluation-flagsmith-v1','--target','oss-unified','--build-arg','CI_COMMIT_SHA='+REV,'--tag','evaluation-flagsmith:'+REV,'--progress','plain','--provenance=false','--metadata-file',str(OUT/'build-metadata.json'),'--load','.'],'build.log',1440,cwd=SRC,env={**os.environ,'BUILDX_METADATA_PROVENANCE':'max'})
  report['stage']='identity_and_export'
  for rel,e in expected.items():
   p=SRC/rel;assert not p.is_symlink() and p.is_file();raw=p.read_bytes()
   assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==e['sha'],rel
  metadata=json.loads((OUT/'build-metadata.json').read_text());provenance=metadata.get('buildx.build.provenance',{})
  assert provenance.get('materials'), 'resolved build materials unavailable'
  report['resolved_materials']=provenance['materials']
  image='evaluation-flagsmith:'+REV
  run(['docker','image','inspect',image],'image-inspect.json',30)
  info=json.loads((OUT/'image-inspect.json').read_text());assert len(info)==1
  assert info[0]['Config']['User']=='nobody' and info[0]['Config']['Entrypoint']==['flagsmith']
  assert info[0]['Size']<=4*1024**3
  report['runtime_image_id']=info[0]['Id'];report['runtime_image_bytes']=info[0]['Size']
  run(['docker','run','--rm','--network','none','--entrypoint','python',image,'-c','import importlib.metadata,json,sys,pathlib; print(json.dumps({"python":sys.version,"packages":sorted([(d.metadata["Name"],d.version) for d in importlib.metadata.distributions()]),"revision":pathlib.Path("/app/CI_COMMIT_SHA").read_text().strip(),"frontend_present":pathlib.Path("/app/templates/index.html").is_file()}))'],'runtime-packages.json',30)
  inventory=json.loads((OUT/'runtime-packages.json').read_text());assert inventory['revision']==REV
  # Frontend location is recorded, not guessed as a qualification gate; original Docker target supplies bundled assets.
  run(['docker','save','--output',str(OUT/'runtime-image.tar'),image],'image-export.log',180)
  bundle=OUT/'runtime-image.tar';assert bundle.stat().st_size<=4*1024**3
  report.update(runtime_archive_sha256=digest(bundle),runtime_archive_bytes=bundle.stat().st_size,status='build_succeeded',stage='complete')
 except Exception as e:report.update(status='build_unavailable',error_type=type(e).__name__,error=str(e))
 finally:
  report['elapsed_seconds']=time.monotonic()-start;save();print(json.dumps({k:report[k] for k in ['status','stage','application_server_started','scientific_cases']}))
 return 0 if report['status']=='build_succeeded' else 1
if __name__=='__main__':raise SystemExit(main())
