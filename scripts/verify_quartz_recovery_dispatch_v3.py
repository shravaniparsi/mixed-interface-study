"""Verify an orchestration-only amendment; the v2 experiment freeze is unchanged."""
from primary_preflight_v1 import ROOT,read,sha
from verify_quartz_recovery_release_v2 import verify,ci_accepted
from mixed_interface.repetition import require
MANIFEST=ROOT/'manifests/quartz-recovery-dispatch-v3.json'
WORKFLOW='.github/workflows/quartz_recovery_dispatch_v3.yml'
GUARD='scripts/verify_quartz_recovery_dispatch_v3.py'
FAILURE=ROOT/'results/quartz-recovery-dispatch-failure-ci-42868555205'

def failure_verified():
    run=read(FAILURE/'run.json');jobs=read(FAILURE/'jobs.json')['jobs']
    require(run['id']==42868555205 and run['conclusion']=='failure','Dispatch failure record differs')
    require(len(jobs)==2,'Unexpected dispatch jobs')
    selection=next(j for j in jobs if j['name']=='selection')
    app=next(j for j in jobs if j['name']=='application')
    require(selection['conclusion']=='failure' and app['conclusion']=='skipped' and not app['runner_id'] and not app['steps'],'Application work started in failed dispatch')
    require('quartz_recovery_matrix_v1.py' in (FAILURE/'selection-failure.log').read_text(),'Dispatch failure cause differs')
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(FAILURE.iterdir())}

def check():
    verify();v=read(MANIFEST)
    require(v['freeze_sha256']==sha(ROOT/'manifests/quartz-recovery-freeze-v2.json'),'Experimental release differs')
    require(v['source_sha256']=={p:sha(ROOT/p) for p in (WORKFLOW,GUARD)},'Dispatch source differs')
    require(v['failed_dispatch_evidence_sha256']==failure_verified(),'Pre-execution failure evidence differs')
    ci=read(ROOT/v['ci_record']);require(sha(ROOT/v['ci_record'])==v['ci_sha256'],'Dispatch CI bytes differ')
    ci_accepted(ci,v['source_commit'])
    return {'amendment_sha256':sha(MANIFEST),'experimental_freeze_sha256':v['freeze_sha256'],'source_ci':ci['id'],'application_cases_started_in_failed_dispatch':0}

if __name__=='__main__':print(__import__('json').dumps(check()))
