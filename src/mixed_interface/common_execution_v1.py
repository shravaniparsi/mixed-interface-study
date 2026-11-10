"""Fresh-attempt bridge. Runtime adapters execute and independently load raw evidence."""
from copy import deepcopy
from pathlib import Path
import hashlib,json,time,uuid
from .common_bindings_v1 import bind_job
from .repetition import require,digest
from .terminal_outcomes import terminal,validate


def read(path):return json.loads(Path(path).read_bytes())
def write(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def inventory(path):
    require(not any(p.is_symlink() for p in path.rglob('*')),'Symlink in attempt evidence')
    return {str(p.relative_to(path)):sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


def translate(bound,loaded,receipt_sha):
    source=loaded['terminal'];validate(source)
    require(source['outcome']['job_id']==bound['runtime_job']['job_id'],'Runtime returned foreign job')
    outcome=deepcopy(source['outcome']);outcome['job_id']=bound['campaign_job']['job_id']
    # Preserve kind, semantic signature and original terminal; only the outer identity changes.
    return terminal(outcome,source['kind'],{'runtime_terminal':digest(source),'attempt_receipt':receipt_sha})


def execute(root,registry,checked,job,adapter,run_identity,initial_outcomes=None):
    bound=bind_job(registry,checked,job,initial_outcomes)
    require(bound['runtime_profile']==adapter.profile,'Unsupported runtime profile')
    require(isinstance(run_identity,str) and bool(run_identity),'Run identity missing')
    namespace=bound['attempt_namespace']
    require(Path(namespace).name==namespace and namespace not in ('.','..'),'Unsafe attempt namespace')
    directory=Path(root)/namespace;directory.mkdir(exist_ok=False)
    write(directory/'binding.json',bound)
    start={'attempt_id':uuid.uuid4().hex,'run_identity':run_identity,'binding_sha256':digest(bound),
           'started_monotonic_s':time.monotonic(),'status':'started','new_primary_samples':0}
    write(directory/'started.json',start)
    runtime=directory/'runtime';runtime.mkdir()
    try:
        adapter.execute(runtime,deepcopy(bound))
        loaded=adapter.load(runtime,deepcopy(bound))
        validate(loaded['terminal'])
        receipt={'start':start,'binding_sha256':digest(bound),'runtime_files_sha256':inventory(runtime),
                 'runtime_observations_sha256':digest(loaded),'finished_monotonic_s':time.monotonic(),
                 'status':'completed','new_primary_samples':0,'primary_freeze_complete':False}
        require(receipt['finished_monotonic_s']>=start['started_monotonic_s'],'Invalid attempt clock')
        value=translate(bound,loaded,digest(receipt))
        write(directory/'runtime-observations.json',loaded);write(directory/'receipt.json',receipt)
        write(directory/'terminal.json',value)
        return value
    except BaseException as error:
        write(directory/'failure.json',{'type':type(error).__name__,'error':str(error),'attempt_id':start['attempt_id'],
              'status':'incomplete','new_primary_samples':0})
        raise


def replay(directory,registry,checked,job,adapter,run_identity,initial_outcomes=None):
    directory=Path(directory);bound=bind_job(registry,checked,job,initial_outcomes)
    require(bound['runtime_profile']==adapter.profile,'Unsupported runtime profile')
    require(directory.name==bound['attempt_namespace'] and read(directory/'binding.json')==bound,'Attempt binding differs')
    require(not (directory/'failure.json').exists(),'Failed attempt cannot be qualified')
    start=read(directory/'started.json');receipt=read(directory/'receipt.json')
    require(start['status']=='started' and start['new_primary_samples']==0 and start['run_identity']==run_identity and
            start['binding_sha256']==digest(bound),'Attempt provenance differs')
    require(isinstance(start['attempt_id'],str) and len(start['attempt_id'])==32 and
            all(c in '0123456789abcdef' for c in start['attempt_id']),'Attempt identity malformed')
    require(receipt['start']==start and receipt['binding_sha256']==digest(bound) and receipt['status']=='completed' and
            receipt['new_primary_samples']==0 and receipt['primary_freeze_complete'] is False,'Receipt scope or identity differs')
    import math
    clocks=[start['started_monotonic_s'],receipt['finished_monotonic_s']]
    require(all(type(t) in (int,float) and math.isfinite(t) and t>=0 for t in clocks) and clocks[1]>=clocks[0],'Attempt clocks differ')
    require(inventory(directory/'runtime')==receipt['runtime_files_sha256'],'Runtime inventory or bytes differ')
    loaded=adapter.load(directory/'runtime',deepcopy(bound))
    require(loaded==read(directory/'runtime-observations.json') and digest(loaded)==receipt['runtime_observations_sha256'],'Runtime reconstruction differs')
    value=translate(bound,loaded,digest(receipt))
    require(value==read(directory/'terminal.json'),'Common terminal differs')
    require({p.name for p in directory.iterdir()}=={'binding.json','started.json','runtime','runtime-observations.json','receipt.json','terminal.json'},'Attempt file inventory differs')
    return value
