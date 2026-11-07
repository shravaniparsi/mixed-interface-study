#!/usr/bin/env python3
"""Archive a prospective control plan, own the frontend, and validate one run."""
import json,os,subprocess,sys,time,urllib.request,shutil
from owned_process_scope import interruption_as_exception, defer_stop_signals, stop_owned_group
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from validate_petclinic_integrity import SOURCES,sha,read,validate_run
artifact=Path(os.environ['CI_ARTIFACT_DIR']);runtime=Path(os.environ['STUDY_RUNTIME'])/'petclinic'
selection=read(ROOT/'manifests/petclinic-integrity-controls-v1.json');bootstrap=read(artifact/'petclinic-bootstrap.json')
out=artifact/'petclinic-integrity-controls';snapshot=artifact/'petclinic-integrity-sources'
assert not out.exists();snapshot.mkdir(exist_ok=False)
qualified_sources=[*SOURCES, 'scripts/ci/owned_process_scope.py']
for name in qualified_sources:
 p=snapshot/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)
plan={'source_commit':os.environ['GITHUB_SHA'],'created_at_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':{n:sha(ROOT/n) for n in qualified_sources},'environment_sha256':{n:sha(artifact/n) for n in ['petclinic-bootstrap.json','runtime-versions.json','browser.json']},'selection':selection,'outer_timeout_s':480,'repeat_policy':'No resume, retry or merge; fresh output and complete attempt only.'}
(artifact/'petclinic-integrity-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
frontend=None;runner=None
cleanup={}
def stop(p,name):
 if p is not None:cleanup[name]=stop_owned_group(p)
with interruption_as_exception():
 try:
  with (artifact/'petclinic-frontend.log').open('x') as log:
   frontend=subprocess.Popen(['node','node_modules/@angular/cli/bin/ng.js','serve','--host','127.0.0.1','--port','19766'],cwd=runtime/'frontend',stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   deadline=time.monotonic()+90
   while True:
    if frontend.poll() is not None:raise RuntimeError('Frontend exited during startup')
    try:
     with urllib.request.urlopen('http://127.0.0.1:19766',timeout=1) as r:
      if r.status==200:break
    except (OSError,TimeoutError):pass
    if time.monotonic()>deadline:raise TimeoutError('Frontend readiness deadline')
    time.sleep(.25)
   runner=subprocess.Popen(['node',str(ROOT/'scripts/petclinic_boundary_slice.mjs'),'--registry',str(ROOT/'manifests/petclinic-candidates-v1.json'),'--output',str(out),'--jar',bootstrap['jar'],'--java',os.environ['JAVA_HOME']+'/bin/java','--playwright-module',os.environ['PLAYWRIGHT_MODULE_PATH'],'--chrome-executable',os.environ['CHROME_EXECUTABLE'],'--cases',','.join(c['id'] for c in selection['cases'])],start_new_session=True)
   if runner.wait(timeout=360)!=0:raise RuntimeError('PetClinic runner failed; retain attempt')
   result=validate_run(out,artifact)
   (artifact/'petclinic-integrity-validation.json').write_text(json.dumps(result,indent=2)+'\n')
   print(json.dumps({'status':result['status'],'branches':result['branches']}),flush=True)
 finally:
  with defer_stop_signals():
   try:
    try:stop(runner,'runner')
    finally:stop(frontend,'frontend')
   finally:
    (artifact/'petclinic-owned-process-cleanup.json').write_text(json.dumps(cleanup,indent=2)+'\n')
if any(not r['exit_confirmed'] or r['errors'] for r in cleanup.values()):
 raise RuntimeError('Owned process cleanup failed; retain attempt')
