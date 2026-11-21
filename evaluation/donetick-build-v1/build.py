#!/usr/bin/env python3
"""Frozen original Donetick build; never starts an application container."""
import hashlib,importlib.util,json,os,pathlib,shutil,subprocess,tarfile,time,traceback
ROOT=pathlib.Path(__file__).resolve().parents[2]
_spec=importlib.util.spec_from_file_location('original_verifier',ROOT/'evaluation/komga-build-v1/build.py')
_v=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_v)
require=_v.require
digest=_v.digest
SOURCES=[('backend','donetick/donetick','e4f5f65a034bce330a58f3036c1b92021b494029','results/editability-repairability-repository-metadata-v1/19/3.json'),('frontend','donetick/frontend','ec024ce525243e41cc9a2997a11de0e58278093e','results/evaluation-source-19-native-tree/3.json')]
def tree_identity(rows):
 """Reconstruct Git root tree identity from frozen recursive entries."""
 by_parent={}
 seen=set()
 for row in rows:
  rel=pathlib.PurePosixPath(row['path'])
  require(not rel.is_absolute() and '..' not in rel.parts and '.git' not in rel.parts and str(rel)==row['path'],'safe_tree_path',path=row['path'])
  require(row['path'] not in seen,'unique_tree_path');seen.add(row['path'])
  require(row['type'] in ('blob','tree'),'supported_tree_entry',path=row['path'])
  require(row['mode'] in ('100644','100755','040000') and ((row['mode']=='040000')==(row['type']=='tree')),'tree_mode',path=row['path'])
  by_parent.setdefault(str(rel.parent),[]).append(row)
 def calculate(parent):
  entries=by_parent.get(parent,[]);body=b''
  for row in sorted(entries,key=lambda x:pathlib.PurePosixPath(x['path']).name.encode()+ (b'/' if x['type']=='tree' else b'')):
   sha=row['sha'];name=pathlib.PurePosixPath(row['path']).name
   if row['type']=='tree':require(calculate(row['path'])==sha,'subtree_identity',path=row['path'])
   require(len(sha)==40,'sha_length')
   body+=row['mode'].lstrip('0').encode()+b' '+name.encode()+b'\0'+bytes.fromhex(sha)
  return hashlib.sha1(b'tree '+str(len(body)).encode()+b'\0'+body).hexdigest()
 require(all(parent=='.' or parent in seen for parent in by_parent),'tree_parent_present')
 return calculate('.')
def verify(src,tree):
 for row in tree:
  p=pathlib.PurePosixPath(row['path'])
  require(not p.is_absolute() and '..' not in p.parts and '.git' not in p.parts,'safe_tree_path',path=row['path'])
  require(row['type'] in ('blob','tree'),'supported_tree_entry',path=row['path'])
 return _v.verify(src,tree)
