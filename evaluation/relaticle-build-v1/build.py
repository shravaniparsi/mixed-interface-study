#!/usr/bin/env python3
"""Original-source build only; archive preserved before named verification."""
import datetime,hashlib,json,os,pathlib,subprocess,tarfile,time,traceback
ROOT=pathlib.Path(__file__).resolve().parents[2]
REV='480c46e20b6c3d9c39c9254c1ef90369c0615986'
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def require(ok,criterion,**details):
 if not ok:raise ValueError(json.dumps(dict(criterion=criterion,**details),sort_keys=True))
def excluded(path):
 return path=='.github' or path.startswith('.github/') or pathlib.PurePosixPath(path).name in ('CHANGELOG.md','.styleci.yml')
def extract(archive,tree,dest):
 expected={e['path']:e for e in tree if e['type']=='blob' and not excluded(e['path'])};seen=set();root=None;total=0
 with tarfile.open(archive,'r:gz') as tf:
  for m in tf:
   parts=pathlib.PurePosixPath(m.name).parts
   require(bool(parts) and not m.name.startswith('/') and '..' not in parts,'safe_member_path',member=m.name)
   if root is None:root=parts[0]
   require(parts[0]==root,'single_archive_root',member=m.name)
   if m.isdir():continue
   rel='/'.join(parts[1:]);require(m.isfile() and len(parts)>1,'regular_member',member=m.name,type=str(m.type))
   require(rel in expected,'expected_export_member',path=rel);require(rel not in seen,'unique_member',path=rel)
   e=expected[rel];require(e['mode'] in ('100644','100755'),'supported_git_mode',path=rel,mode=e['mode'])
   require(m.size==e['size'],'member_size',path=rel,expected=e['size'],actual=m.size)
   require(bool(m.mode&0o111)==(e['mode']=='100755'),'executable_mode',path=rel,expected=e['mode'],actual=m.mode)
   total+=m.size;require(total<=96*1024**2 and len(seen)<6000,'archive_expansion_limit',bytes=total,count=len(seen))
   raw=tf.extractfile(m).read();actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();require(actual==e['sha'],'git_blob_identity',path=rel,expected=e['sha'],actual=actual)
   p=dest/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);p.chmod(0o755 if e['mode']=='100755' else 0o644);seen.add(rel)
 require(seen==set(expected),'complete_export',missing=sorted(set(expected)-seen))
 return dict(verified_files=len(seen),verified_bytes=total,excluded_paths=sorted(e['path'] for e in tree if e['type']=='blob' and excluded(e['path'])))
