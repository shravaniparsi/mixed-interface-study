#!/usr/bin/env python3
"""Read-only raw replay; incomplete attempts remain incomplete, not replacements."""
import json,sys
from pathlib import Path
from primary_preflight_v1 import ROOT,PREPARATION,FREEZE,read,sha,sources,environment,units
from primary_attempt_v1 import replay
from mixed_interface.common_execution_v1 import inventory
from mixed_interface.primary_batches_v1 import drive
from mixed_interface.repetition import require

def validate(root):
    root=Path(root);cert=read(root/'plan.json');report=read(root/'report.json');prep=read(PREPARATION);sources(prep)
    require(cert['preparation_sha256']==sha(PREPARATION) and cert['source_sha256']==prep['source_sha256'],'Preparation differs')
    require(cert['unit'] in units(cert['mode']) and report['mode']==cert['mode'] and report['batch_id']==cert['unit']['batch_id'],'Unit differs')
    require(cert['primary_freeze_complete']==(cert['mode']!='smoke') and cert['freeze_sha256']==(None if cert['mode']=='smoke' else sha(FREEZE)),'Freeze differs')
    require({k:v for k,v in inventory(root).items() if k!='report.json'}==report['retained_files_sha256'],'Evidence inventory differs')
    app=cert['unit']['application'];require(set(cert['environment_sha256'])=={'runtime-versions.json','browser.json',app+'-bootstrap.json'},'Environment inventory differs')
    for p,h in cert['environment_sha256'].items():require(sha(root/p)==h,'Environment bytes differ')
    environment(prep,app,read(root/'runtime-versions.json'),read(root/'browser.json'),read(root/(app+'-bootstrap.json')))
    require(read(root/'runtime-versions.json')['runner']['GITHUB_SHA']==cert['source_commit'],'Source commit differs')
    require(read(root/'runtime-versions.json')['runner']['GITHUB_RUN_ID']+':'+read(root/'runtime-versions.json')['runner']['GITHUB_RUN_ATTEMPT']==cert['run_identity'],'Hosted run differs')
    if not (root/'campaign.json').exists():
        require(report['status']=='incomplete' and 'error' in report,'Missing campaign without setup failure')
        return {'verified_retention':True,'qualified_observations':False,'batch_id':report['batch_id'],'status':'setup_failure','run_identity':cert['run_identity'],'mode':cert['mode']}
    recorded=read(root/'campaign.json');jobs={j['attempt_id']:j for j in cert['unit']['jobs']};values={};identities=[]
    fixture_sha=sha(root/'fixture.sqlite3') if (root/'fixture.sqlite3').exists() else None
    for value in recorded['observations']:
        aid=value['attempt_id'];require(aid in jobs,'Foreign recorded observation')
        values[aid]=replay(root/aid,jobs[aid],cert['run_identity'],fixture_sha);require(values[aid]==value,'Observation differs')
        identities.append(read(root/aid/'started.json')['attempt_uuid'])
    require(len(identities)==len(set(identities)),'Attempt identity reused')
    require({p.name for p in root.iterdir() if p.is_dir()}==set(recorded['started']),'Attempt directories differ')
    observed=[]
    def execute(job):
        aid=job['attempt_id'];observed.append(aid)
        if aid in values:return values[aid]
        failure=read(root/aid/'failure.json')
        require(recorded['status']=='halted_executor_error' and failure['type']==recorded['error_type'] and failure['error']==recorded['error'],'Incomplete failure differs')
        raise type(failure['type'],(Exception,),{})(failure['error'])
    checkpoints=[]
    try:result=drive(cert['unit'],execute,checkpoints.append)
    except Exception:result=checkpoints[-1]
    require(result==recorded and observed==recorded['started'],'Ledger replay differs')
    require(report['status']==recorded['status'] or report['status']=='incomplete','Report differs')
    return {'verified_retention':True,'qualified_observations':report['cleanup_confirmed'] and recorded['status']!='halted_executor_error',
            'batch_id':report['batch_id'],'status':recorded['status'],'run_identity':cert['run_identity'],'mode':cert['mode'],
            'source_commit':cert['source_commit'],'observations':len(values),'ledger':recorded,
            'primary_freeze_complete':cert['primary_freeze_complete']}
if __name__=='__main__':print(json.dumps(validate(sys.argv[1]),indent=2))
