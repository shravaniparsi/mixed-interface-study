"""Immutable cross-runtime job bindings and engineering preflight; never dispatches."""
from copy import deepcopy
from .repetition import require,digest
from .campaign_v2 import build_plan,validate_plan,followups
from .terminal_outcomes import POLICY_SHA256
import math


def registry(review,records,profiles):
    require(review['primary_freeze_complete'] is False and review['execution_authorized'] is False,'Review promoted')
    rows={r['inventory_entry']['pair_id']:r for r in review['rows']};require(len(rows)==75,'Corpus differs')
    by_id={r['pair_id']:r for r in records};require(len(by_id)==len(records)==15,'Binding inventory differs')
    result=[]
    for pid,row in rows.items():
        if pid not in by_id:continue
        r=deepcopy(by_id[pid]);entry=row['inventory_entry'];require(row['entry_kind']=='pair','Singleton cannot enter paired plan')
        require(r['profile'] in profiles and profiles[r['profile']]['terminal_policy_sha256']==POLICY_SHA256,'Unknown runtime or terminal policy')
        require(set(r['cases'])==set(r['observed_cost_s'])=={'api','ui'} and sorted(r['branch_order'])==['api','ui'],'Branch inventory differs')
        for branch in row['branches']:
            c=branch['continuation_interface'];require(digest(r['cases'][c])==branch['source_case_sha256'],'Source case differs')
            require(type(r['observed_cost_s'][c]) in (int,float) and math.isfinite(r['observed_cost_s'][c]) and r['observed_cost_s'][c]>0,'Qualified branch timing absent')
        require(set(r['effective_case_ids'])=={'api','ui'} and len(set(r['effective_case_ids'].values()))==2,'Effective branch identity differs')
        reference=row['reference_control_pair_id'];require(reference in by_id,'Reference omitted from bindings')
        ref=rows[reference]['inventory_entry']
        require((entry['workflow_id'],entry['producer_interface'],entry['catalog'])==(ref['workflow_id'],ref['producer_interface'],ref['catalog']),'Reference crosses workflow, producer or catalog')
        r.update(workflow_id=entry['workflow_id'],producer_interface=entry['producer_interface'],reference_pair_id=reference,
                 source_case_sha256={c:digest(s) for c,s in r.pop('cases').items()},
                 registered_semantics_sha256=entry['registered_semantics_sha256'],prior_exposure=entry['prior_exposure'])
        r['binding_sha256']=digest(r);result.append(r)
    require(len(result)==15,'Foreign binding outside corpus')
    core={'kind':'common_engineering_bindings_v1','review_sha256':digest(review),'terminal_policy_sha256':POLICY_SHA256,
          'profiles':deepcopy(profiles),'bindings':result,'unbound_entries':[{'pair_id':pid,'entry_kind':r['entry_kind'],'path_family':r['path_family']} for pid,r in rows.items() if pid not in by_id],
          'counts':{'catalog_entries':len(rows),'bound_pairs':len(result),'unbound_entries':len(rows)-len(result),'singletons_excluded':sum(r['entry_kind']=='singleton' for r in rows.values())},
          'execution_authorized':False,'primary_freeze_complete':False,'runtime_dispatch_qualified':False,'new_primary_samples':0}
    return {**core,'registry_sha256':digest(core)}


def validate_registry(value):
    require(value['registry_sha256']==digest({k:v for k,v in value.items() if k!='registry_sha256'}),'Binding registry hash differs')
    require(value['terminal_policy_sha256']==POLICY_SHA256 and value['execution_authorized'] is False and value['primary_freeze_complete'] is False and value['runtime_dispatch_qualified'] is False,'Policy or scope promoted')
    for b in value['bindings']:
        require(b['binding_sha256']==digest({k:v for k,v in b.items() if k!='binding_sha256'}),'Binding changed')
        require(b['profile'] in value['profiles'] and set(b['observed_cost_s'])=={'api','ui'} and
                all(type(t) in (int,float) and math.isfinite(t) and t>0 for t in b['observed_cost_s'].values()),'Qualified cost missing')
        require(sorted(b['branch_order'])==['api','ui'] and set(b['source_case_sha256'])==set(b['effective_case_ids'])=={'api','ui'},'Branch binding schema differs')
    ids=[b['pair_id'] for b in value['bindings']];unbound=[b['pair_id'] for b in value['unbound_entries']]
    require(len(ids)==15 and len(unbound)==60 and len(set(ids+unbound))==75,'Catalog accounting differs')


