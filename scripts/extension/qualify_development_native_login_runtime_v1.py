#!/usr/bin/env python3
"""One isolated, fixed-binary startup schedule; run inside an empty network namespace."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import urllib.error
import urllib.request

SHA='1c7500685740eb01994aa13ea381f3eb9af2c65bfb92f2379e42bb909225c71b'

def main():
    p=argparse.ArgumentParser();p.add_argument('--java',required=True);p.add_argument('--jar',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--node',required=True);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    work=out/'runtime';work.mkdir(exist_ok=False)
    result={'kind':'development_isolated_native_login','requests':[],'status':'setup_failed'}
    proc=None;start=time.monotonic()
    def fetch(path,label,timeout):
        row={'path':path,'label':label}
        try:
            try:r=urllib.request.urlopen('http://127.0.0.1:8080'+path,timeout=timeout)
            except urllib.error.HTTPError as error:r=error
            with r:
                body=r.read(4*1024*1024+1);row['http_status']=r.code
            if len(body)>4*1024*1024:raise ValueError('response byte bound')
            name=label+'.body';(out/name).write_bytes(body)
            row.update(body_file=name,bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
            try:
                d=json.loads(body)
                if isinstance(d,dict):
                    row['top_level_keys']=sorted(d)
                    row['openapi']=d.get('openapi')
                    row['path_count']=len(d['paths']) if isinstance(d.get('paths'),dict) else 0
                    row['obtained_specification']=row['http_status']==200 and isinstance(d.get('openapi'),str) and row['path_count']>0
            except (ValueError,UnicodeDecodeError):row['json_parse']='failed'
        except Exception as error:row.update(error_type=type(error).__name__,message=str(error))
        result['requests'].append(row);return row
    try:
        jar=a.jar.resolve();assert hashlib.sha256(jar.read_bytes()).hexdigest()==SHA
        result['jar_sha256']=SHA
        subprocess.run(['ip','link','set','lo','up'],check=True)
        interfaces=subprocess.check_output(['ip','-j','link'],text=True)
        (out/'interfaces.json').write_text(interfaces)
        assert {i['ifname'] for i in json.loads(interfaces)}=={'lo'}, 'Network isolation required'
        version=subprocess.run([a.java,'-version'],capture_output=True,text=True,check=True)
        (out/'java-version.txt').write_text(version.stdout+version.stderr)
        assert 'Temurin-17.0.2+8' in version.stderr+version.stdout
        command=[a.java,'-Xmx1g','-jar',str(jar),'--spring.profiles.active=dev,api-docs','--server.address=127.0.0.1','--server.port=8080']
        result['command']=command
        with (out/'application.log').open('w') as log:
            proc=subprocess.Popen(command,cwd=work,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            deadline=time.monotonic()+300;ready=False
            count=0
            while time.monotonic()<deadline and proc.poll() is None:
                count+=1;row=fetch('/management/health','health-'+str(count),3)
                if row.get('http_status') ==200:ready=True;break
                time.sleep(min(5,max(0,deadline-time.monotonic())))
            result['readiness_response_observed']=ready
            if ready:
                browser_run=subprocess.run([a.node,'scripts/extension/qualify_development_native_login_v1.mjs','--out',str(out)],timeout=120);result['browser_exit']=browser_run.returncode
            result['status']='native_login_qualified' if ready and result.get('browser_exit')==0 and json.loads((out/'native-login.json').read_text())['status']=='qualified' else 'native_login_unqualified'
            result['process_exit_before_cleanup']=proc.poll()
    except Exception as error:result.update(error_type=type(error).__name__,message=str(error))
    finally:
        if proc is not None and proc.poll() is None:
            os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=15)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
        result['final_process_exit']=proc.returncode if proc is not None else None
        result['elapsed_seconds']=time.monotonic()-start
        (out/'measurement.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['status']=='native_login_qualified' else 1

if __name__=='__main__':raise SystemExit(main())
