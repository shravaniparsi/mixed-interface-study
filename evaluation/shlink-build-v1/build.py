#!/usr/bin/env python3
"""Build only original pinned Shlink images; no application server or study input."""
import hashlib,json,os,pathlib,subprocess,tarfile,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
BASE=pathlib.Path(os.environ['RUNNER_TEMP'])/'evaluation-shlink-build-v1'
OUT=BASE/'evidence'
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
 OUT.mkdir(parents=True,exist_ok=True);start=time.monotonic()
 report=dict(status='started',application_server_started=False,scientific_cases=0,commands=[],images=[])
 def save():(OUT/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 def run(args,log,cap=60,cwd=None,env=None):
  remaining=1720-(time.monotonic()-start);assert remaining>0,'build budget exhausted'
  row=dict(command=args,log=log);report['commands'].append(row);save();t=time.monotonic()
  try:
   with (OUT/log).open('wb') as f: cp=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,cwd=cwd,env=env,timeout=min(cap,remaining))
   row.update(exit_code=cp.returncode,elapsed_seconds=time.monotonic()-t);assert cp.returncode==0,log
  finally:save()
 try:
  run(['docker','version'],'docker-version.txt');run(['docker','buildx','version'],'buildx-version.txt')
  run(['docker','buildx','create','--name','study-shlink-build','--driver','docker-container','--use'],'builder-create.log')
  projects=[('backend','shlinkio/shlink','2aae1740043c3ab9c53f76467273883ac1a32be8','results/editability-repairability-repository-metadata-v1/11/3.json',788,2230229,1000),('client','shlinkio/shlink-web-client','1f5acdfe6867c7e9b248b5846028aec6a3405e10','results/evaluation-source-11-client-metadata/3.json',175,3849927,500)]
  for label,repo,rev,treepath,count,size,seconds in projects:
   report['stage']=label;save();tree=ROOT/treepath;expected={e['path']:e for e in json.loads(tree.read_text())['tree'] if e['type']=='blob'}
   assert len(expected)==count and sum(e['size'] for e in expected.values())==size
   archive=BASE/(label+'.tar.gz');source=BASE/label
   run(['curl','--fail','--location','--retry','0','--max-time','60','--max-filesize',str(64*1024**2),'--output',str(archive),'https://codeload.github.com/'+repo+'/tar.gz/'+rev],label+'-archive.log',65)
   source.mkdir(exist_ok=False);verified_count,verified_bytes=extract(archive,expected,source);assert (verified_count,verified_bytes)==(count,size)
   image='study-shlink-'+label+':'+rev;meta=OUT/(label+'-build-metadata.json')
   row=dict(role=label,repository=repo,revision=rev,source_tree_sha256=digest(tree),archive_sha256=digest(archive),verified_files=count,verified_bytes=size,image=image);report['images'].append(row);save()
   run(['docker','buildx','build','--builder','study-shlink-build','--tag',image,'--progress','plain','--provenance=false','--metadata-file',str(meta),'--load','.'],label+'-build.log',seconds,cwd=source,env={**os.environ,'BUILDX_METADATA_PROVENANCE':'max'})
   for rel,e in expected.items():
    p=source/rel;assert p.is_file() and not p.is_symlink();raw=p.read_bytes();assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==e['sha'],rel
   metadata=json.loads(meta.read_text());row['resolved_materials']=metadata.get('buildx.build.provenance',{}).get('materials');assert row['resolved_materials']
   run(['docker','image','inspect',image],label+'-image.json');info=json.loads((OUT/(label+'-image.json')).read_text())[0];row.update(image_id=info['Id'],image_bytes=info['Size']);assert info['Size']<=4*1024**3
   if label=='backend':
    assert info['Config']['User']=='1001';assert info['Config']['Entrypoint']==['/bin/sh','./docker-entrypoint.sh']
    run(['docker','create','--name','study-shlink-inspect','--entrypoint','/bin/true',image],'backend-container-create.log')
    run(['docker','cp','study-shlink-inspect:/etc/shlink/vendor/composer/installed.json',str(OUT/'composer-installed.json')],'composer-copy.log')
    run(['docker','rm','study-shlink-inspect'],'backend-container-remove.log')
    installed=json.loads((OUT/'composer-installed.json').read_text());packages={p['name']:p for p in installed['packages']}
    for name,ref in [('shlinkio/shlink-common','7e5d108270e8218b139708e2a587605ba55b55c5'),('shlinkio/shlink-event-dispatcher','e53a2fc66b1aa43ac264add2104e4cbe1e44569c')]:
     actual=packages[name]['source']['reference'];assert len(actual)>=7 and ref.startswith(actual),(name,'source mismatch')
     package_dir=BASE/name.split('/')[-1];run(['docker','create','--name','study-shlink-dependency-inspect','--entrypoint','/bin/true',image],name.split('/')[-1]+'-create.log')
     run(['docker','cp','study-shlink-dependency-inspect:/etc/shlink/vendor/'+name,str(package_dir)],name.split('/')[-1]+'-source-copy.log')
     run(['docker','rm','study-shlink-dependency-inspect'],name.split('/')[-1]+'-remove.log')
     checked=[]
     for receipt in sorted(ROOT.glob('results/evaluation-source-11-*/collection.json')):
      source_receipt=json.loads(receipt.read_text())
      if source_receipt.get('repository')!=name or source_receipt.get('status')!='source_wave_closed':continue
      for source_row in source_receipt['rows']:
       assert source_row['status']=='collected_verified';raw=(package_dir/source_row['path']).read_bytes()
       assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==source_row['blob_sha'],source_row['path']
       checked.append(source_row['path'])
     assert checked;row.setdefault('verified_dependency_source',{})[name]=checked
   else:assert info['Config']['User']=='101'
  run(['docker','pull','redis:7.2.5'],'redis-pull.log',120)
  run(['docker','image','inspect','redis:7.2.5'],'redis-image.json');info=json.loads((OUT/'redis-image.json').read_text())[0]
  report['images'].append(dict(role='redis',image='redis:7.2.5',image_id=info['Id'],repo_digests=info['RepoDigests'],image_bytes=info['Size']))
  report['stage']='export';save()
  for row in report['images']:
   archive=OUT/(row['role']+'-image.tar');run(['docker','save','--output',str(archive),row['image']],row['role']+'-export.log',120);assert archive.stat().st_size<=4*1024**3
   row.update(runtime_archive=archive.name,runtime_archive_sha256=digest(archive),runtime_archive_bytes=archive.stat().st_size);save()
  report.update(status='build_succeeded',stage='complete')
 except Exception as e:report.update(status='build_unavailable',error_type=type(e).__name__,error=str(e))
 finally:report['elapsed_seconds']=time.monotonic()-start;save();print(json.dumps({k:report.get(k) for k in ['status','stage','error','application_server_started']}))
 return 0 if report['status']=='build_succeeded' else 1
if __name__=='__main__':raise SystemExit(main())
