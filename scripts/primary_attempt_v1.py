"""Fresh native evidence receipt and independent reconstruction for primary units."""
from copy import deepcopy
from pathlib import Path
import time,uuid
from mixed_interface.common_execution_v1 import read,write,sha,inventory
from mixed_interface.repetition import require,digest
from mixed_interface.terminal_outcomes import terminal,validate
from primary_runtime_v1 import load

def normalized(attempt,loaded,receipt):
    raw=loaded['runtime_result'];base={'attempt_id':attempt['attempt_id'],'entry_kind':attempt['entry_kind'],
        'branch_total_s':loaded['branch_total_s'],'runtime_result_sha256':digest(raw),'receipt_sha256':digest(receipt)}
    if attempt['entry_kind']=='singleton':
        require(raw['paired_comparison_eligible'] is False and 'terminal' not in raw,'Singleton promoted')
        return {**base,'paired_comparison_eligible':False,'branch':deepcopy(raw['branch'])}
    source=raw['terminal'];validate(source)
    require(source['outcome']['job_id']==attempt['runtime']['job']['job_id'],'Runtime job identity differs')
    outcome=deepcopy(source['outcome']);outcome['job_id']=attempt['attempt_id']
    return {**base,'terminal':terminal(outcome,source['kind'],{'runtime_terminal':digest(source),'attempt_receipt':digest(receipt)})}

def execute(root,attempt,runtime,run_identity,fixture_sha=None):
    d=Path(root)/attempt['attempt_id'];d.mkdir(exist_ok=False);write(d/'attempt.json',attempt)
    start={'attempt_uuid':uuid.uuid4().hex,'run_identity':run_identity,'attempt_sha256':digest(attempt),'started_monotonic_s':time.monotonic()};write(d/'started.json',start)
    raw=d/'runtime';raw.mkdir()
    try:
        runtime.execute(raw,deepcopy(attempt));loaded=load(raw,attempt,fixture_sha)
        receipt={'start':start,'runtime_files_sha256':inventory(raw),'loaded_sha256':digest(loaded),'finished_monotonic_s':time.monotonic(),'status':'completed'}
        value=normalized(attempt,loaded,receipt)
        write(d/'loaded.json',loaded);write(d/'receipt.json',receipt);write(d/'observation.json',value);return value
    except BaseException as e:
        write(d/'failure.json',{'type':type(e).__name__,'error':str(e),'status':'incomplete','attempt_uuid':start['attempt_uuid']});raise

def replay(d,attempt,run_identity,fixture_sha=None):
    import math
    d=Path(d);require(not (d/'failure.json').exists(),'Incomplete attempt')
    require(read(d/'attempt.json')==attempt and d.name==attempt['attempt_id'],'Attempt differs')
    start=read(d/'started.json');receipt=read(d/'receipt.json')
    require(receipt['start']==start and start['run_identity']==run_identity and start['attempt_sha256']==digest(attempt),'Attempt provenance differs')
    require(isinstance(start['attempt_uuid'],str) and len(start['attempt_uuid'])==32 and all(c in '0123456789abcdef' for c in start['attempt_uuid']),'Invalid attempt identity')
    clocks=[start['started_monotonic_s'],receipt['finished_monotonic_s']]
    require(all(type(t) in (int,float) and math.isfinite(t) and t>=0 for t in clocks) and clocks[1]>=clocks[0],'Invalid attempt interval')
    require(receipt['status']=='completed' and receipt['runtime_files_sha256']==inventory(d/'runtime'),'Runtime bytes differ')
    loaded=load(d/'runtime',attempt,fixture_sha)
    require(loaded==read(d/'loaded.json') and digest(loaded)==receipt['loaded_sha256'],'Raw reconstruction differs')
    value=normalized(attempt,loaded,receipt);require(value==read(d/'observation.json'),'Observation differs')
    require({p.name for p in d.iterdir()}=={'attempt.json','started.json','runtime','loaded.json','receipt.json','observation.json'},'Attempt inventory differs')
    return value
