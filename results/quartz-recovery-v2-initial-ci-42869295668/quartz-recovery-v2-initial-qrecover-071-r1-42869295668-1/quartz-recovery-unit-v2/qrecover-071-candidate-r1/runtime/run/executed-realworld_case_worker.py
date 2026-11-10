#!/usr/bin/env python3
"""One reset/backend/browser lifecycle; killed as an owned process group on timeout."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import time
from urllib.request import urlopen

def stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:process.wait(timeout=.7)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=.5)

def _browser_process_snapshot(timeout=.25):
    """Return PID, parent, start identity and command, or an explicit ps error."""
    result=subprocess.run(['ps','-ww','-axo','pid=,ppid=,lstart=,command='],
                          capture_output=True,text=True,timeout=timeout)
    if result.returncode!=0:raise RuntimeError('process_enumeration_failed')
    processes={}
    for line in result.stdout.splitlines():
        if not line.strip():continue
        fields=line.strip().split(None,7)
        if len(fields)!=8:raise RuntimeError('process_enumeration_malformed')
        pid,parent=int(fields[0]),int(fields[1])
        processes[pid]={'pid':pid,'parent':parent,'start':' '.join(fields[2:7]),'command':fields[7]}
    return processes

def _process_identity(process):
    # Parent can change after orphaning; it is not part of stable identity.
    return (process['pid'],process['start'],hashlib.sha256(process['command'].encode()).hexdigest())

class _OwnershipSnapshotError(RuntimeError):pass

def _owned_browser_processes(snapshot,marker,known):
    """Retain observed descendants after reparenting, but not reused PIDs."""
    owned={pid:process for pid,process in snapshot.items() if pid>1 and
           (marker in process['command'].split() or known.get(pid)==_process_identity(process))}
    while True:
        children={pid:process for pid,process in snapshot.items()
                  if pid>1 and pid not in owned and process['parent'] in owned}
        if not children:break
        owned.update(children)
    known.update({pid:_process_identity(process) for pid,process in owned.items()})
    return owned

def cleanup_browser(path,*,term_timeout=.7,kill_timeout=.7,poll_interval=.05,
                    clock=time.monotonic,sleep=time.sleep):
    """Confirm cleanup of this case's marker and observed descendants only.

    The launcher must have exited before calling. JS atomically writes a marker
    before launch and retains it after close, so absent metadata then means no
    browser launch was attempted. A null PID uses exact-marker enumeration.
    Descendant start identities are atomically retained beside the metadata
    before signalling, including after parent exit or interruption of cleanup.
    Every signal revalidates identity; no process group is signalled.
    PID validation and kill cannot be atomic on this portable API, so this avoids
    known PID reuse but does not claim an OS-level atomic identity guarantee.
    Only enumeration timeouts are retried within the TERM/KILL phase deadlines.
    A timeout resets exit confirmation, which requires two fresh empty scans.
    No new ps call starts with less than .05 s remaining in its phase. There is
    no extra enumeration after both deadlines; OS call overhead is measured.
    error_type retains the last exception type, including a recovered timeout.
    """
    result={'ok':False,'reason':None,'metadata_pid':None,'signals':[],
            'observed_owned_pids':[],'remaining_owned_pids':[],
            'identity_changes_skipped':[],'enumeration_timeout_count':0,
            'successful_enumerations':0,'empty_scan_streak':0,'error_type':None}
    started=clock()
    def finish(ok,reason):
        result.update(ok=ok,reason=reason,elapsed_s=max(0.0,clock()-started))
        return result
    if not all(isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>0
               for value in (term_timeout,kill_timeout,poll_interval)):
        return finish(False,'invalid_cleanup_limits')
    path=Path(path);ownership_path=path.with_name(path.name+'.owned.json')
    try:
        info=json.loads(path.read_text())
    except FileNotFoundError:
        if ownership_path.exists():return finish(False,'browser_metadata_missing_with_ownership_snapshot')
        return finish(True,'browser_not_launched')
    except (OSError,ValueError) as error:
        result['error_type']=type(error).__name__
        return finish(False,'invalid_browser_metadata')
    if not isinstance(info,dict) or not isinstance(info.get('marker'),str) or not re.fullmatch(r'--codex-study-case=[0-9a-f]{20}',info['marker']):
        return finish(False,'invalid_browser_marker')
    pid=info.get('pid')
    if 'pid' not in info or (pid is not None and (isinstance(pid,bool) or not isinstance(pid,int) or pid<=1)):
        return finish(False,'invalid_browser_pid')
    marker=info['marker'];result['metadata_pid']=pid
    known={};observed=set();empty_scans=0;last_enumeration_succeeded=False
    try:
        saved=json.loads(ownership_path.read_text())
        if not isinstance(saved,dict) or saved.get('marker')!=marker or not isinstance(saved.get('processes'),list):
            raise ValueError('invalid ownership snapshot')
        for item in saved['processes']:
            if (not isinstance(item,dict) or not isinstance(item.get('pid'),int) or isinstance(item['pid'],bool)
                or item['pid']<=1 or not isinstance(item.get('start'),str) or not item['start']
                or not isinstance(item.get('command_sha256'),str) or not re.fullmatch(r'[0-9a-f]{64}',item['command_sha256'])
                or item['pid'] in known):raise ValueError('invalid process identity')
            known[item['pid']]=(item['pid'],item['start'],item['command_sha256'])
    except FileNotFoundError:pass
    except (OSError,ValueError) as error:
        result['error_type']=type(error).__name__
        return finish(False,'invalid_ownership_snapshot')
    def persist():
        snapshot={'marker':marker,'processes':[{'pid':identity[0],'start':identity[1],'command_sha256':identity[2]}
                                               for _,identity in sorted(known.items())]}
        temporary=ownership_path.with_name(ownership_path.name+'.tmp-'+str(os.getpid()))
        try:
            temporary.write_text(json.dumps(snapshot,sort_keys=True)+'\n')
            temporary.replace(ownership_path)
        except OSError as error:raise _OwnershipSnapshotError('ownership snapshot could not be persisted') from error
    def scan(timeout):
        nonlocal last_enumeration_succeeded
        snapshot=_browser_process_snapshot(timeout=timeout)
        last_enumeration_succeeded=True
        result['successful_enumerations']+=1
        before=dict(known)
        owned=_owned_browser_processes(snapshot,marker,known)
        if known!=before:persist()
        observed.update(owned)
        result['observed_owned_pids']=sorted(observed)
        result['remaining_owned_pids']=sorted(owned)
        return owned
    try:
        for sig,duration in ((signal.SIGTERM,term_timeout),(signal.SIGKILL,kill_timeout)):
            deadline=clock()+duration
            signalled=set()
            while True:
                remaining=deadline-clock()
                if remaining<.05:
                    if remaining>0:sleep(remaining)
                    break
                try:
                    owned=scan(min(.25,remaining))
                    empty_scans=empty_scans+1 if not owned else 0
                    result['empty_scan_streak']=empty_scans
                    if empty_scans>=2:return finish(True,'owned_browser_processes_exited')
                    # Capture descendants before the leader can exit; retained
                    # identities remain valid after reparenting to PID1.
                    for target in sorted(owned,reverse=True):
                        identity=_process_identity(owned[target])
                        if identity in signalled:continue
                        remaining=deadline-clock()
                        if remaining<.05:break
                        current=scan(min(.25,remaining))
                        if target not in current or _process_identity(current[target])!=identity:
                            result['identity_changes_skipped'].append(target)
                            continue
                        if clock()>=deadline:break
                        try:
                            os.kill(target,sig)
                            result['signals'].append({'pid':target,'signal':signal.Signals(sig).name})
                        except ProcessLookupError:pass
                        except OSError as error:
                            result['error_type']=type(error).__name__
                            return finish(False,'owned_process_signal_failed')
                        signalled.add(identity)
                except subprocess.TimeoutExpired as error:
                    empty_scans=0;last_enumeration_succeeded=False
                    result.update(empty_scan_streak=0,error_type=type(error).__name__)
                    result['enumeration_timeout_count']+=1
                remaining=deadline-clock()
                if remaining>0:sleep(min(poll_interval,remaining))
        if not last_enumeration_succeeded:return finish(False,'process_enumeration_unconfirmed')
        return finish(False,'owned_processes_remain' if result['remaining_owned_pids'] else 'exit_not_confirmed_twice')
    except _OwnershipSnapshotError as error:
        result['error_type']=type(error).__name__
        return finish(False,'ownership_snapshot_unconfirmed')
    except (OSError,ValueError,RuntimeError) as error:
        result['error_type']=type(error).__name__
        return finish(False,'process_enumeration_unconfirmed')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['environment','case','output']:parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();config=json.loads(args.environment.read_text());output=args.output
    output.mkdir(parents=True,exist_ok=True);backend=node=None;logs=[]
    def terminate(signum,frame):raise KeyboardInterrupt('case terminated')
    signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate)
    try:
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1',18765))==0:raise RuntimeError('Previous backend still listening; reset refused')
        shutil.copyfile(config['fixture'],config['database'])
        actual=hashlib.sha256(Path(config['database']).read_bytes()).hexdigest()
        assert actual==config['fixture_sha256']
        (output/'reset.json').write_text(json.dumps({'sha256':actual,'independent_offline_reset':True})+'\n')
        env=dict(os.environ,DEBUG='True',DATABASE_URL='file:'+config['database'],TZ='UTC',PYTHONDONTWRITEBYTECODE='1')
        log=open(output/'backend.log','w');logs.append(log)
        backend=subprocess.Popen([config['python'],'manage.py','runserver','127.0.0.1:18765','--noreload'],cwd=config['subject'],env=env,stdout=log,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+25
        while True:
            if backend.poll() is not None:raise RuntimeError('backend startup exited')
            try:
                with urlopen('http://127.0.0.1:18765/api/tags',timeout=.5) as response:
                    if response.status==200:break
            except OSError:pass
            if time.monotonic()>deadline:raise TimeoutError('backend startup')
            time.sleep(.08)
        log=open(output/'node.log','w');logs.append(log)
        node=subprocess.Popen([config['node'],config['case_runner'],'--case',str(args.case),'--output',str(output/'observation.json'),'--browser-pid',str(output/'browser-pid.json')],cwd=config['subject'],env=env,stdout=log,stderr=subprocess.STDOUT)
        (output/'owned-processes.json').write_text(json.dumps({'backend':backend.pid,'node':node.pid})+'\n')
        exit_code=node.wait()
    finally:
        signal.signal(signal.SIGTERM,signal.SIG_IGN)
        cleanup_errors=[]
        for name,process in [('node',node),('backend',backend)]:
            try:stop(process)
            except (OSError,subprocess.TimeoutExpired):cleanup_errors.append(name+'_stop_unconfirmed')
            if process is not None and process.poll() is None:cleanup_errors.append(name+'_still_running')
        cleanup=cleanup_browser(output/'browser-pid.json')
        cleanup['worker_process_cleanup_errors']=cleanup_errors
        cleanup['ok']=cleanup['ok'] and not cleanup_errors
        (output/'cleanup.json').write_text(json.dumps(cleanup,sort_keys=True)+'\n')
        for log in logs:log.close()
        if not cleanup['ok']:raise RuntimeError('Case cleanup unconfirmed: '+str(cleanup['reason']))
    return exit_code

if __name__=='__main__':raise SystemExit(main())
