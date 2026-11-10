"""Source-qualified PetClinic v4 cost and semantic evidence loading."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.repetition import require
from mixed_interface.campaign_v2 import validate_plan
from petclinic_prefix_outcomes_v3 import pair_terminal
from petclinic_branch_cost_validation_v1 import validate_cost,finite
CONTROL_SHA='716c5ffeed77f00146038441324a9ba6f4a863681cdd3b1c9e7c23cd9b50800d'
CONTROL='manifests/petclinic-expanded-batches-v3.json'
REGISTRY='manifests/petclinic-candidates-v1.json'
RUNNER='scripts/run_petclinic_pair_job_v4.mjs'
BINDING='scripts/petclinic_job_binding_v3.mjs'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def contract(batch):
    require(sha(ROOT/CONTROL)==CONTROL_SHA,'Control contract differs')
    c=read(ROOT/CONTROL)
    require(batch in c['batches'],'Unregistered batch')
    validate_plan(c['batches'][batch]['plan'])
    require(sha(ROOT/'manifests/petclinic-prefix-policy-v3.json')==c['prefix_policy_sha256'],'Prefix policy differs')
    require(sha(ROOT/REGISTRY)==c['registry_sha256'],'Registry differs')
    return {**c,**c['batches'][batch]}

def validate_job(job,batch):
    c=contract(batch);require(job in c['allowed_jobs'],'Unregistered job')
    return next(e for e in read(ROOT/REGISTRY)['candidates'] if e['id']==job['pair_id'])

def read_job(directory,job,execution,batch):
    directory=Path(directory);expected=validate_job(job,batch);run=directory/'run'
    require(execution.get('exit_confirmed') is True and not execution.get('errors') and execution.get('returncode')==0,'Runner exit not clean')
    require(read(directory/'job.json')==job,'Job differs')
    s=read(run/'summary.json')
    require(s['kind']=='petclinic_timed_pair_v4' and s['batch']==batch and s['job']==job and s['job_sha256']==sha(directory/'job.json')==sha(run/'job.json'),'Executed job differs')
    require(s['controls_sha256']==sha(run/'controls.json')==CONTROL_SHA,'Executed contract differs')
    require(s['registry_sha256']==sha(run/'registered-candidates.json')==contract(batch)['registry_sha256'],'Executed registry differs')
    for archived,live,key in [('petclinic_branch_cost_v1.mjs','scripts/petclinic_branch_cost_v1.mjs','branch_cost_helper_sha256'),('executed_boundary_slice.mjs',RUNNER,'runner_sha256'),('petclinic_job_binding_v3.mjs',BINDING,'binding_sha256'),('petclinic_integrity.mjs','scripts/petclinic_integrity.mjs','integrity_helper_sha256'),('petclinic_response_capture.mjs','scripts/petclinic_response_capture.mjs','capture_helper_sha256'),('petclinic_cleanup.mjs','scripts/petclinic_cleanup.mjs','cleanup_helper_sha256')]:
        require(sha(run/archived)==s[key]==sha(ROOT/live),'Executed source differs: '+live)
    require(s.get('finished_at') and s.get('backend_stopped') is True and not s.get('stopped_after_harness_or_pair_failure'),'Incomplete job')
    oracles={'api':'api_semantic','ui':'fresh_ui'}
    require([b['oracle'] for b in s['branches']]==[oracles[b['continuation']] for b in job['branches']],'Branch order differs')
    registry=read(run/'registered-candidates.json');spec=next(c for c in registry['candidates'] if c['id']==job['pair_id'])
    require(finite(s['common_browser_startup_s']),'Common browser setup timing missing')
    costs={}
    branches={};evidence={'summary':sha(run/'summary.json'),'job':sha(directory/'job.json'),'execution':sha(directory/'execution.json')}
    for declared,observed in zip(job['branches'],s['branches']):
        oracle=oracles[declared['continuation']];name=job['pair_id']+'-'+oracle+'.json'
        require(observed['candidate_id']==job['pair_id'] and observed['result']==name,'Branch binding differs')
        raw=read(run/name)
        require(raw['candidate_id']==job['pair_id'] and raw['oracle']==oracle and raw['status']==observed['status'],'Raw binding differs')
        cost_name=job['pair_id']+'-'+oracle+'-cost.json'
        require(observed['cost_record']==cost_name,'Cost sidecar name differs')
        cost=validate_cost(read(run/cost_name),(run/name).read_bytes())
        require(cost['candidate_id']==job['pair_id'] and cost['oracle']==oracle,'Cost identity differs')
        require(cost['measurement_status']=='complete_interval' and observed['cost_status']==cost['measurement_status'] and
                finite(observed['branch_total_s']) and observed['branch_total_s']==cost['branch_total_s'],'Complete branch cost missing')
        costs[declared['continuation']]=cost;evidence[cost_name]=sha(run/cost_name)
        branches[declared['continuation']]=raw;evidence[name]=sha(run/name)
    require({p.name for p in run.glob('*-cost.json')}=={job['pair_id']+'-'+oracles[b['continuation']]+'-cost.json' for b in job['branches']},'Cost record inventory differs')
    ordered=[costs[b['continuation']] for b in job['branches']]
    require(ordered[1]['started_monotonic_s']>=ordered[0]['finished_monotonic_s'],'Branch timing overlaps or is reordered')
    require(sum(c['branch_total_s'] for c in ordered)<=120,'Recorded branches exceed pair deadline')
    result=pair_terminal(job['job_id'],branches,spec,registry,cleanup_confirmed=True,evidence=evidence)
    result['branch_costs']=costs
    result['common_browser_startup_s']=s['common_browser_startup_s']
    return result