def main():
 base=pathlib.Path(os.environ['RUNNER_TEMP'])/'evaluation-relaticle-build-v1';out=base/'evidence';out.mkdir(parents=True,exist_ok=True);start=time.monotonic()
 report=dict(status='started',application_server_started=False,scientific_cases=0,commands=[],stage='setup')
 def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 def run(args,log,cap=60,cwd=None,env=None):
  remaining=1700-(time.monotonic()-start);require(remaining>0,'build_time_budget');row=dict(command=args,log=log);report['commands'].append(row);save();t=time.monotonic()
  try:
   with (out/log).open('wb') as f:cp=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,timeout=min(cap,remaining),cwd=cwd,env=env)
   row['exit_code']=cp.returncode;require(cp.returncode==0,'command_exit',log=log,exit_code=cp.returncode)
  finally:row['elapsed_seconds']=time.monotonic()-t;save()
 try:
  run(['docker','version'],'docker-version.txt');run(['docker','buildx','version'],'buildx-version.txt');run(['docker','buildx','create','--name','study-relaticle-build','--driver','docker-container','--use'],'builder-create.log')
  report['stage']='archive';save();archive=out/'original-source.tar.gz'
  try:run(['curl','--fail','--location','--retry','0','--max-time','60','--max-filesize',str(96*1024**2),'--output',str(archive),'https://codeload.github.com/relaticle/relaticle/tar.gz/'+REV],'archive-download.log',65)
  finally:
   if archive.exists():report['source_archive']=dict(file=archive.name,sha256=digest(archive),bytes=archive.stat().st_size);save()
  require(archive.stat().st_size<=96*1024**2,'archive_size_cap')
  treepath=ROOT/'results/editability-repairability-repository-metadata-v1/12/3.json';tree=json.loads(treepath.read_text())['tree'];report['tree_sha256']=digest(treepath);source=base/'source';source.mkdir(exist_ok=False);report['stage']='source_verification';save()
  report['source_verification']=extract(archive,tree,source);save()
  image='study-relaticle:'+REV;meta=out/'build-metadata.json';report.update(stage='docker_build',image=image);save()
  run(['docker','buildx','build','--builder','study-relaticle-build','--tag',image,'--progress','plain','--provenance=false','--metadata-file',str(meta),'--load','.'],'build.log',1350,cwd=source,env={**os.environ,'BUILDX_METADATA_PROVENANCE':'max'})
  for e in tree:
   if e['type']!='blob' or excluded(e['path']):continue
   raw=(source/e['path']).read_bytes();require(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==e['sha'],'source_unchanged_after_build',path=e['path'])
  report['resolved_materials']=json.loads(meta.read_text()).get('buildx.build.provenance',{}).get('materials');require(bool(report['resolved_materials']),'build_materials_present')
  run(['docker','image','inspect',image],'image.json');info=json.loads((out/'image.json').read_text())[0];report.update(image_id=info['Id'],image_bytes=info['Size'],stage='dependency_verification');require(info['Size']<=4*1024**3,'image_size_cap');save()
  run(['docker','create','--name','study-relaticle-inspect','--entrypoint','/bin/true',image],'inspect-create.log')
  run(['docker','cp','study-relaticle-inspect:/var/www/html/vendor/composer/installed.json',str(out/'composer-installed.json')],'composer-copy.log')
  installed=json.loads((out/'composer-installed.json').read_text())['packages'];locked={p['name']:p for p in json.loads((source/'composer.lock').read_text())['packages']}
  for pkg in installed:
   require(pkg['name'] in locked,'installed_package_locked',package=pkg['name']);want=locked[pkg['name']];require(pkg['version']==want['version'],'installed_version',package=pkg['name'])
   for kind in ['source','dist']:
    if want.get(kind,{}).get('reference'):require(pkg.get(kind,{}).get('reference')==want[kind]['reference'],'installed_reference',package=pkg['name'],kind=kind)
  checked={}
  for repo in ['relaticle/custom-fields','laravel/framework','laravel/sanctum']:
   folder=base/repo.replace('/','-');run(['docker','cp','study-relaticle-inspect:/var/www/html/vendor/'+repo,str(folder)],repo.replace('/','-')+'-copy.log');checked[repo]=[]
   for receipt in sorted(ROOT.glob('results/evaluation-source-12-*/collection.json')):
    r=json.loads(receipt.read_text())
    if r.get('repository')!=repo or r.get('status')!='source_wave_closed':continue
    for row in r['rows']:
     require(row['status']=='collected_verified','reviewed_dependency_available',path=row['path']);raw=(folder/row['path']).read_bytes();require(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['blob_sha'],'reviewed_dependency_blob',repository=repo,path=row['path']);checked[repo].append(row['path'])
   require(bool(checked[repo]),'dependency_review_present',repository=repo)
  report['verified_dependency_files']=checked;run(['docker','rm','study-relaticle-inspect'],'inspect-remove.log');report['stage']='export';save()
  runtime=out/'runtime-image.tar';run(['docker','save','--output',str(runtime),image],'image-export.log',180);require(runtime.stat().st_size<=4*1024**3,'runtime_archive_cap');report.update(runtime_archive=runtime.name,runtime_archive_sha256=digest(runtime),runtime_archive_bytes=runtime.stat().st_size,status='build_succeeded',stage='complete')
 except Exception as e:
  report.update(status='build_unavailable',error_type=type(e).__name__,error=str(e));(out/'failure-traceback.txt').write_text(traceback.format_exc())
 finally:report['elapsed_seconds']=time.monotonic()-start;save();print(json.dumps({k:report.get(k) for k in ['status','stage','error','application_server_started']}))
 return 0 if report['status']=='build_succeeded' else 1
if __name__=='__main__':raise SystemExit(main())
