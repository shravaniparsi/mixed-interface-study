"""Strict component attribution and control-pair signal accounting.

No aggregate pass/fail status can substitute for attributed observations. Shared
checks and comparability guards never generate exclusive continuation credit.
"""
from collections import Counter

COMPONENTS={'immediate_response','producer_native_controls','prefix_state_reads',
 'assigned_api_continuation','assigned_native_continuation','shared_post_continuation_api_readback',
 'shared_final_native_read','environment_reset_cleanup','unresolved_policy'}
SOURCE_STATUSES={'no_check_mismatch_observed','check_mismatch_observed','observations_without_registered_predicate','not_reached_or_not_applicable','not_reached_prefix_unsuccessful','not_assigned','incomplete_or_invalid_evidence','policy_observations_only','not_applicable','not_reached_prefix_rejected'}
SHARED={'prefix_state_reads','shared_post_continuation_api_readback','shared_final_native_read'}
GATES={'same_declared_prefix','same_initial_state','same_pre_candidate_state','same_observed_prefix_command',
 'same_prefix_outcome','independent_reset_evidence','same_accepted_prefix_state','same_intended_consumer_command'}
POST_ACCEPTANCE_GATES={'same_accepted_prefix_state','same_intended_consumer_command'}


def normalize_case(raw,source,rules,*,record_id):
    result={'record_id':record_id,'source':source,'case_id':raw['case_id'],'route':raw['route'],
            'accepted_prefix':raw['accepted_prefix'],'execution_evidence_complete':raw['execution_evidence_complete'],
            'policy_unresolved':raw.get('policy_unresolved',False),'evidence_issues':list(raw.get('evidence_issues',[])),
            'components':{name:{'checks':[],'observations':[],'source_statuses':[]} for name in sorted(COMPONENTS)}}
    if type(result['accepted_prefix']) is not bool or type(result['execution_evidence_complete']) is not bool:
        raise ValueError('Missing explicit acceptance or evidence-completeness state')
    if type(result['policy_unresolved']) is not bool:raise ValueError('Unknown policy state')
    if len(raw['route'].split('-'))!=2 or any(x not in {'api','ui'} for x in raw['route'].split('-')):raise ValueError('Unknown continuation route')
    if result['evidence_issues']:result['execution_evidence_complete']=False
    for origin,part in raw['components'].items():
        if part.get('status') not in SOURCE_STATUSES or type(part.get('comparison_eligible')) is not bool:raise ValueError('Unknown component status or eligibility')
        default='environment_reset_cleanup' if origin=='integrity' else origin
        if default not in COMPONENTS:raise ValueError('Unknown component: '+origin)
        result['components'][default]['observations'].extend(part.get('observations',[]))
        result['components'][default]['source_statuses'].append({'origin':origin,'status':part['status'],'comparison_eligible':part['comparison_eligible']})
        seen=set()
        for c in part['checks']:
            key=origin+'::'+c['id']
            if key in seen or key not in rules:raise ValueError('Duplicate or unmapped check: '+key)
            seen.add(key);rule=rules[key]
            if rule['component'] not in COMPONENTS or rule['role'] not in {'observation','comparability_guard','unresolved_policy'}:
                raise ValueError('Unknown attribution rule')
            if type(c.get('passed')) is not bool:raise ValueError('Unknown check verdict')
            item={**c,'origin_component':origin,'component':rule['component'],'analysis_role':rule['role'],
                  'source_comparison_eligible':part['comparison_eligible']}
            result['components'][rule['component']]['checks'].append(item)
            if rule['role']=='comparability_guard' and not c['passed']:
                result['execution_evidence_complete']=False;result['evidence_issues'].append('failed_comparability_guard:'+key)
    for name,part in result['components'].items():
        observations=[c for c in part['checks'] if c['analysis_role']=='observation']
        part['failed_observation_ids']=[c['id'] for c in observations if not c['passed']]
        part['signal_state']=('incomplete' if not result['execution_evidence_complete'] and observations else
          'not_observed' if not observations else 'incomplete' if any(c['source_comparison_eligible'] is not True for c in observations) else
          'mismatch_observed' if part['failed_observation_ids'] else 'no_mismatch_observed')
        part['exclusive_continuation_credit_allowed']=name in {'assigned_api_continuation','assigned_native_continuation'}
    return result


