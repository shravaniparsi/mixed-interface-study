#!/usr/bin/env python3
"""First registered NPM qualification attempt, hosted CI only, no reruns.

One shared 23-minute experiment deadline leaves time inside the hard 30-minute
job for cleanup, encrypted retention and upload. Scientific cases remain zero.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

from build_nginx_runtime_v1 import REVISION, digest, ROOT
from provision_nginx_ordinary_v1 import provision_ordinary_scenarios, BROWSER, APP, CLIENT, NETWORK
from seal_nginx_evidence_v1 import seal

REGISTRATION=ROOT/'manifests/catalog-nginx-qualification-v1.json'


def verify_registration():
    if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('GITHUB_REPOSITORY')!='shravaniparsi/mixed-interface-study' or os.environ.get('RUNNER_OS')!='Linux':
        raise ValueError('Registered hosted Linux repository only')
    if os.environ.get('GITHUB_RUN_ATTEMPT')!='1':raise ValueError('No GitHub rerun of this attempt')
    reg=json.loads(REGISTRATION.read_text())
    if reg['status']!='qualification_registered' or reg['application_revision']!=REVISION or reg['max_job_minutes']!=30 or reg['qualification_attempt']!=1:
        raise ValueError('Wrong qualification registration')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,timeout=15).strip()
    if commit!=os.environ['GITHUB_SHA']:raise ValueError('Checkout differs from dispatched revision')
    for path,expected in reg['script_sha256'].items():
        file=ROOT/path
        if digest(file)!=expected or subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT,timeout=15)!=file.read_bytes():
            raise ValueError('Published qualification artifact mismatch: '+path)
    if subprocess.check_output(['git','show',commit+':'+str(REGISTRATION.relative_to(ROOT))],cwd=ROOT,timeout=15)!=REGISTRATION.read_bytes():
        raise ValueError('Unpublished registration')
    subprocess.run(['git','diff','--exit-code','HEAD','--'],cwd=ROOT,check=True,capture_output=True,timeout=15)
    return reg,commit


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workspace',type=Path,required=True);args=parser.parse_args()
    reg,commit=verify_registration()
    root=args.workspace.resolve();root.mkdir(mode=0o700,exist_ok=False)
    private=root/'private';private.mkdir(mode=0o700)
    public=root/'public';public.mkdir(mode=0o700)
    deadline=time.monotonic()+1380
    report={'status':'in_progress','study_commit':commit,'application_revision':REVISION,
        'qualification_attempt':1,'scientific_cases':0,'started_epoch_seconds':time.time(),'stage':'initialization'}
    error=None
    def run(name,command,limit):
        remaining=deadline-time.monotonic()
        if remaining<=0:raise TimeoutError('Shared original experiment deadline expired')
        with (private/f'{name}.log').open('xb') as stream:
            process=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
            try:
                code=process.wait(timeout=min(limit,remaining))
                if code:raise subprocess.CalledProcessError(code,command)
            except BaseException:
                if process.poll() is None:
                    os.killpg(process.pid,signal.SIGTERM)
                    try:process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
                raise
    try:
        report['stage']='browser_provisioning'
        tools=root/'browser-tools';tools.mkdir()
        shutil.copyfile(ROOT/'scripts/ci/package.json',tools/'package.json')
        shutil.copyfile(ROOT/'results/development-admin-control-v2-api-ci-44105779135/node-tools-package-lock.json',tools/'package-lock.json')
        run('browser-tools',['npm','ci','--prefix',str(tools),'--ignore-scripts','--no-audit','--no-fund'],90)
        if digest(tools/'package-lock.json')!=digest(ROOT/'results/development-admin-control-v2-api-ci-44105779135/node-tools-package-lock.json'):
            raise ValueError('Browser package lock changed')
        run('browser-pull',['docker','pull','--platform','linux/amd64',BROWSER],180)
        report['stage']='source_build'
        build=root/'build'
        try:
            run('source-build',[sys.executable,str(ROOT/'scripts/extension/build_nginx_runtime_v1.py'),'--registration',str(REGISTRATION),'--workspace',str(build)],1100)
        finally:
            if (build/'build-evidence').exists():shutil.copytree(build/'build-evidence',private/'build-evidence')
        build_report=json.loads((build/'build-evidence/build.json').read_text())
        if build_report['status']!='source_build_prepared_runtime_unqualified':raise ValueError('Original source build unavailable')
        report['image_id']=build_report['image_id'];report['stage']='ordinary_scenarios'
        result=provision_ordinary_scenarios(build_report['image_id'],build/'source/frontend',tools,private/'runtime',deadline)
        if len(result['scenarios'])!=2:raise ValueError('Both independently warm ordinary scenarios required')
        # The worker checked all three native/API branches and their mandatory
        # predicates in each scenario. Recovery/audit of retained evidence is a
        # separate gate before any scientific dispatch.
        report['status']='ordinary_controls_executed_pending_retained_evidence_audit'
        report['ordinary_scenarios']=2;report['ordinary_branches']=6
    except Exception as exc:
        error=exc
        report.update(status='qualification_failed_no_retry',failed_stage=report['stage'],error_type=type(exc).__name__,error_message_sha256=hashlib.sha256(str(exc).encode()).hexdigest())
        (private/'failure.json').write_text(json.dumps({'stage':report['stage'],'type':type(exc).__name__,'message':str(exc)},indent=2)+'\n')
    finally:
        # These names belong only to this job. No workspace-wide pruning.
        for command in (['docker','rm','-f',APP,CLIENT,'study-nginx-builder','study-nginx-frontend-inventory','study-nginx-package-inventory','study-nginx-backend-inventory','study-nginx-checkpoint-database'],['docker','network','rm',NETWORK]):
            try:subprocess.run(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20,check=False)
            except Exception:report['cleanup_command_unavailable']=True
        try:
            names=subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],timeout=10,text=True).splitlines()
            nets=subprocess.check_output(['docker','network','ls','--format','{{.Name}}'],timeout=10,text=True).splitlines()
            report['application_and_browser_absent']=APP not in names and CLIENT not in names
            report['network_absent']=NETWORK not in nets
            if not report['application_and_browser_absent'] or not report['network_absent']:raise ValueError('Cleanup absence check failed')
        except Exception:
            report['status']='qualification_evidence_unavailable_cleanup_unverified';error=error or RuntimeError('Cleanup unverified')
        report['ended_epoch_seconds']=time.time()
        (private/'parent-result.json').write_text(json.dumps(report,indent=2)+'\n')
        try:
            sealed=seal(private,ROOT/'manifests/catalog-nginx-evidence-recipient-v1.pem',public/'sealed')
            report['sealed_ciphertext_sha256']=sealed['ciphertext_sha256']
        except Exception:
            report['status']='qualification_evidence_unavailable_sealing_failed';error=error or RuntimeError('Private retention failed')
        (public/'qualification-result.json').write_text(json.dumps(report,indent=2)+'\n')
    if error is not None:raise SystemExit('Qualification did not pass; public summary and sealed evidence retained')

if __name__=='__main__':main()
