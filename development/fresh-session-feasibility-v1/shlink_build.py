#!/usr/bin/env python3
"""Job-local original Shlink build with declared manifest-retention instrumentation.
No application starts, uploads, image pushes, or automatic retries.
"""
import difflib,hashlib,json,os,pathlib,re,subprocess,time,traceback
from source_check import SOURCES,require,tree_identity,verify
ROOT=pathlib.Path(__file__).resolve().parents[2]
BASE_IMAGES={
 'php:8.5-alpine3.24':'sha256:b9d7db51a2b83c41420ba04de0b90e6078d4b6440e5cc480fc4dc51b18e0b6db',
 'composer:2':'sha256:50ea4d33fdcde1adb0f045547295faa1548b33872e5f789dae5b02ce2fb5de93',
 'node:26.12-alpine':'sha256:40cd011b55415bc894e45b02fdd5a5dfde056921b7d23a64c74f80497af48797',
 'nginx/nginx-unprivileged:1.31-alpine':'sha256:60214a103e6f38e953ff957f34b1f2e97a9db801ab2df3821da955d0fe6cadd6'}
DEPENDENCIES={'shlinkio/shlink-common':'7e5d108270e8218b139708e2a587605ba55b55c5','shlinkio/shlink-event-dispatcher':'e53a2fc66b1aa43ac264add2104e4cbe1e44569c'}
def reviewed_reference(observed,expected,constraint):
 # Composer preserves an explicitly abbreviated source pin in installed.json.
 # Accept that spelling only when it is declared by the original manifest;
 # the installed reviewed source blobs are still verified below before passing.
 require(re.fullmatch(r'[a-f0-9]{40}',expected) is not None,'full_reviewed_revision')
 if observed==expected:return
 match=re.search(r'#([a-f0-9]{7,40})(?:\s|$)',constraint)
 require(match is not None and observed==match.group(1) and expected.startswith(observed),'reviewed_dependency_identity')

def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def recipe(original,role):
 text=original
 for tag,digest in BASE_IMAGES.items():
  # Pin only existing image references; leave stage references and commands intact.
  text=text.replace('FROM '+tag+' ','FROM '+tag+'@'+digest+' ').replace('FROM '+tag+'\n','FROM '+tag+'@'+digest+'\n').replace('COPY --from='+tag+' ','COPY --from='+tag+'@'+digest+' ')
 if role=='shlink':
  needle='    php composer.phar clear-cache && '
  require(text.count(needle)==1,'unique_composer_cleanup')
  text=text.replace(needle,'    mkdir -p /study-build-evidence && cp composer.json composer.lock /study-build-evidence/ && '+needle.lstrip(),1)
 return text

