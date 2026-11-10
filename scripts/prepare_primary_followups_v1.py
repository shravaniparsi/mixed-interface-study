#!/usr/bin/env python3
"""Register only policy-authorized follow-up units after complete phase retention."""
import argparse
from pathlib import Path
from primary_preflight_v1 import ROOT,PREPARATION,FREEZE,read,sha
from verify_primary_collection_v1 import verify
from mixed_interface.primary_batches_v1 import followups
from mixed_interface.common_execution_v1 import write
from mixed_interface.repetition import require

def prepare(initial_manifest,repetition,previous_manifest=None):
    initial=verify(initial_manifest);require(initial['mode']=='initial','Wrong initial phase')
    require(initial['freeze_sha256']==sha(FREEZE),'Initial freeze differs')
    previous=None
    if repetition==3:
        require(previous_manifest is not None,'Repetition two evidence missing');previous=verify(previous_manifest)
        require(previous['mode']=='repeat2' and previous['freeze_sha256']==sha(FREEZE),'Wrong repetition two phase')
    schedule=followups(read(PREPARATION)['plan'],initial['records'],repetition,previous['records'] if previous else None)
    for unit in schedule['batches']:
        initial_id=unit['batch_id'][:-1]+'1'
        require(initial['verification'][initial_id]['qualified_observations'],'A globally unqualified initial unit cannot authorize follow-ups')
        if previous is not None:
            second_id=unit['batch_id'][:-1]+'2'
            require(previous['verification'][second_id]['qualified_observations'],'A globally unqualified second repetition cannot authorize a third')
    output=ROOT/f'manifests/primary-execution-repeat{repetition}-v1.json';require(not output.exists(),'Follow-up registration already exists')
    value={'preparation_sha256':sha(PREPARATION),'freeze_sha256':sha(FREEZE),'initial_manifest_sha256':sha(initial_manifest),
           'previous_manifest_sha256':sha(previous_manifest) if previous_manifest else None,
           'initial':initial['records'],'previous':previous['records'] if previous else None,'schedule':schedule}
    write(output,value);return value
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--initial',type=Path,required=True);p.add_argument('--repetition',type=int,choices=[2,3],required=True);p.add_argument('--previous',type=Path);a=p.parse_args()
    v=prepare(a.initial,a.repetition,a.previous);print('Registered follow-up units:',len(v['schedule']['batches']))
