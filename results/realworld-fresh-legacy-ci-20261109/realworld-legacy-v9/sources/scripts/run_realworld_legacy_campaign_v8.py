#!/usr/bin/env python3
"""Nine exposed legacy jobs; bounded initial sweep, no retries or primary claims."""
import os,sys,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts/ci'))
from owned_process_scope import interruption_as_exception,defer_stop_signals,stop_owned_group
from run_realworld_identity_campaign import SOURCES as PRIOR_SOURCES
from realworld_identity_campaign import read,write,sha
from mixed_interface.terminal_outcomes import decision
from realworld_legacy_jobs_v8 import selection, plan_for, read_job
from realworld_legacy_campaign_v8 import drive, JOB_TIMEOUT_S, OUTER_TIMEOUT_S
SOURCES=sorted(set(PRIOR_SOURCES+[
    '.github/workflows/realworld_v8.yml','scripts/run_realworld_legacy_job_v8.py',
    'scripts/realworld_legacy_jobs_v8.py','scripts/realworld_legacy_reducer_v8.py',
    'scripts/realworld_legacy_terminal_v8.py','scripts/realworld_legacy_campaign_v8.py',
    'scripts/run_realworld_legacy_campaign_v8.py','scripts/validate_realworld_legacy_campaign_v8.py',
    'scripts/realworld_paired_case.mjs','manifests/realworld-boundary-registry-v1.json',
    'protocol/realworld-legacy-jobs-v8.md','manifests/realworld-python-lock.txt']))


def main():
    artifact=Path(os.environ['CI_ARTIFACT_DIR']);runtime=Path(os.environ['STUDY_RUNTIME'])
    output=artifact/'realworld-legacy-v8';output.mkdir(exist_ok=False)
    execution_root=runtime/'realworld-execution-v8';execution_root.mkdir(exist_ok=False)
    registry=selection();plan=plan_for(registry)
    cert={'source_commit':os.environ.get('GITHUB_SHA'),'plan':plan,
          'sources':{n:sha(ROOT/n) for n in SOURCES},
          'primary_freeze_complete':False,'new_primary_samples':0,
          'job_timeout_s':JOB_TIMEOUT_S,'outer_timeout_s':OUTER_TIMEOUT_S,
          'cleanup_grace_s':5,'kill_wait_s':2}
    for name in SOURCES:
        dest=output/'sources'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    cert['bootstrap_sha256']=sha(artifact/'realworld-bootstrap.json')
    cert['runtime_sha256']={name:sha(artifact/name) for name in ('runtime-versions.json','browser.json')}
    for name in cert['runtime_sha256']:shutil.copyfile(artifact/name,output/name)
    write(output/'plan.json',cert);write(output/'selection.json',registry)
    shutil.copyfile(artifact/'realworld-bootstrap.json',output/'bootstrap.json')
    def execute(job):
        for n,h in cert['sources'].items():
            if sha(ROOT/n)!=h:raise ValueError('Source changed: '+n)
        directory=output/job['job_id'];directory.mkdir(exist_ok=False)
        write(directory/'job.json',job);(directory/'run').mkdir()
        command=[sys.executable,str(ROOT/'scripts/run_realworld_legacy_job_v8.py'),
                 '--subject',str(runtime/'realworld/realworld-django-ninja'),
                 '--python',str(runtime/'realworld/venv/bin/python'),'--node',shutil.which('node'),
                 '--runtime-root',str(execution_root),'--registry',str(output/'selection.json'),
                 '--job',str(directory/'job.json'),'--output-root',str(directory/'run')]
        write(directory/'dispatch.json',{'job':job,'command':command})
        child=None;execution={}
        try:
            with (directory/'runner.log').open('x') as log:
                child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                child.wait(timeout=JOB_TIMEOUT_S)
        finally:
            with defer_stop_signals():
                if child is not None:execution=stop_owned_group(child)
                write(directory/'execution.json',execution)
        observed=read_job(directory,job,registry,execution)
        write(directory/'observations.json',observed);return observed
    with interruption_as_exception():
        report=drive(registry,execute,lambda value:write(output/'diagnostic.json',value))
    print(report['status'])
    return 0 if report['status']=='completed_bounded_diagnostic' else 1


if __name__=='__main__':raise SystemExit(main())