def main(base):
 base=pathlib.Path(base);base.mkdir(parents=True,exist_ok=True);out=base/'build-evidence';out.mkdir(exist_ok=False)
 start=time.monotonic();report=dict(status='started',application_started=False,commands=[],sources={},images={})
 def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 def run(args,label,seconds=60,cwd=None):
  remaining=1740-(time.monotonic()-start);require(remaining>0,'build_deadline');entry=dict(command=args,log=label);report['commands'].append(entry);save();t=time.monotonic()
  try:
   with (out/label).open('wb') as log:p=subprocess.run(args,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,timeout=min(remaining,seconds))
   entry['exit_code']=p.returncode;require(p.returncode==0,'command_exit',log=label,exit_code=p.returncode)
  finally:entry['elapsed_seconds']=time.monotonic()-t;save()
 def extract(image,label,paths):
  name='fs-build-extract-'+label;run(['docker','create','--name',name,'--entrypoint','/bin/true',image],label+'-container-create.log')
  try:
   for inside,filename in paths:run(['docker','cp',name+':'+inside,str(out/filename)],filename+'.copy.log')
  finally:run(['docker','rm',name],label+'-container-remove.log')
 def build(src,dockerfile,tag,label,target=None):
  args=['docker','build','--platform=linux/amd64','--progress=plain','--file',str(dockerfile),'--tag',tag]
  if target:args+=['--target',target]
  run(args+[str(src)],label+'.log',900)
  run(['docker','image','inspect',tag],label+'-identity.json')
  info=json.loads((out/(label+'-identity.json')).read_text())[0];require(info['Size']<=4*1024**3,'image_size_cap')
  require(info['Architecture']=='amd64' and info['Os']=='linux','target_platform')
  if label=='backend-runtime':
   require(info['Config']['User']=='1001' and info['Config']['Entrypoint']==['/bin/sh','./docker-entrypoint.sh'],'original_backend_entrypoint')
  if label=='client-runtime':require(info['Config']['User']=='101','original_client_user')
  report['images'][label]=dict(tag=tag,id=info['Id'],bytes=info['Size']);save()
 try:
  run(['docker','version'],'docker-version.log')
  for role,repo,rev,metadata in SOURCES:
   if role=='zipline':continue
   report['stage']=role;save();src=base/role;require(not src.exists(),'fresh_source_destination');run(['git','init','-q',str(src)],role+'-init.log')
   git=['git','-c','core.hooksPath=/dev/null','-C',str(src)]
   run(git+['fetch','--depth=1','--no-tags','https://github.com/'+repo+'.git',rev],role+'-fetch.log',90)
   run(git+['rev-parse','FETCH_HEAD'],role+'-commit.txt');require((out/(role+'-commit.txt')).read_text().strip()==rev,'exact_commit')
   rows=json.loads((ROOT/metadata).read_text())['tree'];run(git+['rev-parse','FETCH_HEAD^{tree}'],role+'-tree.txt');require((out/(role+'-tree.txt')).read_text().strip()==tree_identity(rows),'exact_tree')
   run(git+['checkout','--detach','--quiet','FETCH_HEAD'],role+'-checkout.log');verified=verify(src,rows);report['sources'][role]=dict(repository=repo,revision=rev,**verified)
   original=(src/'Dockerfile').read_text();generated=recipe(original,role);dockerfile=out/(role+'.Dockerfile');dockerfile.write_text(generated);(out/(role+'.original.Dockerfile')).write_text(original)
   (out/(role+'.packaging.diff')).write_text(''.join(difflib.unified_diff(original.splitlines(True),generated.splitlines(True),fromfile='original/Dockerfile',tofile='study/Dockerfile')))
   if role=='shlink':
    original_composer=src/'composer.json';(out/'backend-original-composer.json').write_bytes(original_composer.read_bytes())
    build(src,dockerfile,'fresh-shlink-builder:v1','backend-builder','builder')
    extract('fresh-shlink-builder:v1','backend-builder',[('/study-build-evidence/composer.json','backend-final-composer.json'),('/study-build-evidence/composer.lock','backend-resolved-composer.lock')])
    require(sha(original_composer)==sha(out/'backend-final-composer.json'),'composer_manifest_unchanged')
    build(src,dockerfile,'fresh-shlink-backend:v1','backend-runtime')
    extract('fresh-shlink-backend:v1','backend-runtime',[('/etc/shlink/vendor/composer/installed.json','backend-installed.json'),('/etc/shlink/bin/rr','roadrunner')])
    installed=json.loads((out/'backend-installed.json').read_text());packages={p['name']:p for p in installed['packages']}
    require(packages['cuyz/valinor']['source']['reference']=='473ba512c859a4441e382ca279778a67a302971d','reviewed_metadata_cache_library')
    for name,reference in DEPENDENCIES.items():reviewed_reference(packages[name]['source']['reference'],reference,json.loads(original_composer.read_text())['require'][name])
    for name,constraint in json.loads(original_composer.read_text())['require'].items():
     match=re.search(r'#([a-f0-9]{7,40})(?:\s|$)',constraint)
     if match:require(packages[name]['source']['reference'].startswith(match.group(1)),'original_dependency_source_pin',package=name)
    report['roadrunner_sha256']=sha(out/'roadrunner')
    run(['docker','run','--rm','--network=none','--entrypoint','/etc/shlink/bin/rr','fresh-shlink-backend:v1','--version'],'roadrunner-version.txt',15)
    # Retain the exact installed source paths used by prior reviewed source receipts.
    for name in DEPENDENCIES:
     label=name.rsplit('/',1)[-1];extract('fresh-shlink-backend:v1',label,[('/etc/shlink/vendor/'+name,label)])
     checked=[]
     for collection in sorted(ROOT.glob('results/evaluation-source-11-*/collection.json')):
      receipt=json.loads(collection.read_text())
      if receipt.get('repository')!=name or receipt.get('status')!='source_wave_closed':continue
      for row in receipt.get('rows',[]):
       raw=(out/label/row['path']).read_bytes();require(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['blob_sha'],'installed_reviewed_blob',package=name,path=row['path']);checked.append(row['path'])
     require(bool(checked),'reviewed_dependency_paths_present',package=name);report.setdefault('dependency_checked_paths',{})[name]=sorted(set(checked))
   else:
    for name in ['package.json','package-lock.json']:(out/('client-original-'+name)).write_bytes((src/name).read_bytes())
    build(src,dockerfile,'fresh-shlink-client-builder:v1','client-builder','node')
    extract('fresh-shlink-client-builder:v1','client-builder',[('/shlink-web-client/package.json','client-final-package.json'),('/shlink-web-client/package-lock.json','client-final-package-lock.json'),('/shlink-web-client/node_modules/.package-lock.json','client-installed-package-lock.json')])
    for name in ['package.json','package-lock.json']:require(sha(src/name)==sha(out/('client-final-'+name)),'client_manifest_unchanged',path=name)
    installed=json.loads((out/'client-installed-package-lock.json').read_text())['packages']
    locked=json.loads((src/'package-lock.json').read_text())['packages']
    for package,version in [('@shlinkio/shlink-js-sdk','3.2.1'),('@shlinkio/shlink-web-component','0.20.0')]:
     key='node_modules/'+package;require(installed[key]['version']==version,'reviewed_client_version',package=package)
     for attribute in ['version','resolved','integrity']:require(installed[key][attribute]==locked[key][attribute],'client_locked_package_identity',package=package,attribute=attribute)
    build(src,dockerfile,'fresh-shlink-client:v1','client-runtime')
   require(verify(src,rows)==verified,'original_build_context_unchanged');save()
  run(['docker','pull','redis:7.2.5'],'redis-pull.log',120);run(['docker','image','inspect','redis:7.2.5'],'redis-identity.json')
  info=json.loads((out/'redis-identity.json').read_text())[0];report['images']['redis']=dict(tag='redis:7.2.5',id=info['Id'],bytes=info['Size'],repo_digests=info['RepoDigests'])
  run(['docker','run','--rm','--network=none','--entrypoint','redis-server',info['Id'],'--version'],'redis-version.txt',15)
  require('v=7.2.5 ' in (out/'redis-version.txt').read_text(),'redis_runtime_version')
  report.update(status='build_verified',stage='complete',runtime_storage='job_local_only_no_upload')
 except Exception as error:
  report.update(status='build_unavailable',error_type=type(error).__name__,error=str(error));(out/'failure-traceback.txt').write_text(traceback.format_exc())
 finally:report['elapsed_seconds']=time.monotonic()-start;save()
 print(json.dumps({k:report.get(k) for k in ['status','stage','error','application_started']}));return 0 if report['status']=='build_verified' else 1
if __name__=='__main__':
 import sys
 raise SystemExit(main(sys.argv[1]))
