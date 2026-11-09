"""PetClinic terminal extraction v2; historical replay and pure evidence functions.

Fresh per-job dispatch is not qualified by this module. The historical sources
remain immutable; completed native blocking and changed rejection graphs are
observations, while identity/capture/cleanup conditions remain mandatory.
"""
from copy import deepcopy
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import summarize_petclinic_integrity_components as prior
from summarize_petclinic_integrity_components import legacy,project_trace,refresh,sha,load
from validate_petclinic_integrity import require,read
from summarize_petclinic_oracle_components import same,digest
from mixed_interface.terminal_outcomes import terminal

def validate_observation(r,case):
 require(r['prefix_status']==case['prefix_status'],'Unexpected prefix status')
 require(r['backend_cleanup']['confirmed'] is True,'Backend exit not confirmed')
 require(not r['page_errors'],'Native page errors')
 integrity=r['integrity'];require(integrity['version']==1,'Integrity version')
 guards=integrity['guards'];names=[g['name'] for g in guards]
 require(len(names)==len(set(names)),'Duplicate guard')
 blocked=r.get('status')=='ui_blocked'
 intended_command=None
 required={'pre_candidate_state_readable','candidate_prefix_command'}
 if case['prefix_status']==201:
  required|={'loaded_target_binding','returned_target_id_valid'}
  if not blocked:required.add('continuation_edit_command')
  if r['template']!='owner_address_edit':required|={'returned_pet_owner','bound_owner_read_status','bound_owner_identity'}
  if r['template']=='visit_reschedule':required|={'returned_visit_parent','bound_pet_read_status','bound_pet_identity'}
  if r['oracle']=='fresh_ui':
   required|={'native_loaded_target','native_loaded_fields'}
   if r['template']!='owner_address_edit':required|={'native_owner_status','native_owner_binding'}
   if r['template']=='visit_reschedule':required|={'native_pet_status','native_pet_binding'}
  if blocked:
   require(r['oracle']=='fresh_ui' and r.get('ui_submit_disabled') is True and 'continuation_http_status' not in r,'Invalid blocked native outcome')
   require(not any(e.get('method')=='PUT' for e in r['trace']),'Write despite blocked submit')
  else:require(r['status']=='continuation_passed' and r['continuation_http_status']==204,'Unsupported completed continuation')
 else:
  require(r['status']=='prefix_rejected' and r['continuation_reachable'] is False,'Unexpected rejected-prefix continuation')
  require(not any(e.get('method')=='PUT' for e in r['trace']),'Write after rejected prefix')
 require(required<=set(names),'Missing required guard: '+str(required-set(names)))
 for g in guards:
  require(g['passed'] is True and same(g['expected'],g['observed']),'Failed or forged guard: '+g['name'])
  if g['name'].endswith('_command'):
   actual=g['observed'];source='ui_network' if g['name']=='continuation_edit_command' and r['oracle']=='fresh_ui' else 'direct_api'
   events=[e for e in r['trace'] if e.get('source')==source and e.get('method')==actual['method'] and e.get('path').removeprefix('/petclinic/api')==actual['path'] and same(e.get('request'),actual['payload'])]
   require(len(events)==1,'Command does not match one captured request')
 # Reconstruct intended commands and returned-resource bindings from raw evidence.
 registered=next(c for c in read(ROOT/'manifests/petclinic-candidates-v1.json')['candidates'] if c['id']==case['id'])
 direct=[e for e in r['trace'] if e.get('source')=='direct_api']
 prefix=next(e for e in direct if e['phase']=='candidate_prefix')
 setup=[e for e in direct if e['phase']=='prefix_setup' and e['method']=='POST']
 owner=next((e['response'] for e in setup if e['path']=='/owners'),None)
 pet=next((e['response'] for e in setup if e['path'].endswith('/pets')),None)
 wanted_path=('/owners' if r['template']=='owner_address_edit' else '/owners/'+str(owner['id'])+'/pets'+('' if r['template']=='pet_rename' else '/'+str(pet['id'])+'/visits'))
 require(prefix['path']==wanted_path and same(prefix['request'],registered['payload']),'Candidate prefix differs from registered command')
 guardmap={g['name']:g for g in guards}
 if case['prefix_status']==201:
  target=prefix['response'];kind={'owner_address_edit':'owners','pet_rename':'pets','visit_reschedule':'visits'}[r['template']]
  keys={'owners':['id','firstName','lastName','address','city','telephone'],'pets':['id','name','birthDate','type','ownerId'],'visits':['id','date','description','petId']}[kind]
  loaded=next(e['response'] for e in direct if e['phase']=='continuation_read' and e['path']=='/'+kind+'/'+str(target['id']))
  require(same(loaded,r['before']),'Loaded target is not trace-backed')
  g=guardmap['loaded_target_binding']
  require(same(g['expected'],{k:target[k] for k in keys}) and same(g['observed'],{k:loaded[k] for k in keys}),'Loaded-target guard is not bound to producer')
  change={'owners':{'address':'2 Pilot Lane'},'pets':{'name':'Renamedpet'},'visits':{'date':'2026-11-07'}}[kind]
  if kind=='owners':payload={**{k:loaded[k] for k in keys},**change}
  elif kind=='pets':
   require(loaded['ownerId']==owner['id'],'Pet belongs to wrong owner')
   payload={**{k:loaded[k] for k in ['id','name','birthDate','type']},**change}
  else:
   require(loaded['petId']==pet['id'],'Visit belongs to wrong pet')
   bound=next(e['response'] for e in direct if e['phase']=='binding_read' and e['path']=='/pets/'+str(loaded['petId']))
   require(bound['id']==pet['id'] and bound['ownerId']==owner['id'],'Wrong returned pet/owner chain')
   payload={'id':loaded['id'],'pet':bound,'date':change['date'],'description':loaded['description']}
  intended_command={'method':'PUT','path':'/'+kind+'/'+str(target['id']),'payload':payload}
  if blocked:require(same(r['ui_edit_intended'],change),'Blocked edit intent differs')
  else:require(same(guardmap['continuation_edit_command']['expected'],intended_command),'Intended edit payload is not bound to loaded state')
  require(same(r['after'],loaded if blocked else {**loaded,**change}),'Final entity does not preserve expected fields')
  if blocked:require(same(r['final_graph'],r['post_prefix_graph']),'Blocked native source cannot report changed relationships')
 before=integrity['before'];require(before['readable'] is True,'Unreadable before state')
 events=[e for e in r['trace'] if e.get('source')=='direct_api' and e.get('phase')=='pre_candidate_state' and e.get('path')=='/owners']
 require(len(events)==1 and events[0]['status']==200 and same(events[0]['response'],before['data']),'Before graph not trace-backed')
 if case['prefix_status']!=201:
  after=integrity['rejection']['after'];require(after['readable'] is True,'Unreadable after state')
  require(integrity['rejection']['status']==('unchanged' if same(before['data'],after['data']) else 'changed'),'Rejected-state verdict is not supported by graphs')
  require(same(after['data'],r['post_prefix_graph']),'After graph not backed by post-prefix evidence')
  events=[e for e in r['trace'] if e.get('phase')=='post_prefix_state' and e.get('path')=='/owners']
  require(len(events)==1 and events[0]['status']==200 and same(events[0]['response'],after['data']),'After graph not trace-backed')
 capture=r['capture_integrity'];require(not capture['errors'],'Native capture errors')
 requests={};responses={}
 for e in r['trace']:
  if e.get('source') not in ('ui_request','ui_network'):continue
  target=requests if e['source']=='ui_request' else responses
  key=e['capture_request_id'];require(key not in target,'Duplicate capture request identifier')
  target[key]={k:e[k] for k in ['context_id','method','path','request_phase']}
 require(requests==responses,'Incomplete native request/response accounting')
 contexts=capture['contexts'];require(len(contexts)==(1 if case['prefix_status']==201 and r['oracle']=='fresh_ui' else 0),'Unexpected capture context count')
 for c in contexts:
  require(c['complete'] is True and c['timed_out'] is False and not c['outstanding'] and c['failures']==0,'Incomplete context drain')
  require(c['admitted']==c['completed']==len(requests),'Capture counts disagree')
 return {'intended_command':intended_command,'guards':len(guards),'native_requests':len(requests),'capture_contexts':len(contexts),'rejection_state':(integrity.get('rejection') or {}).get('status')}

