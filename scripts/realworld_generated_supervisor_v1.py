"""Bounded synthetic lifecycle preflight. No application dispatch interface."""
import json,math,subprocess,sys,time
from pathlib import Path
from realworld_generated_bindings_v1 import ROOT,case_for,extract
from realworld_generated_loader_v1 import sha
sys.path.insert(0,str(ROOT/'scripts/ci'))
from owned_process_scope import stop_owned_group,defer_stop_signals,interruption_as_exception
WORKER=ROOT/'tests/fixtures/generated_lifecycle_worker_v1.py'


def run_branch(job,channel,source,output,*,mode='success',deadline_s=5):
    spec=case_for(job,channel)
    if mode not in ('success','timeout','failure'):raise ValueError('Unknown synthetic mode')
    if type(deadline_s) not in (int,float) or not math.isfinite(deadline_s) or not 0<deadline_s<=30:raise ValueError('Invalid preflight deadline')
    source=Path(source).resolve();output=Path(output).resolve()
    if source==output or source in output.parents:raise ValueError('Output must be separate from inputs')
    # Common preparation occurs outside the branch timer; worker copies reset bytes inside it.
    if not (source/'fixture.bin').is_file() or not (source/'raw.json').is_file():raise ValueError('Missing synthetic inputs')
    fixture_sha=sha(source/'fixture.bin');output.mkdir(parents=True,exist_ok=False)
    record={'evidence_origin':'synthetic_lifecycle_preflight','case_id':spec['case_id'],
            'route':[o['interface'] for o in spec['operations']],'runtime_dispatch_qualified':False,
            'primary_freeze_complete':False,'status':'running','timed_out':False,'interrupted':False,
            'worker_sha256':sha(WORKER),'deadline_s':deadline_s,'cleanup_reserve_s':1.5}
    child=None;began=time.monotonic();cleanup={};validation=None
    try:
        with interruption_as_exception(), (output/'worker.log').open('x') as log:
            child=subprocess.Popen([sys.executable,str(WORKER),str(source),str(output),mode],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            child.wait(timeout=max(.001,deadline_s-(time.monotonic()-began)))
            record['exit_code']=child.returncode
            if child.returncode!=0:record['status']='worker_failure'
            else:
                if sha(output/'reset.bin')!=fixture_sha:raise ValueError('Reset differs')
                raw=json.loads((output/'raw.json').read_bytes())
                run={'case_id':spec['case_id'],'route':record['route'],'status':'completed','exit_code':0}
                validation=extract(job,channel,raw,run)
                record['status']='validated_synthetic_branch' if validation['components']['execution_evidence_complete'] else 'incomplete_evidence'
                if time.monotonic()-began>deadline_s:record.update(timed_out=True,status='case_timeout')
    except subprocess.TimeoutExpired:record.update(timed_out=True,status='case_timeout')
    except (KeyboardInterrupt,SystemExit):record.update(interrupted=True,status='interrupted')
    except Exception as error:record.update(status='environment_failure',error=type(error).__name__+': '+str(error))
    finally:
        with defer_stop_signals():
            if child is not None:cleanup=stop_owned_group(child,grace=.5,kill_wait=.5)
            if child is None or not cleanup.get('exit_confirmed') or cleanup.get('errors'):record['status']='cleanup_unconfirmed'
        ended=time.monotonic()
        record.update(branch_started_monotonic=began,branch_finished_monotonic=ended,
                      branch_total_s=ended-began,cleanup=cleanup,reset_sha256=fixture_sha,
                      timing_scope='worker launch, independent reset, raw capture, validation and owned direct-child cleanup; excludes common preparation and report serialization',
                      detached_descendant_cleanup_qualified=False)
        (output/'supervisor.json').write_text(json.dumps(record,indent=2)+'\n')
        if validation is not None:(output/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    return record