def compare_pair(api,ui,gates,*,pair_id,catalog,workflow):
    if set(gates)!=GATES:raise ValueError('Missing or unknown pair-validity gates')
    if any(type(v) is not bool and v is not None for v in gates.values()):raise ValueError('Pair gates must be true, false or unobserved')
    if api['record_id']==ui['record_id'] or api['route'].split('-')[-1]!='api' or ui['route'].split('-')[-1]!='ui':
        raise ValueError('Pair must contain distinct API and UI records')
    accepted=api['accepted_prefix'] and ui['accepted_prefix']
    required=GATES if accepted else GATES-POST_ACCEPTANCE_GATES
    issues=[g for g in sorted(required) if gates[g] is not True]
    if api['accepted_prefix']!=ui['accepted_prefix']:issues.append('prefix_acceptance_differs')
    if api['route'].split('-')[0]!=ui['route'].split('-')[0]:issues.append('producer_interface_differs')
    if not api['execution_evidence_complete'] or not ui['execution_evidence_complete']:issues.append('incomplete_branch_evidence')
    a=api['components']['assigned_api_continuation']['signal_state'];u=ui['components']['assigned_native_continuation']['signal_state']
    overlap=None
    if issues:status='unresolved_pair'
    elif not accepted:status='rejected_prefix_no_continuation_contrast'
    elif a not in {'mismatch_observed','no_mismatch_observed'} or u not in {'mismatch_observed','no_mismatch_observed'}:
        status='unresolved_pair';issues.append('assigned_observation_missing_or_incomplete')
    else:
        status='comparable_accepted_control_pair'
        overlap=('both' if a==u=='mismatch_observed' else 'api_only' if a=='mismatch_observed' else 'ui_only' if u=='mismatch_observed' else 'neither')
    shared=[{'record_id':r['record_id'],'component':name,'failed_check_ids':r['components'][name]['failed_observation_ids']}
            for r in (api,ui) for name in sorted(SHARED) if r['components'][name]['failed_observation_ids']]
    return {'pair_id':pair_id,'catalog':catalog,'workflow_id':workflow,'records':[api['record_id'],ui['record_id']],
            'status':status,'validity_gates':gates,'issues':issues,'accepted_prefixes':accepted,
            'assigned_signal_states':{'api':a,'ui':u},'assigned_signal_overlap':overlap,'shared_mismatches':shared,
            'unresolved_policy_present':api['policy_unresolved'] or ui['policy_unresolved'],
            'primary_evaluation_eligible':False,'adjudicated_root_cause':None}


def counts(pairs,records,singletons):
    overlap=Counter(p['assigned_signal_overlap'] for p in pairs if p['status']=='comparable_accepted_control_pair')
    return {'branch_records':len(records),'declared_pair_entries':len(pairs),'unpaired_control_records':len(singletons),
            'accepted_control_pairs':sum(p['status']=='comparable_accepted_control_pair' for p in pairs),
            'rejected_prefix_pairs':sum(p['status']=='rejected_prefix_no_continuation_contrast' for p in pairs),
            'unresolved_pairs':sum(p['status']=='unresolved_pair' for p in pairs),
            'assigned_check_mismatch_overlap':{k:overlap[k] for k in ('api_only','ui_only','both','neither')},
            'pairs_with_shared_mismatches':sum(bool(p['shared_mismatches']) for p in pairs),
            'primary_evaluation_eligible_pairs':0,'independent_sample_size':None}
