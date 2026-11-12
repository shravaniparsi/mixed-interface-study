#!/usr/bin/env python3
"""Bounded valid-service qualification; runs unmodified golden tests, no mutants."""
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
import urllib.request
import xml.etree.ElementTree as ET


def classify_test(return_code, timed_out, totals):
    if timed_out: return 'timeout'
    if totals is None: return 'missing_test_report'
    if totals['errors']: return 'test_error'
    if totals['tests'] == 0: return 'no_tests'
    if totals['failures']: return 'test_failed'
    if totals['skipped']: return 'skipped_unqualified'
    if return_code != 0: return 'execution_error'
    return 'passed'


def main():
    p = argparse.ArgumentParser(); p.add_argument('--benchmark', type=Path, required=True); p.add_argument('--service', choices=['nestjs-realworld'], required=True); p.add_argument('--output', type=Path, required=True); args = p.parse_args()
    bench = args.benchmark.resolve(); out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    service = args.service; service_dir = bench/'services'/service; working = service_dir/'working'
    count = {'fastapi':63,'nestjs-realworld':29,'todoapp':14}[service]
    report = {'kind':'restestbench_valid_golden_nestjs_correction_v1','service':service,'upstream_commit':'4decc1e36ea3dd41b64ce3e3ac6a85bc72df36ae','expected_ids':list(range(1,count+1)),'cases':[],'commands':[],'terminal':'initializing','paid_model_calls':0,'mutations_installed':0}
    def save():
        report['unattempted_ids'] = sorted(set(report['expected_ids'])-{r['id'] for r in report['cases']})
        (out/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(label, command, cwd=bench, timeout=120, input_text=None):
        started=time.monotonic(); log=out/(label+'.log'); timed_out=False
        with log.open('w') as f:
            process=subprocess.Popen(command,cwd=cwd,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.PIPE if input_text else subprocess.DEVNULL,text=True,start_new_session=True)
            try: process.communicate(input_text,timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out=True; os.killpg(process.pid,signal.SIGKILL); process.communicate()
        row={'label':label,'command':command,'return_code':process.returncode,'timeout':timed_out,'elapsed_seconds':round(time.monotonic()-started,3),'log':log.name}
        report['commands'].append(row); save(); return row
    def checked(label, command, cwd=bench, timeout=120, input_text=None):
        row=run(label,command,cwd,timeout,input_text)
        if row['timeout'] or row['return_code'] != 0: raise RuntimeError(label)
        return row
    compose_dir=service_dir if service=='todoapp' else working
    selected={'fastapi':['backend','mailcatcher'],'nestjs-realworld':['nestjs-realworld'],'todoapp':['todoapi']}[service]
    def compose(label, tail, timeout=120, input_text=None):
        return checked(label,['docker','compose']+tail,compose_dir,timeout,input_text)
    url={'fastapi':'http://localhost:8000/docs','nestjs-realworld':'http://localhost:3000/api/tags','todoapp':'http://localhost:5000/scalar/v1'}[service]
    def health(label):
        attempts=[]; start=time.monotonic()
        while time.monotonic()-start<120:
            try:
                with urllib.request.urlopen(url,timeout=3) as response: status=response.status
                attempts.append({'status':status})
                if status==200:
                    (out/(label+'.json')).write_text(json.dumps(attempts));return
            except Exception as exc: attempts.append({'error':type(exc).__name__})
            time.sleep(2)
        (out/(label+'.json')).write_text(json.dumps(attempts));raise RuntimeError(label)
    try:
        actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=bench,text=True).strip();assert actual==report['upstream_commit']
        checked('versions',[sys.executable,'-m','pip','freeze'])
        shutil.copytree(service_dir/'original',working)
        hashes={}
        for directory in [working,bench/'data/tests'/service]:
            for file in sorted(directory.rglob('*')):
                if file.is_file():hashes[str(file.relative_to(bench))]=hashlib.sha256(file.read_bytes()).hexdigest()
        (out/'input-sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
        compose('build',['build',selected[0]],timeout=600)
        compose('start',['up','-d']+selected,timeout=240);health('initial-health')
        compose('images',['images','--format','json'])
        for number in report['expected_ids']:
            prefix=f'req-{number}'
            try:
                if service=='fastapi':
                    compose(prefix+'-schema',['exec','-T','db','psql','-v','ON_ERROR_STOP=1','-U','postgres','-d','app','-c','DROP SCHEMA public CASCADE; CREATE SCHEMA public;'])
                    compose(prefix+'-migrate',['exec','-T','backend','alembic','upgrade','head'])
                    compose(prefix+'-seed',['exec','-T','backend','python','app/initial_data.py'])
                elif service=='nestjs-realworld':
                    compose(prefix+'-restart',['restart','nestjs-realworld']);health(prefix+'-restart-health')
                    tables=['user','article','comment','tag','follows','user_favorites_article']
                    sql='SET FOREIGN_KEY_CHECKS=0;\n'+''.join('TRUNCATE TABLE `'+t+'`;\n' for t in tables)+'SET FOREIGN_KEY_CHECKS=1;\n'
                    compose(prefix+'-truncate',['exec','-T','db','mysql','-u','nestjs','-ppassword','nestjsrealworld'],input_text=sql)
                    count_sql=''.join('SELECT COUNT(*) FROM `'+table+'`;\n' for table in tables)
                    compose(prefix+'-empty-check',['exec','-T','db','mysql','-N','-B','-u','nestjs','-ppassword','nestjsrealworld'],input_text=count_sql)
                    lines=(out/(prefix+'-empty-check.log')).read_text().splitlines()
                    counts=[int(line.strip()) for line in lines if line.strip().isdigit()]
                    if counts != [0]*len(tables): raise RuntimeError(prefix+'-nonempty-reset')
                else:
                    compose(prefix+'-clean',['down','-v']);compose(prefix+'-restart',['up','-d']+selected,timeout=180)
                health(prefix+'-health')
            except Exception as exc:
                report['cases'].append({'id':number,'outcome':'reset_or_health_failure','detail':str(exc),'test_executed':False});raise
            junit=out/(prefix+'.xml');test=bench/'data/tests'/service/f'test_{number}.py'
            row=run(prefix+'-test',[sys.executable,'-m','pytest',str(test),'-v','--tb=short','--junitxml='+str(junit)],timeout=60)
            case={'id':number,'test_executed':True,'return_code':row['return_code'],'timeout':row['timeout'],'test_sha256':hashlib.sha256(test.read_bytes()).hexdigest()}
            totals=None
            if junit.exists():
                xml=ET.parse(junit).getroot(); suites=list(xml.iter('testsuite'))
                totals={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']};case['junit']=totals
            case['outcome']=classify_test(row['return_code'],row['timeout'],totals)
            report['cases'].append(case);save()
        report['terminal']='completed'
    except Exception as exc:report['terminal']='infrastructure_failure';report['error']=type(exc).__name__+': '+str(exc)
    finally:
        if compose_dir.exists():
            run('final-containers',['docker','compose','ps','-a','--format','json'],compose_dir)
            run('final-service-logs',['docker','compose','logs','--no-color','--tail','300'],compose_dir)
            run('cleanup',['docker','compose','down','-v'],compose_dir)
        save()
    print(json.dumps({'terminal':report['terminal'],'cases':len(report['cases']),'unattempted':len(report['unattempted_ids'])}))
    return 0 if report['terminal']=='completed' else 1


if __name__=='__main__':sys.exit(main())
