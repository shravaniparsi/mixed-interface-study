#!/usr/bin/env python3
"""Single original-source Komga JAR build, no application startup."""
import datetime,hashlib,json,os,pathlib,subprocess,tarfile,time,traceback,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
REV='db2ad643c64d9199f7dd01cd3cca3ff0e7a17445'
def require(ok,criterion,**details):
 if not ok:raise ValueError(json.dumps(dict(criterion=criterion,**details),sort_keys=True))
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def verify(src,tree):
 expected={r['path']:r for r in tree if r['type']=='blob'}
 actual={str(p.relative_to(src)) for p in src.rglob('*') if '.git' not in p.relative_to(src).parts and (p.is_file() or p.is_symlink())}
 require(actual==set(expected),'complete_checkout',missing=sorted(set(expected)-actual),extra=sorted(actual-set(expected)))
 total=0
 for rel,r in expected.items():
  p=src/rel; require(not p.is_symlink() and p.is_file(),'regular_file',path=rel)
  require(r['mode'] in ('100644','100755'),'supported_mode',path=rel)
  require(p.stat().st_size==r['size'],'file_size',path=rel)
  raw=p.read_bytes();sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
  require(sha==r['sha'],'blob_identity',path=rel,actual=sha,expected=r['sha'])
  require(bool(p.stat().st_mode&0o111)==(r['mode']=='100755'),'executable_mode',path=rel)
  total+=len(raw)
 return dict(files=len(actual),bytes=total,tree_files=expected)