def main():
 base=pathlib.Path(os.environ['RUNNER_TEMP'])/'evaluation-donetick-build-v1';out=base/'evidence';out.mkdir(parents=True,exist_ok=True)
 start=time.monotonic();report=dict(status='started',stage='sources',application_started=False,scientific_cases=0,commands=[],sources={})
 def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 def run(args,log,cap=60,cwd=None,allow_nonzero=False):
  remaining=1650-(time.monotonic()-start);require(remaining>0,'build_time_budget');row=dict(command=args,log=log);report['commands'].append(row);save();t=time.monotonic()
  try:
   with (out/log).open('wb') as f:cp=subprocess.run(args,cwd=cwd,stdout=f,stderr=subprocess.STDOUT,timeout=min(cap,remaining))
   row['exit_code']=cp.returncode
   if not allow_nonzero:require(cp.returncode==0,'command_exit',log=log,exit_code=cp.returncode)
  finally:row['elapsed_seconds']=time.monotonic()-t;save()
 try:
  for name,repo,rev,treefile in SOURCES:
   src=base/name;src.mkdir();git=['git','-c','core.hooksPath=/dev/null','-C',str(src)]
   run(['git','init','--quiet',str(src)],name+'-init.log')
   run(git+['fetch','--depth=1','--no-tags','https://github.com/'+repo+'.git',rev],name+'-fetch.log',120)
   size=sum(p.stat().st_size for p in (src/'.git').rglob('*') if p.is_file());require(size<=512*1024**2,'git_size_cap',source=name)
   run(git+['rev-parse','FETCH_HEAD'],name+'-commit.txt');require((out/(name+'-commit.txt')).read_text().strip()==rev,'exact_commit')
   run(git+['rev-parse','FETCH_HEAD^{tree}'],name+'-tree.txt')
   tree=json.loads((ROOT/treefile).read_text());require((out/(name+'-tree.txt')).read_text().strip()==tree_identity(tree['tree']),'exact_tree')
   run(git+['checkout','--detach','--quiet','FETCH_HEAD'],name+'-checkout.log')
   v=verify(src,tree['tree']);(out/(name+'-source-verification.json')).write_text(json.dumps(v,indent=2)+'\n')
   archive=out/(name+'-source.tar.gz')
   with tarfile.open(archive,'w:gz',compresslevel=1) as tf:
    for rel in sorted(v['tree_files']):tf.add(src/rel,arcname=name+'/'+rel,recursive=False)
   report['sources'][name]=dict(repository=repo,revision=rev,tree_sha=tree_identity(tree['tree']),files=v['files'],bytes=v['bytes'],archive_sha256=digest(archive),git_bytes=size)
   save()
  front=base/'frontend';back=base/'backend';report['stage']='frontend';save()
  for tool in ['node','npm']:run([tool,'--version'],tool+'-version.txt')
  require((out/'node-version.txt').read_text().strip().startswith('v23.'),'original_node23')
  lock=front/'package-lock.json';report['frontend_lock_before']=digest(lock)
  run(['npm','install'],'frontend-install.log',600,cwd=front)
  report['frontend_lock_after']=digest(lock);shutil.copy2(lock,out/'frontend-resolved-package-lock.json');save()
  run(['npm','ls','--all','--json'],'frontend-dependencies.json',60,cwd=front,allow_nonzero=True)
  run(['npm','run','build-selfhosted'],'frontend-build.log',420,cwd=front)
  dist=front/'dist';require((dist/'index.html').is_file(),'original_frontend_index')
  ui={str(p.relative_to(dist)):dict(bytes=p.stat().st_size,sha256=digest(p)) for p in dist.rglob('*') if p.is_file() and not p.is_symlink()}
  require(not any(p.is_symlink() for p in dist.rglob('*')),'regular_ui_files')
  (out/'frontend-dist-inventory.json').write_text(json.dumps(ui,indent=2)+'\n')
  with tarfile.open(out/'frontend-dist.tar.gz','w:gz',compresslevel=1) as tf:tf.add(dist,arcname='dist')
  shutil.rmtree(back/'frontend/dist');shutil.copytree(dist,back/'frontend/dist')
  for name,_,_,_ in SOURCES:
   original=json.loads((out/(name+'-source-verification.json')).read_text())['tree_files'];changes=[]
   for rel,row in original.items():
    p=base/name/rel
    changed=not p.is_file() or p.is_symlink()
    if not changed:
     raw=p.read_bytes();changed=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=row['sha']
    if changed:changes.append(rel)
   allowed=lambda p:(name=='backend' and p.startswith('frontend/dist/')) or (name=='frontend' and p=='package-lock.json')
   require(all(allowed(p) for p in changes),'no_unplanned_source_changes',source=name,paths=changes)
   report['sources'][name]['changed_paths']=changes
  report['stage']='images';save()
  for idx,tag in enumerate(['golang:1.24-alpine','alpine:latest','postgres:16-bookworm']):
   run(['docker','pull',tag],'image-'+str(idx)+'-pull.log',180)
   run(['docker','image','inspect',tag],'image-'+str(idx)+'-identity.json')
  run(['docker','build','--pull=false','--platform=linux/amd64','--build-arg','VERSION=study','--build-arg','COMMIT='+SOURCES[0][2],'--tag','study-donetick-evaluation:v1',str(back)],'backend-build.log',900)
  run(['docker','image','inspect','study-donetick-evaluation:v1'],'runtime-identity.json')
  run(['docker','create','--name','study-donetick-build-extract','study-donetick-evaluation:v1'],'extract-container.log')
  try:run(['docker','cp','study-donetick-build-extract:/donetick',str(out/'donetick')],'extract-binary.log')
  finally:run(['docker','rm','study-donetick-build-extract'],'extract-cleanup.log')
  report['binary_sha256']=digest(out/'donetick')
  run(['docker','run','--rm','--network=none','--volume',str(out)+':/evidence:ro','golang:1.24-alpine','go','version','-m','/evidence/donetick'],'go-binary-dependencies.txt',60)
  report['image_id']=json.loads((out/'runtime-identity.json').read_text())[0]['Id']
  report['postgres_image_id']=json.loads((out/'image-2-identity.json').read_text())[0]['Id']
  runtime=out/'runtime-images.tar';run(['docker','save','--output',str(runtime),'study-donetick-evaluation:v1','postgres:16-bookworm'],'runtime-export.log',180)
  require(runtime.stat().st_size<=4*1024**3,'export_size_cap');report.update(runtime_archive_sha256=digest(runtime),runtime_archive_bytes=runtime.stat().st_size,status='build_succeeded',stage='complete')
 except Exception as e:
  report.update(status='build_unavailable',error_type=type(e).__name__,error=str(e));(out/'failure-traceback.txt').write_text(traceback.format_exc())
 finally:report['elapsed_seconds']=time.monotonic()-start;save();print(json.dumps({k:report.get(k) for k in ['status','stage','error','application_started']}))
 return 0 if report['status']=='build_succeeded' else 1
if __name__=='__main__':raise SystemExit(main())
