#!/usr/bin/env python3
"""Aggregate complete declared artifact inventory; never substitute failed units."""
from pathlib import Path
import argparse,json
from quartz_public_qualification_preflight_v1 import PREPARATION,FREEZE,units,read,sha
from validate_quartz_public_qualification_unit_v1 import validate
from mixed_interface.common_execution_v1 import inventory,write
from mixed_interface.repetition import require,digest

def collect(root,mode):
    root=Path(root);expected={u['batch_id']:u for u in units(mode)};records={};verification={};run_ids=set();commits=set()
    require(all(p.is_dir() and (p/'requested-unit.json').is_file() for p in root.iterdir()),'Unrecognized phase artifact')
    for request_path in sorted(root.glob('*/requested-unit.json')):
        folder=request_path.parent;request=read(request_path);bid=request['batch']
        require(request['mode']==mode and bid in expected and bid not in records,'Foreign or duplicate unit artifact')
        run_ids.add(request['run_identity']);commits.add(request['source_commit']);unitdir=folder/'quartz-public-qualification-unit-v1'
        if (unitdir/'plan.json').exists() and (unitdir/'report.json').exists():
            require(read(unitdir/'plan.json')['source_commit']==request['source_commit'],'Request/source commit differs')
            value=validate(unitdir);require(value['batch_id']==bid and value['run_identity']==request['run_identity'],'Request/certificate differs')
            record=value.get('ledger',{'batch_id':bid,'status':'halted_executor_error','started':[],'observations':[],
                'independent_sample_size':None,'error_type':'SetupFailure','error':'See retained setup evidence'})
        else:
            value={'verified_retention':True,'qualified_observations':False,'batch_id':bid,'status':'environment_setup_or_outer_failure','run_identity':request['run_identity']}
            record={'batch_id':bid,'status':'halted_executor_error','started':[],'observations':[],'independent_sample_size':None,
                    'error_type':'SetupOrOuterFailure','error':'No completed unit certificate; retained as failed, never replaced'}
        records[bid]=record;verification[bid]=value
    require(set(records)==set(expected),'Declared artifact inventory incomplete')
    require(len(run_ids)==len(commits)==1,'Phase cannot merge different hosted workflow attempts or source commits')
    # A single workflow attempt's matrix contains all predeclared units.
    return {'kind':'primary_unit_collection_v1','mode':mode,'preparation_sha256':sha(PREPARATION),'freeze_sha256':None if mode=='smoke' else sha(FREEZE),
            'run_identity':next(iter(run_ids)),'records':records,'verification':verification,'files_sha256':inventory(root),
            'all_units_retained':True,'all_units_qualified':all(v['qualified_observations'] for v in verification.values()),
            'primary_freeze_complete':mode!='smoke','independent_sample_size':None}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--mode',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    value=collect(a.root,a.mode);write(a.output,value);print(json.dumps({'units':len(value['records']),'all_units_qualified':value['all_units_qualified']}))
