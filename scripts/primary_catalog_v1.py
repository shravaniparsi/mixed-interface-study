"""Exact runtime templates for all retained entries; no execution authorization."""
from copy import deepcopy
from pathlib import Path
import sys,importlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.common_execution_v1 import read,write,sha
from mixed_interface.repetition import require,digest
from mixed_interface.evaluation import digest as case_digest
from mixed_interface.campaign_v2 import build_plan

RW={
 'realworld_paired_controls':('rw_expanded','realworld_expanded_campaign','manifests/realworld-paired-controls-v1.json','scripts/run_realworld_pair_job_v3.py'),
 'realworld_field_controls':('rw_field','realworld_field_campaign','manifests/realworld-field-controls-v1.json','scripts/run_realworld_pair_job_v5.py'),
 'realworld_rejection_controls':('rw_rejection','realworld_rejection_campaign','manifests/realworld-rejection-controls-v1.json','scripts/run_realworld_pair_job_v4.py'),
 'identity':('rw_identity','realworld_identity_campaign','manifests/realworld-identity-controls-v1.json','scripts/run_realworld_pair_job_v7.py')}

def rw_template(row,cid=None):
    cid=cid or row['inventory_entry']['candidate_id']
    identity=row['inventory_entry']['candidate_id'] in ('profile-username-null','profile-username-length60','profile-username-length61')
    family='identity' if identity else row['path_family']
    if family in RW:
        profile,module,registry_path,runner=RW[family];m=importlib.import_module(module);registry=read(ROOT/registry_path)
        job=next(j for j in m.plan_for(registry)['schedule']['initial_jobs'] if j['pair_id']==cid)
        spec=m.validate_job(job,registry)
        loader='realworld_identity_database_job_v7' if identity else module
        return {'profile':profile,'runner':runner,'loader':loader,'registry_path':registry_path,'job':job,'specs':{c:spec for c in ('api','ui')},'context':{}}
    from realworld_legacy_jobs_v8 import selection,plan_for,validate_job
    registry=selection();job=next(j for j in plan_for(registry)['jobs'] if j['candidate_id']==cid)
    spec=validate_job(job,registry)
    return {'profile':'rw_legacy','runner':'scripts/run_realworld_legacy_job_v8.py','loader':'realworld_legacy_jobs_v10',
            'registry_path':None,'registry':registry,'job':job,'specs':{b['continuation']:spec for b in job['branches']},'context':{}}

def templates():
    rows=read(ROOT/'manifests/retained-corpus-review-v5.json')['review']['rows'];lookup={r['inventory_entry']['pair_id']:r for r in rows}
    from petclinic_timed_jobs_v4 import contract,validate_job
    from realworld_generated_bindings_v1 import plan as generated_plan,case_for
    from prepare_common_bindings_v1 import collect
    generated={r['pair_id']:r for r in collect()[0] if r['profile'].startswith('generated_')}
    pc={}
    for batch in ('owner_required','owner_formats','pets','visits'):
        for job in contract(batch)['plan']['schedule']['initial_jobs']:
            pc.setdefault(job['pair_id'],(batch,job))
    inventory=read(ROOT/'manifests/paired-candidate-inventory-v1.json')['pairs']
    quartz_plan=build_plan([p for p in inventory if p['catalog']=='quartz_generated_v2'])
    quartz_jobs={j['pair_id']:j for j in quartz_plan['schedule']['initial_jobs']}
    quartz=read(ROOT/'manifests/quartz-job-generated-pool-v2.json');quartz_cases={c['case_id']:c for c in quartz['cases']}
    def make(row,cid=None):
        entry=row['inventory_entry'];catalog=entry['catalog'];pid=entry['pair_id'] if cid is None else catalog+'::'+cid
        if catalog=='realworld_development':return rw_template(row,cid)
        if catalog=='petclinic_development':
            chosen=entry['candidate_id'];batch,job=pc[chosen]
            if cid is not None:job=next(j for j in contract(batch)['plan']['schedule']['initial_jobs'] if j['pair_id']==cid)
            spec=validate_job(job,batch)
            return {'profile':'petclinic_v4','runner':'scripts/run_petclinic_pair_job_v4.mjs','loader':'petclinic_timed_jobs_v4',
                    'registry_path':'manifests/petclinic-candidates-v1.json','job':job,'specs':{c:spec for c in ('api','ui')},'context':{'batch':batch}}
        if catalog=='realworld_generated_integration':
            g=generated[pid];job=g['runtime_job']
            return {'profile':g['profile'],'runner':'scripts/realworld_generated_worker_v2.py','loader':'common_generated_adapter_v1',
                    'registry_path':'manifests/realworld-article-generated-pool-v1.json','job':job,
                    'specs':{c:case_for(job,c) for c in ('api','ui')},'context':{}}
        require(catalog=='quartz_generated_v2','Unknown catalog')
        job=quartz_jobs[pid]
        return {'profile':'quartz_v2','runner':'scripts/run_quartz_pair_job_v2.mjs','loader':'quartz_terminal_outcomes',
                'registry_path':'manifests/quartz-job-generated-pool-v2.json','job':job,
                'specs':{b['continuation']:quartz_cases[b['case_id']] for b in job['branches']},'context':{}}
    def validate(template,row):
        wanted={b['continuation_interface']:b['source_case_sha256'] for b in row['branches']}
        require({c:case_digest(s) for c,s in template['specs'].items()}==wanted,'Source case differs: '+row['inventory_entry']['pair_id'])
        channels=[b.get('continuation',b.get('channel')) for b in template['job']['branches']]
        require(sorted(channels)==sorted(wanted),'Runtime channel inventory differs')
        for path in (template['runner'],'scripts/'+template['loader']+'.py'):require((ROOT/path).is_file(),'Missing runtime source: '+path)
        value=deepcopy(template);value['source_case_sha256']={c:case_digest(s) for c,s in value.pop('specs').items()};value['branch_order']=channels
        return value
    bindings=[]
    for index,row in enumerate(rows):
        e=row['inventory_entry'];runtime=validate(make(row),row);refid=row['reference_control_pair_id'];reference=None
        if refid:
            refrow=lookup[refid];refcid=refrow['inventory_entry'].get('candidate_id',refid.split('::',1)[1])
            reference=validate(make(row,refcid),refrow)
        item={'entry':deepcopy(e),'entry_kind':row['entry_kind'],'initial_attempt_id':f'initial-{index:03d}',
              'runtime':runtime,'reference_pair_id':refid,'reference_runtime':reference,
              'historical_remaining_requirements':row['remaining_execution_requirements'],
              'historical_outcome_limits':row['retained_outcome_limits']}
        item['binding_sha256']=digest(item);bindings.append(item)
    require(len(bindings)==75 and sum(b['entry_kind']=='pair' for b in bindings)==73,'Catalog count differs')
    return {'kind':'primary_runtime_catalog_preparation_v1','bindings':bindings,'review_sha256':sha(ROOT/'manifests/retained-corpus-review-v5.json'),
            'counts':{'entries':75,'pairs':73,'singletons':2,'branches':148},'execution_authorized':False,'primary_freeze_complete':False}

if __name__=='__main__':
    import json
    value=templates();print(json.dumps(value['counts'],indent=2))
    write(ROOT/'manifests/primary-runtime-catalog-v1.json',value)
