#!/usr/bin/env python3
"""Install every registered mutant independently and qualify golden-test execution."""
import argparse
import hashlib
import importlib.util
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
PIN='4decc1e36ea3dd41b64ce3e3ac6a85bc72df36ae'


def digest(data):return hashlib.sha256(data).hexdigest()


def classify(code, timed_out, totals):
    if timed_out:return 'timeout'
    if totals is None:return 'missing_test_report'
    if totals['errors']:return 'test_error'
    if not totals['tests']:return 'no_tests'
    if totals['skipped']:return 'skipped_unqualified'
    if totals['failures']:return 'execution_qualified_test_failure' if code==1 else 'execution_error'
    return 'passed' if code==0 else 'execution_error'


def eligible_detection(row):
    installed=row.get('after_sha256')
    return bool(row.get('mutant_index') is not None and row.get('control_passed')
                and row.get('mutation_applied') and row.get('bytes_changed')
                and row.get('execution_setup_qualified') and row.get('test_executed')
                and isinstance(installed,str) and len(installed)==64
                and row.get('container_source_sha256')==installed
                and row.get('outcome')=='execution_qualified_test_failure')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--benchmark',type=Path,required=True);parser.add_argument('--service',choices=['fastapi','nestjs-realworld','todoapp'],required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    bench=args.benchmark.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    service=args.service;service_dir=bench/'services'/service;working=service_dir/'working';start=time.monotonic()
    report={'kind':'restestbench_mutant_runtime_v1','upstream_commit':PIN,'service':service,'expected_keys':[],'trials':[],'commands':[],'terminal':'initializing','paid_model_calls':0}
    def save():
        report['unattempted_keys']=[k for k in report['expected_keys'] if k not in {r['key'] for r in report['trials']}]
        temporary=out/'observations.tmp';temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(out/'observations.json')
    def run(label,command,cwd=bench,timeout=120,input_text=None):
        begun=time.monotonic();log=out/(label+'.log');timed_out=False
        effective_timeout=timeout if label in ['final-containers','cleanup'] else min(timeout,max(1,35*60-(begun-start)))
        with log.open('w') as stream:
            process=subprocess.Popen(command,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,text=True,start_new_session=True)
            try:process.communicate(input_text,timeout=effective_timeout)
            except subprocess.TimeoutExpired:
                timed_out=True;os.killpg(process.pid,signal.SIGKILL);process.communicate()
        row={'label':label,'command':command,'return_code':process.returncode,'timeout':timed_out,'effective_timeout_seconds':effective_timeout,'elapsed_seconds':round(time.monotonic()-begun,3),'log':log.name};report['commands'].append(row);save();return row
    def checked(label,command,cwd=bench,timeout=120,input_text=None):
        row=run(label,command,cwd,timeout,input_text)
        if row['return_code']!=0 or row['timeout']:raise RuntimeError(label)
        return row
    compose_dir=service_dir if service=='todoapp' else working
    app={'fastapi':'backend','nestjs-realworld':'nestjs-realworld','todoapp':'todoapi'}[service]
    def compose(label,tail,timeout=120,input_text=None):return checked(label,['docker','compose']+tail,compose_dir,timeout,input_text)
    url={'fastapi':'http://localhost:8000/docs','nestjs-realworld':'http://localhost:3000/api/tags','todoapp':'http://localhost:5000/scalar/v1'}[service]
    def health(label):
        attempts=[];begun=time.monotonic()
        while time.monotonic()-begun<60 and time.monotonic()-start<35*60:
            try:
                with urllib.request.urlopen(url,timeout=3) as response:status=response.status
                attempts.append({'status':status})
                if status==200:
                    (out/(label+'.json')).write_text(json.dumps(attempts));return
            except Exception as exc:attempts.append({'error':type(exc).__name__})
            time.sleep(2)
        (out/(label+'.json')).write_text(json.dumps(attempts));raise RuntimeError(label)
    def reset(prefix):
        if service=='todoapp':
            compose(prefix+'-clean',['down','-v']);compose(prefix+'-restart',['up','-d',app],timeout=180)
        else:compose(prefix+'-restart',['restart',app])
        health(prefix+'-restart-health')
        if service=='fastapi':
            compose(prefix+'-schema',['exec','-T','db','psql','-v','ON_ERROR_STOP=1','-U','postgres','-d','app','-c','DROP SCHEMA public CASCADE; CREATE SCHEMA public;'])
            compose(prefix+'-migrate',['exec','-T',app,'alembic','upgrade','head'])
            compose(prefix+'-seed',['exec','-T',app,'python','app/initial_data.py'])
        elif service=='nestjs-realworld':
            tables=['user','article','comment','tag','follows','user_favorites_article']
            sql='SET FOREIGN_KEY_CHECKS=0;\n'+''.join('TRUNCATE TABLE `'+table+'`;\n' for table in tables)+'SET FOREIGN_KEY_CHECKS=1;\n'
            compose(prefix+'-truncate',['exec','-T','db','mysql','-u','nestjs','-ppassword','nestjsrealworld'],input_text=sql)
            sql=''.join('SELECT COUNT(*) FROM `'+table+'`;\n' for table in tables)
            compose(prefix+'-empty-check',['exec','-T','db','mysql','-N','-B','-u','nestjs','-ppassword','nestjsrealworld'],input_text=sql)
            counts=[int(line.strip()) for line in (out/(prefix+'-empty-check.log')).read_text().splitlines() if line.strip().isdigit()]
            if counts!=[0]*6:raise RuntimeError(prefix+'-nonempty-reset')
        health(prefix+'-health')
        compose(prefix+'-container-id',['ps','-q',app])
        container=(out/(prefix+'-container-id.log')).read_text().strip()
        if len(container)!=64 or any(c not in '0123456789abcdef' for c in container):raise RuntimeError(prefix+'-container-id')
        checked(prefix+'-container-state',['docker','inspect',container,'--format','{{json .State}}'])
        state=json.loads((out/(prefix+'-container-state.log')).read_text());assert state['Running']
        return {'id':container,'started_at':state['StartedAt'],'pid':state['Pid']}
    pristine={};last_container=None
    try:
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=bench,text=True).strip()==PIN
        spec=importlib.util.spec_from_file_location('upstream_mutator',bench/'src/mutator.py');module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
        requirements=[module.Requirement.from_file(p) for p in (bench/'data/requirements'/service).glob('requirement_*.json')];requirements.sort(key=lambda r:r.id)
        assert [r.id for r in requirements]==list(range(1,{'fastapi':63,'nestjs-realworld':29,'todoapp':14}[service]+1))
        assert sum(len(r.mutants) for r in requirements)=={'fastapi':141,'nestjs-realworld':65,'todoapp':22}[service]
        for req in requirements:
            assert req.service==service
            report['expected_keys'].append(f'req-{req.id}-valid')
            for index,mutant in enumerate(req.mutants):
                report['expected_keys'].append(f'req-{req.id}-mut-{index}')
                relative=Path(mutant.file);assert not relative.is_absolute() and '..' not in relative.parts
                pristine[mutant.file]=(service_dir/'original'/relative).read_bytes()
        save();checked('versions',[sys.executable,'-m','pip','freeze']);shutil.copytree(service_dir/'original',working)
        hashes={}
        for directory in [working,bench/'data/tests'/service,bench/'data/requirements'/service]:
            for file in sorted(directory.rglob('*')):
                if file.is_file():hashes[str(file.relative_to(bench))]=digest(file.read_bytes())
        (out/'input-sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
        compose('build',['build',app],timeout=600)
        compose('start',['up','-d',app]+(['mailcatcher'] if service=='fastapi' else []),timeout=240);health('initial-health');compose('images',['images','--format','json'])
        halted=False
        for req in requirements:
            control_passed=False
            for index,mutant in [(None,None)]+list(enumerate(req.mutants)):
                if time.monotonic()-start>=35*60:report['terminal']='soft_limit';halted=True;break
                key=f'req-{req.id}-valid' if mutant is None else f'req-{req.id}-mut-{index}'
                row={'key':key,'requirement_id':req.id,'mutant_index':index,'control_passed':control_passed,'test_executed':False,'mutation_applied':False,'bytes_changed':False}
                stage='source_restore'
                try:
                    for path,raw in pristine.items():(working/path).write_bytes(raw)
                    if mutant is not None:
                        assert control_passed;stage='mutation_install'
                        row['target']=mutant.file;row['before_sha256']=digest(pristine[mutant.file])
                        row['mutation_applied']=module.Mutator(working).apply_mutation(mutant)
                        installed=(working/mutant.file).read_bytes();row['after_sha256']=digest(installed);row['bytes_changed']=installed!=pristine[mutant.file]
                        if not row['mutation_applied'] or not row['bytes_changed']:raise RuntimeError(key+'-not-applied-changed')
                    stage='reset_or_readiness';row['container']=reset(key)
                    if last_container is not None and row['container']['id']==last_container['id'] and row['container']['started_at']==last_container['started_at']:raise RuntimeError(key+'-process-not-restarted')
                    last_container=row['container']
                    if mutant is not None:
                        stage='installed_source_verification'
                        target={'fastapi':'/app/'+mutant.file.removeprefix('backend/'),'nestjs-realworld':'/app/'+mutant.file,'todoapp':'/src/'+mutant.file}[service]
                        compose(key+'-installed-source',['exec','-T',app,'sha256sum',target])
                        row['container_source_sha256']=(out/(key+'-installed-source.log')).read_text().split()[0]
                        assert row['container_source_sha256']==row['after_sha256']
                    row['execution_setup_qualified']=True
                    stage='test_execution';test=bench/'data/tests'/service/f'test_{req.id}.py';row['test_sha256']=digest(test.read_bytes());junit=out/(key+'.xml')
                    result=run(key+'-test',[sys.executable,'-m','pytest',str(test),'-v','--tb=short','--junitxml='+str(junit)],timeout=60)
                    row.update(test_executed=True,return_code=result['return_code'],timeout=result['timeout']);totals=None
                    if junit.exists():
                        suites=list(ET.parse(junit).getroot().iter('testsuite'));totals={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','errors','failures','skipped']};row['junit']=totals
                    row['outcome']=classify(result['return_code'],result['timeout'],totals)
                    if mutant is not None and row['outcome']=='passed':row['outcome']='survived'
                except Exception as exc:row.update(outcome=stage+'_failure',error=type(exc).__name__+': '+str(exc))
                row['candidate_detection']=eligible_detection(row)
                report['trials'].append(row);save()
                if row['outcome'] not in ['passed','survived']:run(key+'-service-logs',['docker','compose','logs','--no-color','--tail','100',app],compose_dir)
                if mutant is None:
                    control_passed=row['outcome']=='passed'
                    if not control_passed:report['terminal']='valid_control_failure';halted=True;break
            if halted:break
        if not halted:report['terminal']='completed'
    except Exception as exc:report['terminal']='infrastructure_failure';report['error']=type(exc).__name__+': '+str(exc)
    finally:
        if working.exists():
            for path,raw in pristine.items():
                if (working/path).parent.exists():(working/path).write_bytes(raw)
        if compose_dir.exists():
            run('final-containers',['docker','compose','ps','-a','--format','json'],compose_dir)
            run('cleanup',['docker','compose','down','-v'],compose_dir)
        save()
    print(json.dumps({'service':service,'terminal':report['terminal'],'trials':len(report['trials']),'unattempted':len(report['unattempted_keys'])}))
    return 0 if report['terminal']=='completed' else 1

if __name__=='__main__':sys.exit(main())
