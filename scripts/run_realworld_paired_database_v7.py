#!/usr/bin/env python3
"""Four exposed pairs with branch-local database capture; no retries or primary claims."""
import os,sys,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts/ci'))
from owned_process_scope import interruption_as_exception,defer_stop_signals,stop_owned_group
from run_realworld_identity_campaign import SOURCES as PRIOR_SOURCES
from realworld_identity_campaign import read,write,sha
from realworld_identity_database_job_v7 import read_job
from realworld_paired_database_plan_v7 import jobs
from mixed_interface.terminal_outcomes import decision
SOURCES=sorted(set(PRIOR_SOURCES+[
    '.github/workflows/realworld_v7.yml','scripts/run_realworld_pair_job_v7.py',
    'scripts/realworld_identity_case_v2.mjs','scripts/realworld_database_capture_v2.mjs',
    'scripts/capture_identity_database_v2.py','scripts/realworld_identity_db_state_v1.py',
    'scripts/validate_identity_database_capture_v2.py','scripts/realworld_identity_measurements_v2.py',
    'scripts/realworld_identity_database_job_v7.py','scripts/realworld_paired_database_plan_v7.py',
    'scripts/run_realworld_paired_database_v7.py','scripts/validate_realworld_paired_database_v7.py',
    'src/mixed_interface/write_observations.py','protocol/realworld-paired-database-dispatch-v7.md',
    'manifests/realworld-python-lock.txt']))


def main():
    artifact=Path(os.environ['CI_ARTIFACT_DIR']);runtime=Path(os.environ['STUDY_RUNTIME'])
    output=artifact/'realworld-paired-database-v7';output.mkdir(exist_ok=False)
    execution_root=runtime/'realworld-execution-v7';execution_root.mkdir(exist_ok=False)
    registry=read(ROOT/'manifests/realworld-identity-controls-v1.json');selected=jobs(registry)
    cert={'source_commit':os.environ.get('GITHUB_SHA'),'jobs':selected,'sources':{n:sha(ROOT/n) for n in SOURCES},
          'scope':'four exposed pairs; fresh bounded diagnostic, not a resumed campaign; no repetitions',
          'primary_freeze_complete':False,'new_primary_samples':0,'pair_timeout_s':180}
    for name in SOURCES:
        dest=output/'sources'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    cert['bootstrap_sha256']=sha(artifact/'realworld-bootstrap.json')
    write(output/'plan.json',cert)
    shutil.copyfile(artifact/'realworld-bootstrap.json',output/'bootstrap.json')
    report={'status':'running','started_jobs':[],'completed_jobs':[],'terminal_kinds':[],
            'primary_freeze_complete':False,'new_primary_samples':0}
    def save():write(output/'diagnostic.json',report)
    save()
    try:
        with interruption_as_exception():
            for index,job in enumerate(selected):
                for n,h in cert['sources'].items():
                    if sha(ROOT/n)!=h:raise ValueError('Source changed: '+n)
                directory=output/job['job_id'];directory.mkdir(exist_ok=False)
                write(directory/'job.json',job);(directory/'run').mkdir()
                command=[sys.executable,str(ROOT/'scripts/run_realworld_pair_job_v7.py'),
                         '--subject',str(runtime/'realworld/realworld-django-ninja'),
                         '--python',str(runtime/'realworld/venv/bin/python'),'--node',shutil.which('node'),
                         '--runtime-root',str(execution_root),'--registry',str(ROOT/'manifests/realworld-identity-controls-v1.json'),
                         '--job',str(directory/'job.json'),'--output-root',str(directory/'run')]
                write(directory/'dispatch.json',{'job':job,'command':command})
                report['started_jobs'].append(job['job_id']);save()
                child=None;execution={}
                try:
                    with (directory/'runner.log').open('x') as log:
                        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                        child.wait(timeout=180)
                finally:
                    with defer_stop_signals():
                        if child is not None:execution=stop_owned_group(child)
                        write(directory/'execution.json',execution)
                observed=read_job(directory,job,registry,execution)
                write(directory/'observations.json',observed)
                terminal=observed['legacy_result']['terminal']
                report['completed_jobs'].append(job['job_id']);report['terminal_kinds'].append(terminal['kind']);save()
                if index==0 and terminal['kind']!='clean_observation':raise ValueError('Route control is not clean')
                if decision(terminal)['action']=='halt' and index<len(selected)-1:
                    raise ValueError('Semantic terminal halt before remaining diagnostic jobs')
            report['status']='completed_bounded_diagnostic';save()
    except BaseException as error:
        report.update(status='halted',error_type=type(error).__name__,error=str(error));save();raise
    print('Completed four exposed database-instrumented pairs; semantic incompleteness remains explicit.')


if __name__=='__main__':main()