def reduce_observation(raw,registered,registry,expected):
    checked=validate_observation(raw,expected)
    projected,omitted=project_trace(raw)
    result=legacy.reduce_case(projected,registered,registry)
    result['projection']={'kind':'finite_legacy_trace_view_with_separate_new_evidence_checks','omitted_from_legacy_view':omitted,
        'visit_api_binding_read_phase_projected_to':'continuation_read','original_trace_changed':False}
    parts=result['components']
    # These GETs are issued before either continuation in the revised runner.
    for name in ('api_target_load_200','api_bound_pet_load'):
        api=parts['assigned_api_continuation']
        api['checks']=[c for c in api['checks'] if c['id']!=name]
    def add(component,name,passed,detail=None,role='comparability_guard'):
        c={'id':name,'passed':bool(passed),'origin_component':component,'scope':'recorded_integrity_adapter_predicate','analysis_role':role}
        if detail is not None:c['detail']=detail
        parts[component]['checks'].append(c)
    if result['accepted_prefix']:
        kind=legacy.TEMPLATES[registered['template']][0]
        located=legacy.locate(raw['post_prefix_graph'],kind,raw['prefix_response']['id'])
        before=next(e for e in raw['trace'] if e.get('source')=='direct_api' and e.get('phase')=='continuation_read')
        add('prefix_state_reads','shared_target_read_200',before['status']==200,role='state_observation')
        for e in raw['trace']:
            if e.get('phase')=='binding_read':
                bound=located[0] if e['path'].startswith('/owners/') else located[1]
                name='shared_bound_owner_read_matches_prefix_graph' if e['path'].startswith('/owners/') else 'shared_bound_pet_read_matches_prefix_graph'
                add('prefix_state_reads',name,legacy.same(e['response'],bound),role='retrospective_state_observation')
    for g in raw['integrity']['guards']:
        component=('assigned_native_continuation' if g['name'].startswith('native_') else
                   'assigned_native_continuation' if g['name']=='continuation_edit_command' and raw['oracle']=='fresh_ui' else
                   'assigned_api_continuation' if g['name']=='continuation_edit_command' else
                   'prefix_state_reads' if g['name'] in {'loaded_target_binding','returned_visit_parent','bound_pet_read_status','bound_pet_identity','returned_pet_owner','bound_owner_read_status','bound_owner_identity'} else 'integrity')
        add(component,'integrity:'+g['name'],g['passed'],{'expected':g['expected'],'observed':g['observed']})
    add('integrity','native_capture_complete',True,checked)
    add('integrity','owned_backend_exit_confirmed',raw['backend_cleanup']['confirmed'],raw['backend_cleanup'])
    if not result['accepted_prefix']:
        result['unavailable_evidence']=[s for s in result['unavailable_evidence'] if not s.startswith('pre_candidate_snapshot_after_valid_setup_not_recorded')]
        add('prefix_state_reads','pre_candidate_graph_unchanged_after_rejection',raw['integrity']['rejection']['status']=='unchanged',
            {'projection':'owner/pet/visit API graph after valid setup'},role='state_observation')
    for name,part in parts.items():
        if part['checks'] or part.get('observations'):refresh(part,result['execution_evidence_complete'] and name!='unresolved_policy')
        elif name=='assigned_api_continuation' and raw['oracle']=='api_semantic':refresh(part,result['execution_evidence_complete'])
    result['validation']=checked
    result['source_version']='petclinic_terminal_observations_v2'
    result['interpretation']='Source-qualified engineering controls; shared pre-continuation GETs are not API-exclusive observations. No defect adjudication.'
    return result