def main():
 base=pathlib.Path(os.environ['RUNNER_TEMP'])/'evaluation-komga-build-v1';out=base/'evidence';out.mkdir(parents=True,exist_ok=True)
 src=base/'source';src.mkdir();start=time.monotonic()
 report=dict(status='started',stage='fetch',application_started=False,scientific_cases=0,commands=[],revision=REV)
 def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 def run(args,log,cap=60,cwd=None,env=None):
  remaining=1650-(time.monotonic()-start);require(remaining>0,'build_time_budget')
  row=dict(command=args,log=log);report['commands'].append(row);save();t=time.monotonic()
  try:
   with (out/log).open('wb') as f:cp=subprocess.run(args,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=min(cap,remaining))
   row['exit_code']=cp.returncode;require(cp.returncode==0,'command_exit',log=log,exit_code=cp.returncode)
  finally:row['elapsed_seconds']=time.monotonic()-t;save()
 try:
  run(['git','init','--quiet',str(src)],'git-init.log')
  git=['git','-c','core.hooksPath=/dev/null','-C',str(src)]
  run(git+['fetch','--depth=1','--no-tags','https://github.com/gotson/komga.git',REV],'git-fetch.log',120)
  gitbytes=sum(p.stat().st_size for p in (src/'.git').rglob('*') if p.is_file());report['git_directory_bytes']=gitbytes;require(gitbytes<=512*1024**2,'git_size_cap')
  run(git+['rev-parse','FETCH_HEAD'],'fetched-commit.txt');require((out/'fetched-commit.txt').read_text().strip()==REV,'fetched_commit')
  run(git+['rev-parse','FETCH_HEAD^{tree}'],'fetched-tree.txt');report['tree_identity']=(out/'fetched-tree.txt').read_text().strip();save()
  run(git+['checkout','--detach','--quiet','FETCH_HEAD'],'checkout.log')
  tree=json.load(open(ROOT/'results/editability-repairability-repository-metadata-v1/14/3.json'))['tree']
  verification=verify(src,tree);(out/'source-verification.json').write_text(json.dumps(verification,indent=2)+'\n')
  require(verification['files']==1970 and verification['bytes']==95998919,'original_tree_counts')
  archive=out/'original-source.tar.gz'
  with tarfile.open(archive,'w:gz',compresslevel=1) as tf:
   for rel in sorted(verification['tree_files']):tf.add(src/rel,arcname='source/'+rel,recursive=False)
  report['source_archive_sha256']=digest(archive);report['source_archive_bytes']=archive.stat().st_size;report['stage']='frontend';save()
  for dirname,nodekey,version,command in [('komga-webui','NODE22_BIN','22','build'),('next-ui','NODE24_BIN','24','build:with-i18n')]:
   require((src/dirname/'.nvmrc').read_text().strip()==version,'original_node_version',project=dirname)
   env=dict(os.environ);env['PATH']=os.environ[nodekey]+os.pathsep+env['PATH']
   if dirname=='komga-webui':env['NODE_OPTIONS']='--max-old-space-size=4096'
   run(['node','--version'],dirname+'-node.txt',env=env);run(['npm','--version'],dirname+'-npm.txt',env=env)
   run(['npm','ci'],dirname+'-install.log',420,cwd=src/dirname,env=env)
   run(['npm','run',command],dirname+'-build.log',420,cwd=src/dirname,env=env)
  report['stage']='jar';save();run(['java','-version'],'java-version.txt')
  run([str(src/'gradlew'),':komga:webuiCopyIndex',':komga:nextuiCopyIndex',':komga:bootJar'],'gradle-build.log',900,cwd=src)
  jars=[]
  for p in (src/'komga/build/libs').glob('*.jar'):
   with zipfile.ZipFile(p) as z:
    if 'BOOT-INF/classes/application.yml' in z.namelist():jars.append(p)
  require(len(jars)==1,'unique_boot_jar',jars=[str(p) for p in jars]);jar=out/'application.jar';jar.write_bytes(jars[0].read_bytes())
  with zipfile.ZipFile(jar) as z:
   packaged={n:dict(bytes=z.getinfo(n).file_size,sha256=hashlib.sha256(z.read(n)).hexdigest()) for n in z.namelist() if not n.endswith('/')}
   require('BOOT-INF/classes/public/index.html' in packaged and 'BOOT-INF/classes/public/index-next.html' in packaged,'both_original_frontends_packaged')
  (out/'jar-inventory.json').write_text(json.dumps(packaged,indent=2)+'\n');report['jar_sha256']=digest(jar)
  # Verify original tracked source identities remain intact, apart from declared generated web resources.
  changed=[]
  for rel,r in verification['tree_files'].items():
   p=src/rel
   if not p.exists() or hashlib.sha1(b'blob '+str(p.stat().st_size).encode()+b'\0'+p.read_bytes()).hexdigest()!=r['sha']:changed.append(rel)
  report['build_modified_original_paths']=changed
  require(not changed,'original_tracked_sources_unchanged',paths=changed)
  report['stage']='image';save()
  wrapper=base/'packaging';wrapper.mkdir();(wrapper/'application.jar').write_bytes(jar.read_bytes())
  (wrapper/'Dockerfile').write_text('FROM eclipse-temurin:21-jdk\nWORKDIR /app\nCOPY application.jar /app/application.jar\nENTRYPOINT ["java","--enable-native-access=ALL-UNNAMED","-jar","/app/application.jar"]\n')
  run(['docker','pull','eclipse-temurin:21-jdk'],'base-pull.log',180)
  run(['docker','image','inspect','eclipse-temurin:21-jdk'],'base-identity.json')
  run(['docker','build','--pull=false','--tag','study-komga-evaluation:v1',str(wrapper)],'packaging-build.log',180)
  run(['docker','image','inspect','study-komga-evaluation:v1'],'runtime-identity.json')
  report['image_id']=json.load(open(out/'runtime-identity.json'))[0]['Id']
  runtime=out/'runtime-image.tar';run(['docker','save','--output',str(runtime),'study-komga-evaluation:v1'],'export.log',180)
  require(runtime.stat().st_size<=4*1024**3,'runtime_size_cap');report.update(runtime_archive_sha256=digest(runtime),runtime_archive_bytes=runtime.stat().st_size,status='build_succeeded',stage='complete')
 except Exception as e:
  report.update(status='build_unavailable',error_type=type(e).__name__,error=str(e));(out/'failure-traceback.txt').write_text(traceback.format_exc())
 finally:
  report['elapsed_seconds']=time.monotonic()-start;save();print(json.dumps({k:report.get(k) for k in ['status','stage','error','application_started']}))
 return 0 if report['status']=='build_succeeded' else 1
if __name__=='__main__':raise SystemExit(main())