def preflight(value,selection,live_hashes):
    validate_registry(value);require(bool(selection) and len(selection)==len(set(selection)),'Empty or duplicate selection')
    by_id={b['pair_id']:b for b in value['bindings']};require(all(pid in by_id for pid in selection),'Unbound or singleton selection')
    for profile in value['profiles'].values():
        require(profile['terminal_policy_sha256']==POLICY_SHA256,'Runtime policy changed')
        require(all(live_hashes.get(p)==h for p,h in profile['source_sha256'].items()),'Runtime source changed')
    pairs=[]
    for pid in selection:
        b=by_id[pid];require(b['reference_pair_id'] in selection,'Same-producer reference missing')
        reference=b['reference_pair_id']==pid
        pairs.append({'pair_id':pid,'workflow_id':b['workflow_id'],'producer_interface':b['producer_interface'],
            'case_ids':b['effective_case_ids'],'intervention':'route_only' if reference else 'payload_mutation',
            'mutation':None if reference else {'registered_semantics_sha256':b['registered_semantics_sha256']}})
    campaign=build_plan(pairs)
    for p,j in zip(campaign['schedule']['pairs'],campaign['schedule']['initial_jobs']):
        b=by_id[j['pair_id']]
        require(p['reference_control']==b['reference_pair_id'],'Campaign reference changed')
        require([x['continuation'] for x in j['branches']]==b['branch_order'],'Planner order differs from qualified runtime order')
    core={'kind':'common_engineering_preflight_v1','registry_sha256':value['registry_sha256'],'campaign':campaign,
          'binding_sha256':{pid:by_id[pid]['binding_sha256'] for pid in selection},'engineering_preflight_passed':True,
          'execution_authorized':False,'primary_freeze_complete':False,'live_common_executor_qualified':False}
    return {**core,'preflight_sha256':digest(core)}


def bind_job(value,checked,job,initial_outcomes=None):
    validate_registry(value);validate_plan(checked['campaign'])
    require(checked['preflight_sha256']==digest({k:v for k,v in checked.items() if k!='preflight_sha256'}) and checked['registry_sha256']==value['registry_sha256'],'Preflight changed')
    require(checked['execution_authorized'] is False and checked['primary_freeze_complete'] is False and checked['live_common_executor_qualified'] is False,'Preflight promoted')
    initial=checked['campaign']['schedule']['initial_jobs']
    if job not in initial:
        require(initial_outcomes is not None,'Follow-up lacks registered trigger evidence')
        f=followups(checked['campaign'],initial_outcomes)
        require(f['status']=='planned' and job in f['jobs'],'Follow-up not authorized by terminal policy')
    b=next((b for b in value['bindings'] if b['pair_id']==job['pair_id']),None)
    require(b is not None and checked['binding_sha256'].get(job['pair_id'])==b['binding_sha256'],'Job binding differs')
    require([x['continuation'] for x in job['branches']]==b['branch_order'] and all(x['fresh_reset_required'] is True for x in job['branches']),'Branch order or reset differs')
    return {'campaign_job':deepcopy(job),'runtime_profile':b['profile'],'runtime_job':deepcopy(b['runtime_job']),
            'runtime_context':deepcopy(b['runtime_context']),'attempt_namespace':job['job_id'],
            'binding_sha256':b['binding_sha256'],'cost_scope':value['profiles'][b['profile']]['cost_scope'],
            'requires_fresh_execution':True,'historical_attempt_reuse_allowed':False,'execution_authorized':False}