def classify_branch(raw,registered,registry,expected,*,cleanup_confirmed):
    if cleanup_confirmed is not True or raw.get('backend_cleanup',{}).get('confirmed') is not True:
        return {'kind':'cleanup_unconfirmed','issues':['owned_cleanup_not_confirmed']}
    if raw.get('status')=='runner_or_assertion_failure' or raw.get('error'):
        return {'kind':'environment_failure','issues':['unclassified_runner_or_assertion_failure']}
    try:
        require(raw['candidate_id']==registered['id']==expected['id'] and raw['template']==registered['template'],'Candidate identity differs')
        require(raw['oracle'] in ('api_semantic','fresh_ui'),'Unknown consumer')
        require(raw['integrity']['helper_sha256']==prior.HELPERS['petclinic_integrity.mjs'],'Integrity helper differs')
        require(raw['capture_integrity']['helper_sha256']==prior.HELPERS['petclinic_response_capture.mjs'],'Capture helper differs')
        require(raw['backend_cleanup']['owned'] is True and type(raw['backend_pid']) is int and raw['backend_pid']>0 and raw['backend_pid']==raw['backend_cleanup']['pid'],'Backend ownership differs')
        reduced=reduce_observation(raw,registered,registry,expected)
        if not reduced['execution_evidence_complete']:
            return {'kind':'missing_evidence','issues':reduced['evidence_issues'],'components':reduced}
    except (ValueError,KeyError,TypeError,AttributeError,StopIteration,IndexError) as error:
        return {'kind':'missing_evidence','issues':[type(error).__name__+': '+str(error)]}
    failed=any(p['mismatch_observed'] for name,p in reduced['components'].items() if name not in ('integrity','unresolved_policy'))
    kind='completed_mismatch' if failed else 'unresolved_policy' if reduced['policy_unresolved'] else 'clean_observation' if reduced['accepted_prefix'] else 'matched_rejection'
    return {'kind':kind,'issues':[],'components':reduced}


