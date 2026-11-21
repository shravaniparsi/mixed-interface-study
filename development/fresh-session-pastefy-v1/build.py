"""Original job-local Docker build with source/dependency evidence, no app startup."""
import hashlib,json,pathlib,subprocess,sys,time
from source_preflight import ROOT,main as preflight
from verify_dependencies import verify_frontend,verify_maven
from source_check import require
PINS=ROOT/'manifests/fresh-session-pastefy-base-images-v1.json'
def recipe(original):
 text=original
 for row in json.loads(PINS.read_text()):
  needle='FROM '+row['tag'];require(text.count(needle)==1,'unique_original_base',tag=row['tag']);text=text.replace(needle,needle+'@'+row['linux_amd64_digest'],1)
 needle='RUN npm --prefix app install';require(text.count(needle)==1,'unique_npm_install')
 # Original COPY frontend app subsequently overwrites package-lock.json.
 # Retain npm's actual resolution before that COPY, without changing install.
 text=text.replace(needle,needle+' && mkdir /study-dependencies && cp /app/package-lock.json /study-dependencies/resolved-package-lock.json',1)
 return text

def build(base):
 base=pathlib.Path(base);require(not base.exists(),'fresh_build_base');base.mkdir();out=base/'evidence';out.mkdir();report=dict(status='started',commands=[],application_started=False);start=time.monotonic()
 def save():(out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
 def run(args,label,timeout=60):
  left=1800-(time.monotonic()-start);require(left>0,'build_deadline');entry=dict(args=args,label=label);report['commands'].append(entry);save()
  with (out/(label+'.log')).open('wb') as log:
   p=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=min(left,timeout))
  entry['returncode']=p.returncode;save();require(p.returncode==0,'build_command',label=label)
 def extract(tag,name,paths):
  container='pastefy-evidence-'+name;run(['docker','create','--name',container,'--entrypoint','/bin/true',tag],name+'-create')
  try:
   for inside,dest in paths:run(['docker','cp',container+':'+inside,str(dest)],name+'-copy-'+dest.name,120)
  finally:run(['docker','rm',container],name+'-remove')
 try:
  src=base/'source';report['source']=preflight(src);df=out/'Dockerfile';df.write_text(recipe((src/'Dockerfile').read_text()));save()
  for stage in ['frontend','build','runtime']:
   report['stage']=stage;tag='fresh-pastefy-'+stage+':v1';args=['docker','build','--platform=linux/amd64','--progress=plain','-f',str(df),'-t',tag]
   if stage!='runtime':args+=['--target',stage]
   run(args+[str(src)],stage,900)
   run(['docker','image','inspect',tag],stage+'-identity')
   if stage=='frontend':
    dep=base/'frontend';dep.mkdir();extract(tag,stage,[('/study-dependencies/resolved-package-lock.json',dep/'resolved.json'),('/app/node_modules/.package-lock.json',dep/'installed.json')]);original=json.loads((src/'frontend/package-lock.json').read_text());resolved=json.loads((dep/'resolved.json').read_text())
    for name in ['resolved','installed']:(out/('frontend-'+name+'.json')).write_bytes((dep/(name+'.json')).read_bytes())
    before,after=original.get('packages',{}),resolved.get('packages',{})
    report['frontend_lock_delta']=dict(top_level_changed=[k for k in sorted(set(original)|set(resolved)) if k!='packages' and original.get(k)!=resolved.get(k)],added=sorted(set(after)-set(before)),removed=sorted(set(before)-set(after)),changed={k:sorted(f for f in set(before[k])|set(after[k]) if before[k].get(f)!=after[k].get(f)) for k in before.keys()&after.keys() if before[k]!=after[k]});save()
    report['frontend']=verify_frontend(src/'frontend/package-lock.json',dep/'resolved.json',dep/'installed.json')
   if stage=='build':
    extract(tag,stage,[('/root/.m2/repository',base/'maven-repository'),('/home/app/target/backend.jar',base/'backend.jar')]);report['vendored_resolution']=verify_maven(src/'backend/vendor-maven-repository',base/'maven-repository')
    report['resolved_jars']=[dict(path=str(p.relative_to(base/'maven-repository')),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted((base/'maven-repository').rglob('*.jar'))]
    report['backend_jar_sha256']=hashlib.sha256((base/'backend.jar').read_bytes()).hexdigest()
   if stage=='runtime':
    identity=json.loads((out/(stage+'-identity.log')).read_text())[0]
    require(identity['Architecture']=='amd64' and identity['Os']=='linux','runtime_platform')
    require(identity['Config']['Entrypoint']==['java','-jar','/usr/local/lib/backend.jar','start'],'original_runtime_entrypoint')
    extract(tag,stage,[('/usr/local/lib/backend.jar',base/'runtime.jar')]);require(hashlib.sha256((base/'runtime.jar').read_bytes()).hexdigest()==report['backend_jar_sha256'],'runtime_jar_equals_builder')
  report['status']='build_verified_not_runtime_qualified'
 except Exception as e:report.update(status='build_unavailable',error_type=type(e).__name__,error=str(e));raise
 finally:report['elapsed_seconds']=time.monotonic()-start;save()
if __name__=='__main__':build(sys.argv[1])
