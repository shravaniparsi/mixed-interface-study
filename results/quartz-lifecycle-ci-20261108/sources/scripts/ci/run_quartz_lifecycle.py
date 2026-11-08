#!/usr/bin/env python3
"""Live lifecycle probes of the unchanged Quartz campaign, ordinary controls only."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from run_quartz_repeat_campaign import SOURCES
from run_petclinic_interruption import snapshot,track,survivors,port_open,save
from owned_process_scope import interruption_as_exception,defer_stop_signals

QUALIFIED_SOURCES=list(dict.fromkeys(SOURCES+['scripts/ci/run_quartz_lifecycle.py','scripts/validate_quartz_lifecycle.py',
    'scripts/ci/run_petclinic_interruption.py','scripts/ci/owned_process_scope.py',
    'scripts/ci/run_applications.sh','.github/workflows/applications.yml','protocol/quartz-lifecycle-v1.md']))


def browser_checkpoint(stage,table,known):
    """Identify only live owned processes with the adapter's browser marker."""
    live=survivors(table,known)
    for path in sorted((stage/'initial-000/run').glob('*/browser-pid.json')):
        try: metadata=json.loads(path.read_text())
        except (OSError,json.JSONDecodeError):continue
        browser=next((p for p in live if p['pid']==metadata.get('pid') and metadata.get('marker') and metadata['marker'] in p['command']),None)
        adapter=next((p for p in live if 'quartz_generated_case.mjs' in p['command'] and str(path.parent) in p['command']),None)
        java=next((p for p in live if 'org.springframework.boot.loader.launch.PropertiesLauncher' in p['command']),None)
        if browser and adapter and java and port_open(19965):
            return {'kind':'first_control_browser_and_adapter_alive_with_JVM_listening',
                    'browser_metadata':metadata,'metadata_path':str(path.relative_to(stage)),
                    'adapter':adapter,'browser':browser,'java':java,'observed_descendants':live}
    return None


def wait_exit(child,known,deadline):
    while child.poll() is None and time.monotonic()<deadline:
        track(snapshot(),child.pid,known);time.sleep(.05)
    if child.poll() is None:raise TimeoutError('Campaign did not exit before stage deadline')
    child.wait()


def cleanup_observation(known):
    deadline=time.monotonic()+5
    while True:
        remaining=survivors(snapshot(),known)
        if not remaining or time.monotonic()>=deadline:break
        time.sleep(.05)
    return {'observed_processes':list(known.values()),'live_survivors':remaining,'application_port_open':port_open(19965)}


def main():
    if not Path('/proc/self/stat').exists():raise RuntimeError('Linux procfs required')
    artifact=Path(os.environ['CI_ARTIFACT_DIR']);out=artifact/'quartz-lifecycle';out.mkdir(exist_ok=False)
    for name in ('runtime-versions.json','browser.json','quartz-bootstrap.json'):shutil.copyfile(artifact/name,out/name)
    report={'kind':'quartz_live_lifecycle_qualification','status':'incomplete','source_commit':os.environ['GITHUB_SHA'],
            'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in QUALIFIED_SOURCES},
            'stages':{},'primary_freeze_complete':False,'boundary_branches_executed':0,
            'limits':{'checkpoint_s':90,'external_exit_after_signal_s':120,'deadline_exit_from_launch_s':130,'fresh_run_s':210},
            'deadline_injection':'SIGSTOP only the identity-verified owned adapter; unchanged runner uses its ordinary 75000 ms timer and 7000 ms hard-stop grace.'}
    save(out/'plan.json',report)
    for name in QUALIFIED_SOURCES:
        target=out/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    child=None;known={};began=time.monotonic()
    try:
        for stage in ('external_sigterm','case_deadline','fresh'):
            directory=out/stage
            command=[sys.executable,str(ROOT/'scripts/run_quartz_repeat_campaign.py'),
                '--runtime',str(Path(os.environ['STUDY_RUNTIME'])/'quartz'),'--java',os.environ['JAVA_HOME']+'/bin/java',
                '--node',shutil.which('node'),'--python',sys.executable,'--output',str(directory),
                '--playwright-module',os.environ['PLAYWRIGHT_MODULE_PATH'],'--chrome-executable',os.environ['CHROME_EXECUTABLE'],
                '--environment-file',str(artifact/'runtime-versions.json'),'--browser-info',str(artifact/'browser.json')]
            record={'command':command,'status':'running'};report['stages'][stage]=record
            save(out/'report.json',report)
            with (out/(stage+'.log')).open('x') as log:
                started=time.monotonic();known={}
                child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                record['campaign_pid']=child.pid
                if stage!='fresh':
                    while True:
                        table=snapshot();track(table,child.pid,known);point=browser_checkpoint(directory,table,known)
                        if point is not None:break
                        if child.poll() is not None:raise RuntimeError('Campaign exited before checkpoint')
                        if time.monotonic()-started>90:raise TimeoutError('Browser checkpoint missing')
                        time.sleep(.02)
                    record['checkpoint']={**point,'elapsed_s':time.monotonic()-started}
                    if stage=='external_sigterm':
                        sent=time.monotonic();child.send_signal(signal.SIGTERM)
                        record['injection']={'signal':'SIGTERM','target':'campaign'}
                        wait_exit(child,known,sent+120)
                        record['exit_after_signal_s']=time.monotonic()-sent
                    else:
                        adapter=point['adapter'];current=snapshot().get(adapter['pid'])
                        if not current or current['start_ticks']!=adapter['start_ticks']:raise RuntimeError('Adapter identity changed before SIGSTOP')
                        os.kill(adapter['pid'],signal.SIGSTOP)
                        for _ in range(50):
                            current=snapshot().get(adapter['pid'])
                            if current and current['start_ticks']==adapter['start_ticks'] and current['state'] in ('T','t'):break
                            time.sleep(.01)
                        else:raise RuntimeError('Adapter suspension not confirmed')
                        record['injection']={'signal':'SIGSTOP','target':'owned_adapter','suspended_identity':current}
                        wait_exit(child,known,started+130)
                    if child.returncode!=1:raise RuntimeError('Expected unsuccessful interrupted campaign exit')
                else:
                    wait_exit(child,known,started+210)
                    if child.returncode!=0:raise RuntimeError('Fresh controls failed')
                    from validate_quartz_repeat_campaign import verify
                    record['fresh_verification']=verify(directory)
                record['returncode']=child.returncode;record['elapsed_s']=time.monotonic()-started
                record['cleanup']=cleanup_observation(known)
                if record['cleanup']['live_survivors'] or record['cleanup']['application_port_open']:raise RuntimeError('Observed processes or port survived cleanup')
                record['status']='observed';save(out/'report.json',report)
        report['status']='observations_complete'
    except BaseException as error:
        report['error']=type(error).__name__+': '+str(error)
        raise
    finally:
        with defer_stop_signals():
            rescue=[]
            if child is not None:
                if child.poll() is None:child.kill();child.wait(timeout=3);rescue.append({'campaign_pid':child.pid})
                for p in survivors(snapshot(),known):
                    current=snapshot().get(p['pid'])
                    if current and current['start_ticks']==p['start_ticks']:
                        try:os.kill(p['pid'],signal.SIGKILL);rescue.append(p)
                        except ProcessLookupError:pass
            report['rescue_actions']=rescue;report['elapsed_s']=time.monotonic()-began
            if rescue:report['status']='failed_rescue_required'
            save(out/'report.json',report)
            if rescue:raise RuntimeError('Qualification required emergency rescue')
    from validate_quartz_lifecycle import verify
    result=verify(out);save(out/'verification.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':
    with interruption_as_exception():main()
