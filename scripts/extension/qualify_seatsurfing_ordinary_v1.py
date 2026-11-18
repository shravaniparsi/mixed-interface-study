#!/usr/bin/env python3
"""Bounded two-cycle parent. Requires a published registration before execution."""
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
from seal_nginx_evidence_v1 import seal
from seatsurfing_fixture_resources_v1 import inspect_resources
from run_seatsurfing_ordinary_cycle_v1 import EDITS

ROOT=Path(__file__).resolve().parents[2]
REVISION='9953f452324bab6fb8f7106dd8965cc401aa456c'


def verify_registration(path):
    if (os.environ.get('GITHUB_ACTIONS'),os.environ.get('GITHUB_REPOSITORY'),os.environ.get('RUNNER_OS'),os.environ.get('GITHUB_RUN_ATTEMPT')) != ('true','shravaniparsi/mixed-interface-study','Linux','1'):
        raise ValueError('Original registered hosted CI attempt only')
    path=Path(path).resolve();reg=json.loads(path.read_text())
    if reg['status']!='qualification_registered' or reg['application_revision']!=REVISION or reg['max_job_minutes']!=30 or reg['qualification_attempt']!=1 or reg['shared_execution_seconds']!=1380:
        raise ValueError('Unexpected registration or deadline')
    if reg['ordinary_edits']!=list(EDITS):raise ValueError('Ordinary edit schedule changed')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,timeout=15).strip()
    if commit!=os.environ.get('GITHUB_SHA'):raise ValueError('Dispatched commit mismatch')
    for name,expected in reg['script_sha256'].items():
        raw=(ROOT/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=expected or subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT,timeout=15)!=raw:
            raise ValueError('Unpublished or changed registered input')
    if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(ROOT))],cwd=ROOT,timeout=15)!=path.read_bytes():
        raise ValueError('Registration is not published')
    subprocess.run(['git','diff','--exit-code','HEAD','--'],cwd=ROOT,check=True,capture_output=True,timeout=15)
    return reg,commit


def run_bounded(command, log, deadline, limit):
    remaining=deadline-time.monotonic()
    if remaining<=0:raise TimeoutError('Original shared deadline exhausted')
    with Path(log).open('xb') as stream:
        process=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            code=process.wait(timeout=min(remaining,limit))
            if code:raise subprocess.CalledProcessError(code,command)
        except BaseException:
            # Kill descendants even if the group leader exited on an error.
            try:os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:pass
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            process.wait(timeout=5)
            raise


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--registration',type=Path,required=True)
    parser.add_argument('--workspace',type=Path,required=True)
    args=parser.parse_args();reg,commit=verify_registration(args.registration)
    os.umask(0o077)
    root=args.workspace.resolve();root.mkdir(mode=0o700,exist_ok=False)
    private=root/'private';private.mkdir(mode=0o700)
    public=root/'public';public.mkdir(mode=0o700)
    started=time.monotonic();deadline=started+1380
    report={'status':'qualification_in_progress','application_revision':REVISION,'study_commit':commit,
            'qualification_attempt':1,'scientific_cases_executed':0,'ordinary_cycles_completed':0,
            'runtime_qualified':False,'stage':'initial_inventory'}
    failure=None;cleanup_count=0
    def cleanup():
        nonlocal cleanup_count
        cleanup_count+=1
        # All cleanup calls share the original 26-minute boundary, leaving
        # four minutes within the hard job ceiling for encryption and upload.
        destination=private/('cleanup-'+str(cleanup_count))
        run_bounded([sys.executable,str(ROOT/'scripts/extension/seatsurfing_fixture_resources_v1.py'),
                     '--private',str(destination)],private/('cleanup-'+str(cleanup_count)+'.log'),started+1560,150)
        value=json.loads((destination/'cleanup-result.json').read_text())
        if value['status']!='owned_fixture_absent_after_cleanup':raise RuntimeError('Cleanup unavailable')
    try:
        if inspect_resources():raise RuntimeError('Runner already contains study fixture')
        report['stage']='source_build';build=root/'build'
        try:
            run_bounded([sys.executable,str(ROOT/'scripts/extension/build_seatsurfing_runtime_v1.py'),
                '--registration',str(args.registration.resolve()),'--workspace',str(build)],private/'build.log',deadline,1100)
        finally:
            if (build/'build-evidence').exists():shutil.copytree(build/'build-evidence',private/'build-evidence')
        build_report=build/'build-evidence/build-report.json'
        for index,edit in enumerate(EDITS):
            report['stage']='ordinary_cycle_'+str(index)
            cycle=private/('cycle-'+str(index))
            run_bounded([sys.executable,str(ROOT/'scripts/extension/run_seatsurfing_ordinary_cycle_v1.py'),
                '--registration',str(args.registration.resolve()),'--build-report',str(build_report),
                '--private',str(cycle),'--edit-index',str(index)],private/('cycle-'+str(index)+'.log'),deadline,1380)
            value=json.loads((cycle/'cycle-result.json').read_text())
            if value['status']!='ordinary_cycle_observed_pending_parent_retention_and_audit' or value['edit']!=edit:
                raise RuntimeError('Ordinary cycle did not pass its gates')
            cleanup()
            report['ordinary_cycles_completed']+=1
        report['status']='ordinary_controls_observed_pending_retained_evidence_audit'
    except Exception as error:
        failure=error
        report.update(status='qualification_unavailable_no_retry',error_type=type(error).__name__)
        (private/'failure.json').write_text(json.dumps({'stage':report['stage'],'type':type(error).__name__,'message':str(error)},indent=2))
    finally:
        try:cleanup();report['fixture_absent_after_cleanup']=True
        except Exception as error:
            failure=failure or error
            report.update(status='qualification_unavailable_cleanup_unverified',fixture_absent_after_cleanup=False)
        report['elapsed_seconds']=time.monotonic()-started
        (private/'parent-result.json').write_text(json.dumps(report,indent=2))
        try:
            sealed=seal(private,ROOT/'manifests/catalog-nginx-evidence-recipient-v1.pem',public/'sealed')
            report['sealed_ciphertext_sha256']=sealed['ciphertext_sha256']
        except Exception as error:
            failure=failure or error;report['status']='qualification_unavailable_evidence_sealing_failed'
        (public/'summary.json').write_text(json.dumps(report,indent=2))
    if failure:raise SystemExit(1)


if __name__=='__main__':main()
