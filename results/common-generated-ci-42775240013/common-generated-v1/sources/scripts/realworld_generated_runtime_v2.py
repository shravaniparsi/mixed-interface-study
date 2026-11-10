"""Runtime branch loader for the exact two exposed generated reference pairs."""
import json,math
from pathlib import Path
from realworld_generated_bindings_v1 import ROOT,plan,case_for,extract
from realworld_generated_loader_v1 import sha,SOURCES as PRIOR
from realworld_generated_terminal_v1 import compare
from mixed_interface.repetition import require
SOURCES=sorted(set(PRIOR+('scripts/realworld_generated_worker_v2.py','scripts/realworld_case_worker.py',
 'scripts/realworld_generated_runtime_v2.py','scripts/run_realworld_generated_controls_v2.py',
 'scripts/validate_realworld_generated_controls_v2.py','scripts/run_realworld_pilot.py',
 'scripts/ci/owned_process_scope.py','scripts/ci/prepare_realworld.py','manifests/realworld-python-lock.txt',
 '.github/workflows/realworld_generated_v2.yml','protocol/realworld-generated-runtime-v2.md')))

def read(path):return json.loads(Path(path).read_bytes())
def jobs():return [j for j in plan()['jobs'] if j['pair']['intervention']=='route_only']

def branch(directory,job,channel,fixture_sha):
    d=Path(directory);spec=case_for(job,channel)
    require(job in jobs(),'Only exposed reference jobs admitted')
    require(read(d/'case.json')==spec,'Executed case changed')
    run=read(d/'run.json');raw=read(d/'observation.json')
    require(run['case_id']==spec['case_id'] and run['route']==[o['interface'] for o in spec['operations']],'Route/case differs')
    require(run['reset_sha256']==sha(d/'reset.sqlite3')==fixture_sha,'Reset bytes differ')
    require(read(d/'reset.json')=={'sha256':fixture_sha,'independent_offline_reset':True},'Reset record differs')
    require(run['raw_sha256']==sha(d/'observation.json'),'Raw trace hash differs')
    require(run['exit_code']==0 and not run['timed_out'] and run['cleanup_confirmed'] is True,'Worker lifecycle incomplete')
    execution=read(d/'execution.json')
    require(execution['exit_confirmed'] is True and execution['returncode']==0 and not execution['errors'],'Owned worker exit unconfirmed')
    for name in ('cleanup.json','parent-browser-cleanup.json'):
        c=read(d/name);require(c['ok'] is True and not c.get('worker_process_cleanup_errors'),'Browser/backend cleanup unconfirmed')
    require(read(d/'port-check.json')=={'backend_port_closed':True},'Backend remains available')
    a,b,total=(run[k] for k in ('started_monotonic','finished_monotonic','branch_total_s'))
    require(all(type(x) in (int,float) and math.isfinite(x) for x in (a,b,total)) and b>=a and total>0 and abs((b-a)-total)<1e-6 and total<=95,'Branch interval invalid')
    result=extract(job,channel,raw,run)
    require(result['components']['execution_evidence_complete'],'Incomplete branch evidence')
    return raw,run
