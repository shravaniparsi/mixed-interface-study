#!/usr/bin/env python3
"""Run five previously exposed RealWorld profile identity pairs through terminal campaign v2."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts/ci'))
from mixed_interface.campaign_v2 import drive
from owned_process_scope import interruption_as_exception,defer_stop_signals,stop_owned_group
from realworld_identity_campaign import read,write,sha,plan_for,read_job
SOURCES=['scripts/realworld_identity_bridge_v1.py','scripts/realworld_identity_extract_v1.py','scripts/realworld_identity_v1.mjs','.github/workflows/realworld_v6.yml','scripts/ci/prepare_realworld.py','scripts/realworld_rejection_outcomes.py','scripts/realworld_terminal_campaign.py','scripts/validate_realworld_identity_campaign.py','scripts/run_realworld_identity_campaign.py','scripts/run_realworld_pair_job_v6.py',
 'scripts/realworld_identity_campaign.py','scripts/realworld_terminal_outcomes.py',
 'scripts/summarize_realworld_paired_components.py','scripts/summarize_realworld_oracle_components.py',
 'scripts/validate_realworld_paired_controls.py','scripts/run_realworld_pilot.py',
 'scripts/realworld_identity_case_v1.mjs','scripts/realworld_integrity.mjs','scripts/response_capture.mjs',
 'scripts/realworld_normalization.mjs','scripts/phase_clock.mjs','scripts/ci/owned_process_scope.py',
 'src/mixed_interface/normalization.py','src/mixed_interface/terminal_outcomes.py',
 'src/mixed_interface/campaign_v2.py','src/mixed_interface/repetition.py',
 'manifests/realworld-identity-controls-v1.json','protocol/realworld-identity-dispatch-v6.md']


def main():
    artifact=Path(os.environ['CI_ARTIFACT_DIR']);runtime=Path(os.environ['STUDY_RUNTIME'])
    output=artifact/'realworld-identity-controls';output.mkdir(exist_ok=False)
    execution_root=runtime/'realworld-execution';execution_root.mkdir(exist_ok=True)
    registry=read(ROOT/'manifests/realworld-identity-controls-v1.json');plan=plan_for(registry)
    cert={'source_commit':os.environ.get('GITHUB_SHA'),'plan':plan,
          'sources':{n:sha(ROOT/n) for n in SOURCES},'primary_freeze_complete':False,
          'scope':'Five exposed profile identity pairs; no boundary selection; no resume',
          'pair_timeout_s':180,'cleanup_grace_s':5,'kill_wait_s':2}
    for name in SOURCES:
        dest=output/'sources'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    write(output/'plan.json',cert)
    def execute(job):
        for n,h in cert['sources'].items():
            if sha(ROOT/n)!=h:raise ValueError('Live source changed: '+n)
        directory=output/job['job_id'];directory.mkdir(exist_ok=False)
        write(directory/'job.json',job);(directory/'run').mkdir()
        command=[sys.executable,str(ROOT/'scripts/run_realworld_pair_job_v6.py'),
                 '--subject',str(runtime/'realworld/realworld-django-ninja'),
                 '--python',str(runtime/'realworld/venv/bin/python'),'--node',shutil.which('node'),
                 '--runtime-root',str(execution_root),'--registry',str(ROOT/'manifests/realworld-identity-controls-v1.json'),
                 '--job',str(directory/'job.json'),'--output-root',str(directory/'run')]
        write(directory/'dispatch.json',{'job':job,'command':command})
        child=None;execution={}
        try:
            with (directory/'runner.log').open('x') as log:
                child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                child.wait(timeout=180)
        finally:
            with defer_stop_signals():
                if child is not None:execution=stop_owned_group(child)
                write(directory/'execution.json',execution)
        result=read_job(directory,job,registry,execution);write(directory/'observations.json',result)
        return result['terminal']
    with interruption_as_exception():
        state=drive(plan,execute,lambda state:write(output/'campaign.json',state))
    if state['status']!='completed_observations':raise RuntimeError('Identity campaign halted; retain all evidence')
    print('Completed five RealWorld identity pairs through terminal v2')


if __name__=='__main__':main()
