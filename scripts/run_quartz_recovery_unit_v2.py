#!/usr/bin/env python3
"""Run one declared diagnostic unit; never authorize a primary run without freeze."""
import argparse,os,shutil,sys,time
from pathlib import Path
from quartz_recovery_preflight_v2 import ROOT,PREPARATION,FREEZE,read,sha,sources,environment,units
from primary_runtime_v1 import Runtime
from primary_attempt_v1 import execute
from mixed_interface.common_execution_v1 import write,inventory
from mixed_interface.primary_batches_v1 import drive
from mixed_interface.repetition import require
sys.path.insert(0,str(ROOT/'scripts/ci'))
from owned_process_scope import interruption_as_exception,defer_stop_signals

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',required=True);parser.add_argument('--batch',required=True);args=parser.parse_args()
    selected=units(args.mode);unit=next((u for u in selected if u['batch_id']==args.batch),None);require(unit is not None,'Undeclared unit')
    artifact=Path(os.environ['CI_ARTIFACT_DIR']);out=artifact/'quartz-recovery-unit-v2';out.mkdir(exist_ok=False)
    preparation=read(PREPARATION);app=unit['application'];versions=read(artifact/'runtime-versions.json');browser=read(artifact/'browser.json');bootstrap=read(artifact/(app+'-bootstrap.json'))
    environment(preparation,app,versions,browser,bootstrap)
    for name in ('runtime-versions.json','browser.json',app+'-bootstrap.json'):shutil.copyfile(artifact/name,out/name)
    cert={'source_commit':os.environ['GITHUB_SHA'],'run_identity':os.environ['GITHUB_RUN_ID']+':'+os.environ['GITHUB_RUN_ATTEMPT'],
          'mode':args.mode,'unit':unit,'preparation_sha256':sha(PREPARATION),'source_sha256':preparation['source_sha256'],
          'environment_sha256':{n:sha(out/n) for n in ('runtime-versions.json','browser.json',app+'-bootstrap.json')},
          'primary_freeze_complete':args.mode!='smoke','freeze_sha256':None if args.mode=='smoke' else sha(FREEZE)}
    write(out/'plan.json',cert);runtime=Runtime(app,out,artifact,os.environ['STUDY_RUNTIME']);report={'status':'incomplete','mode':args.mode,'batch_id':unit['batch_id']}
    started=time.monotonic()
    try:
        runtime.prepare(unit['jobs'])
        fixture_sha=sha(out/'fixture.sqlite3') if (out/'fixture.sqlite3').exists() else None
        def run(job):sources(preparation);return execute(out,job,runtime,cert['run_identity'],fixture_sha)
        ledger=drive(unit,run,lambda state:write(out/'campaign.json',state));report['status']=ledger['status']
    except BaseException as error:report.update(error_type=type(error).__name__,error=str(error))
    finally:
        with defer_stop_signals():
            report['cleanup_confirmed']=runtime.close();report['outer_elapsed_s']=time.monotonic()-started
            if not report['cleanup_confirmed']:report['status']='incomplete'
            report['retained_files_sha256']=inventory(out);write(out/'report.json',report)
    return 0 if report['status'] in ('completed_observations','halted_terminal_outcome') else 1
if __name__=='__main__':
    with interruption_as_exception():raise SystemExit(main())
