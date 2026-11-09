"""Immutable six-control PetClinic job binding and evidence extraction."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.repetition import require
from mixed_interface.campaign_v2 import validate_plan
from petclinic_terminal_outcomes import pair_terminal
CONTROL_SHA='b7b5751dcdb6437c64d903964b1817be6fc08675a95eba6cc5837344fa1707ae'
CONTROL='manifests/petclinic-terminal-controls-v2.json'
REGISTRY='manifests/petclinic-candidates-v1.json'
RUNNER='scripts/run_petclinic_pair_job_v2.mjs'
BINDING='scripts/petclinic_job_binding.mjs'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def contract():
    require(sha(ROOT/CONTROL)==CONTROL_SHA,'Control contract differs')
    c=read(ROOT/CONTROL);validate_plan(c['plan'])
    require(sha(ROOT/REGISTRY)==c['registry_sha256'],'Registry differs')
    return c

def validate_job(job):
    c=contract();require(job in c['allowed_jobs'],'Unregistered job')
    return next(e for e in c['selection'] if e['id']==job['pair_id'])

def read_job(directory,job,execution):
    directory=Path(directory);expected=validate_job(job);run=directory/'run'
    require(execution.get('exit_confirmed') is True and not execution.get('errors') and execution.get('returncode')==0,'Runner exit not clean')
    require(read(directory/'job.json')==job,'Job differs')
    s=read(run/'summary.json')
    require(s['kind']=='petclinic_terminal_pair_v2' and s['job']==job and s['job_sha256']==sha(directory/'job.json')==sha(run/'job.json'),'Executed job differs')
    require(s['controls_sha256']==sha(run/'controls.json')==CONTROL_SHA,'Executed contract differs')
    require(s['registry_sha256']==sha(run/'registered-candidates.json')==contract()['registry_sha256'],'Executed registry differs')
    for archived,live,key in [('executed_boundary_slice.mjs',RUNNER,'runner_sha256'),('petclinic_job_binding.mjs',BINDING,'binding_sha256'),('petclinic_integrity.mjs','scripts/petclinic_integrity.mjs','integrity_helper_sha256'),('petclinic_response_capture.mjs','scripts/petclinic_response_capture.mjs','capture_helper_sha256'),('petclinic_cleanup.mjs','scripts/petclinic_cleanup.mjs','cleanup_helper_sha256')]:
        require(sha(run/archived)==s[key]==sha(ROOT/live),'Executed source differs: '+live)
    require(s.get('finished_at') and s.get('backend_stopped') is True and not s.get('stopped_after_harness_or_pair_failure'),'Incomplete job')
    oracles={'api':'api_semantic','ui':'fresh_ui'}
    require([b['oracle'] for b in s['branches']]==[oracles[b['continuation']] for b in job['branches']],'Branch order differs')
    registry=read(run/'registered-candidates.json');spec=next(c for c in registry['candidates'] if c['id']==job['pair_id'])
    branches={};evidence={'summary':sha(run/'summary.json'),'job':sha(directory/'job.json'),'execution':sha(directory/'execution.json')}
    for declared,observed in zip(job['branches'],s['branches']):
        oracle=oracles[declared['continuation']];name=job['pair_id']+'-'+oracle+'.json'
        require(observed['candidate_id']==job['pair_id'] and observed['result']==name,'Branch binding differs')
        raw=read(run/name)
        require(raw['candidate_id']==job['pair_id'] and raw['oracle']==oracle and raw['status']==observed['status'],'Raw binding differs')
        branches[declared['continuation']]=raw;evidence[name]=sha(run/name)
    return pair_terminal(job['job_id'],branches,spec,registry,expected,cleanup_confirmed=True,evidence=evidence)