def pair_terminal(job_id,branches,registered,registry,expected,*,cleanup_confirmed,evidence):
    classified={c:classify_branch(raw,registered,registry,expected,cleanup_confirmed=cleanup_confirmed) for c,raw in branches.items()}
    kinds=[v['kind'] for v in classified.values()];gates={}
    complete={'clean_observation','matched_rejection','completed_mismatch','unresolved_policy'}
    if set(branches)=={'api','ui'} and all(k in complete for k in kinds):
        a,u=branches['api'],branches['ui']
        def prefix(raw):return next(e for e in raw['trace'] if e.get('phase')=='candidate_prefix' and e.get('source')=='direct_api')
        ap,up=prefix(a),prefix(u)
        gates={'correct_consumers':a['oracle']=='api_semantic' and u['oracle']=='fresh_ui',
               'same_actor':a['actor']==u['actor']==registry['actor'],
               'same_initial_state':a['initial_state_sha256']==u['initial_state_sha256']==legacy.INITIAL_STATE_SHA256,
               'independent_backend_processes':a['backend_pid']!=u['backend_pid'],
               'same_pre_candidate_graph':same(a['integrity']['before']['data'],u['integrity']['before']['data']),
               'same_prefix_command':all(same(ap[k],up[k]) for k in ('method','path','request')),
               'same_prefix_status':a['prefix_status']==u['prefix_status'],
               'same_post_prefix_graph':same(a['post_prefix_graph'],u['post_prefix_graph']),
               'same_intended_edit':same(classified['api']['components']['validation']['intended_command'],classified['ui']['components']['validation']['intended_command'])}
    accepted=[v.get('components',{}).get('accepted_prefix') for v in classified.values()]
    prefix_state='unobserved' if not accepted or None in accepted else 'accepted' if all(accepted) else 'rejected' if not any(accepted) else 'mixed'
    kind=next((k for k in ('cleanup_unconfirmed','environment_failure','missing_evidence') if k in kinds),None)
    if not cleanup_confirmed:kind='cleanup_unconfirmed'
    if kind is None and set(branches)!={'api','ui'}:kind='missing_evidence'
    if kind is None and (not gates or not all(gates.values()) or prefix_state=='mixed'):kind='incomparable_observation'
    if kind is None:kind='completed_mismatch' if 'completed_mismatch' in kinds else 'unresolved_policy' if 'unresolved_policy' in kinds else 'clean_observation' if prefix_state=='accepted' else 'matched_rejection'
    comparable=kind in complete
    signals={c:v['components']['components']['assigned_api_continuation' if c=='api' else 'assigned_native_continuation']['mismatch_observed'] for c,v in classified.items() if 'components' in v}
    signature={'kinds':{c:v['kind'] for c,v in classified.items()},'comparability':gates,
               'prefix_http_status':{c:r.get('prefix_status') for c,r in branches.items()},
               'checks':{c:{name:[[x['id'],x['passed']] for x in part['checks']] for name,part in v['components']['components'].items()} for c,v in classified.items() if 'components' in v}}
    outcome={'job_id':job_id,'execution':'complete' if comparable else 'incomplete','prefix':prefix_state,
             'channel_discrepancy':signals.get('api')!=signals.get('ui') if comparable else None,
             'check_failure':'completed_mismatch' in kinds if comparable else None,
             'cleanup_confirmed':bool(cleanup_confirmed) and 'cleanup_unconfirmed' not in kinds,'observation_signature':signature}
    return {'terminal':terminal(outcome,kind,evidence),'comparability':gates,'branches':classified}


