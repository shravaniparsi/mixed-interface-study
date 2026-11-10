"""Requirement-aware prefix interpretation; preserve raw evidence and v2 archives."""
from copy import deepcopy
import petclinic_terminal_outcomes as v2
from petclinic_terminal_outcomes import ROOT,load,sha,same,legacy,terminal,require,refresh
POLICY='manifests/petclinic-prefix-policy-v3.json'
POLICY_SHA='95a1c08e7a62b72c19031ffec84ef5602e2553fd7c67bbde432656febd6faf9e'

def policy_for(registered,registry):
    require(sha(ROOT/POLICY)==POLICY_SHA,'Prefix policy differs')
    policy=load(ROOT/POLICY)
    require(sha(ROOT/'manifests/petclinic-candidates-v1.json')==policy['registry_sha256'],'Registry bytes differ')
    require(same(registry,load(ROOT/'manifests/petclinic-candidates-v1.json')),'Registry content differs')
    require(registered in registry['candidates'],'Registered case differs')
    rows=[c for c in policy['cases'] if c['id']==registered['id']]
    require(len(rows)==1 and rows[0]['requirement_ids']==registered['requirement_ids'],'Requirement binding differs')
    return policy,rows[0]

def classify_branch(raw,registered,registry,*,cleanup_confirmed):
    if cleanup_confirmed is not True or raw.get('backend_cleanup',{}).get('confirmed') is not True:
        return {'kind':'cleanup_unconfirmed','issues':['owned_cleanup_not_confirmed']}
    if raw.get('status')=='runner_or_assertion_failure' or raw.get('error'):
        return {'kind':'environment_failure','issues':['unclassified_runner_or_assertion_failure']}
    try:
        policy,spec=policy_for(registered,registry)
        code=raw.get('prefix_status')
        require(type(code) is int and 100<=code<=599,'Invalid HTTP status')
        if code!=201:
            require(raw.get('status')==('prefix_server_error' if code>=500 else 'prefix_rejected'),'Prefix status tag differs from recorded response')
        projected=deepcopy(raw)
        # The legacy evidence validator uses one tag for all non-201 stopped prefixes.
        # Only the tag is adapted; HTTP code, response, state and trace stay intact.
        if code>=500:projected['status']='prefix_rejected'
        result=v2.classify_branch(projected,registered,registry,{'id':registered['id'],'prefix_status':code},cleanup_confirmed=True)
        if result['kind'] in ('cleanup_unconfirmed','environment_failure','missing_evidence'):return result
        parts=result['components']['components']
        result['prefix_policy']={'policy_sha256':POLICY_SHA,**spec,'observed_status':code}
        result['components']['source_version']='petclinic_prefix_outcomes_v3'
        result['components']['raw_status_projection']={'from':raw['status'],'to':projected['status'],'raw_evidence_changed':False}
        result['components']['interpretation']='Recorded observations under registered prefix requirements; no automatic defect adjudication.'
        if code!=201 and code not in policy['validation_rejection_statuses']:
            result['kind']='application_response_failure'
            result['prefix_policy']['assessment']='non_validation_response; semantic outcome incomplete'
            return result
        requirement=spec['prefix_requirement']
        if requirement!='unresolved':
            passed=(code==201)==(requirement=='accept')
            parts['immediate_response']['checks'].append({'id':'registered_prefix_requirement','passed':passed,'origin_component':'immediate_response','scope':'registered_prefix_requirement','analysis_role':'shared_producer_observation','detail':result['prefix_policy']})
            refresh(parts['immediate_response'],True)
        else:result['components']['policy_unresolved']=True
        failed=any(p['mismatch_observed'] for name,p in parts.items() if name not in ('integrity','unresolved_policy'))
        result['kind']='completed_mismatch' if failed else 'unresolved_policy' if result['components']['policy_unresolved'] else 'clean_observation' if code==201 else 'matched_rejection'
        return result
    except (ValueError,KeyError,TypeError,AttributeError,StopIteration,IndexError) as error:
        return {'kind':'missing_evidence','issues':[type(error).__name__+': '+str(error)]}


def pair_terminal(job_id,branches,registered,registry,*,cleanup_confirmed,evidence):
    classified={c:classify_branch(raw,registered,registry,cleanup_confirmed=cleanup_confirmed) for c,raw in branches.items()}
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
    kind=next((k for k in ('cleanup_unconfirmed','environment_failure','missing_evidence','application_response_failure') if k in kinds),None)
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