def replay_archive(directory):
    directory=Path(directory)
    qualification=load(ROOT/'manifests/petclinic-execution-integrity.json')
    for name,h in qualification['compact_artifact_sha256'].items():
        relative=Path(name).relative_to('results/petclinic-integrity-ci-20261107')
        require(sha(directory/relative)==h,'Historical artifact differs: '+str(relative))
    prior_report=prior.summarize_compact(directory)
    require(prior_report['status']=='complete_observations','Historical source qualification failed')
    cleanup=load(directory/'petclinic-owned-process-cleanup.json')
    require(set(cleanup)=={'frontend','runner'} and all(set(r)=={'pid','exit_confirmed','returncode'} and r['exit_confirmed'] is True for r in cleanup.values()) and cleanup['runner']['returncode']==0 and cleanup['frontend']['returncode']==143,'Historical cleanup record differs')
    registry=load(ROOT/'manifests/petclinic-candidates-v1.json')
    selection=load(ROOT/'manifests/petclinic-integrity-controls-v1.json')['cases']
    pairs=[]
    for expected in selection:
        cid=expected['id'];spec=next(c for c in registry['candidates'] if c['id']==cid)
        paths={c:directory/'observations'/(cid+'-'+o+'.json') for c,o in (('api','api_semantic'),('ui','fresh_ui'))}
        result=pair_terminal('archive::'+cid,{c:load(p) for c,p in paths.items()},spec,registry,expected,
                             cleanup_confirmed=True,evidence={**{str(p.relative_to(directory)):sha(p) for p in paths.values()},'cleanup':sha(directory/'petclinic-owned-process-cleanup.json'),'source_plan':sha(directory/'petclinic-integrity-plan.json')})
        require(result['terminal']['kind']==('clean_observation' if expected['prefix_status']==201 else 'matched_rejection'),'Historical control terminal differs')
        pairs.append({'candidate_id':cid,**result})
    return {'kind':'petclinic_historical_terminal_replay','pairs':pairs,'pair_count':6,'branches':12,
            'application_executions_added':0,'per_job_dispatch_qualified':False,'primary_freeze_complete':False,
            'historical_plan_sha256':sha(directory/'petclinic-integrity-plan.json')}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path);args=parser.parse_args()
    print(json.dumps(replay_archive(args.archive),indent=2))
