#!/usr/bin/env python3
"""Source-qualified component extraction of the twelve hosted integrity controls.

This version-specific extension preserves the historical reducer and records the
finite trace projection used to reuse its entity/graph predicates. New snapshot,
binding, capture and cleanup evidence is checked separately, never discarded.
"""
from copy import deepcopy
import hashlib,json
from pathlib import Path
import summarize_petclinic_oracle_components as legacy
import validate_petclinic_integrity as integrity

ROOT=Path(__file__).resolve().parents[1]
RUNNER='c7b2215f57e0ca1e67cc799acfbd027f37489c0f3bbc2217406629bed3d750b7'
BASE_REDUCER='7c97bb49033345b9274df6e1f976571d8234b426d29266daa0a596a8b289f4c9'
VALIDATOR='0e1d27a4ed20b043b910192e8adb22438cb3184391bfc07e3d3beefe23ffcde1'
HELPERS={'petclinic_integrity.mjs': '60d5f484a3f4939753bf68d5a581a220dd727681beda8cc2989cb18969df6bc1', 'petclinic_response_capture.mjs': 'db710ed6d36aac38405b4cc746d5e0ee1c95a54e76e7d2860477f5c24f7d5868', 'petclinic_cleanup.mjs': 'a30e5b89c813b67b37e537b0b4c1aac3caa3892d13ff14dad547d3780be01e3c'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_bytes())

def project_trace(result):
    """Explicit derived view; raw observation and its hash are always retained."""
    projected=deepcopy(result);trace=[];omitted=[]
    allowed_bindings=set()
    if result['prefix_status']==201 and result['template']!='owner_address_edit':
        kind='pets' if result['template']=='pet_rename' else 'visits'
        located=legacy.locate(result['post_prefix_graph'],kind,result['prefix_response']['id'])
        if not located:raise ValueError('Missing target graph binding')
        allowed_bindings.add('/owners/'+str(located[0]['id']))
        if kind=='visits':allowed_bindings.add('/pets/'+str(located[1]['id']))
    bindings=[e for e in result['trace'] if e.get('phase')=='binding_read']
    if len(bindings)!=len(allowed_bindings) or {e['path'] for e in bindings}!=allowed_bindings or any(e.get('source')!='direct_api' or e.get('method')!='GET' or e.get('status')!=200 for e in bindings):
        raise ValueError('Unknown, duplicate, missing or failed shared binding read')
    for index,event in enumerate(projected['trace']):
        if event.get('source')=='ui_request' or event.get('phase')=='pre_candidate_state':
            omitted.append({'trace_index':index,'reason':'accounted_in_capture_or_pre_candidate_snapshot_extension'})
            continue
        if event.get('phase')=='binding_read':
            if result['oracle']=='api_semantic' and result['template']=='visit_reschedule' and event['path'].startswith('/pets/'):
                event['phase']='continuation_read'
            else:
                omitted.append({'trace_index':index,'reason':'shared_binding_read_accounted_in_extension'});continue
        trace.append(event)
    projected['trace']=trace
    return projected,omitted

def refresh(part,eligible):
    part['failed_check_ids']=[c['id'] for c in part['checks'] if c['passed'] is False]
    part['mismatch_observed']=bool(part['failed_check_ids'])
    applicable=bool(part['checks'] or part.get('observations'))
    part['comparison_eligible']=eligible and applicable
    if applicable:part['status']='incomplete_or_invalid_evidence' if not eligible else 'check_mismatch_observed' if part['mismatch_observed'] else 'no_check_mismatch_observed'


def reduce_control(raw,registered,registry,expected):
    checked=integrity.validate_case(raw,expected)
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
    result['source_version']='petclinic_integrity_controls_631a667'
    result['interpretation']='Source-qualified engineering controls; shared pre-continuation GETs are not API-exclusive observations. No defect adjudication.'
    return result


def summarize_compact(directory):
    directory=Path(directory)
    if sha(ROOT/'scripts/summarize_petclinic_oracle_components.py')!=BASE_REDUCER or sha(ROOT/'scripts/validate_petclinic_integrity.py')!=VALIDATOR:
        raise ValueError('Unsupported extraction dependency version')
    plan=load(directory/'petclinic-integrity-plan.json');summary=load(directory/'run-summary.json')
    validation=load(directory/'petclinic-integrity-validation.json');registry=load(ROOT/'manifests/petclinic-candidates-v1.json')
    if summary['runner_sha256']!=RUNNER or plan['source_sha256']['scripts/petclinic_boundary_slice.mjs']!=RUNNER:
        raise ValueError('Unsupported executing PetClinic source')
    if summary['registry_sha256']!=sha(ROOT/'manifests/petclinic-candidates-v1.json'):
        raise ValueError('Changed registry')
    for name,pin in HELPERS.items():
        if plan['source_sha256']['scripts/'+name]!=pin:raise ValueError('Unsupported helper: '+name)
    if validation['plan_sha256']!=sha(directory/'petclinic-integrity-plan.json') or validation['status']!='passed':
        raise ValueError('Unqualified control run')
    expected=plan['selection']['cases'];wanted=[(c['id'],o) for c in expected for o in plan['selection']['oracles']]
    if len(wanted)!=12 or [(b['candidate_id'],b['oracle']) for b in summary['branches']]!=wanted:
        raise ValueError('Missing, duplicate, reordered or additional branches')
    pins={(c['candidate_id'],c['oracle']):c for c in validation['cases']}
    observations=[];inputs={}
    for branch in summary['branches']:
        key=(branch['candidate_id'],branch['oracle']);name=key[0]+'-'+key[1]+'.json'
        if branch['result']!=name:raise ValueError('Unexpected branch path')
        path=directory/'observations'/name;inputs['observations/'+name]=sha(path)
        if inputs['observations/'+name]!=pins[key]['observation_sha256']:raise ValueError('Changed branch bytes: '+name)
        raw=load(path)
        for field in ('candidate_id','oracle','status','prefix_status'):
            if raw.get(field)!=branch.get(field):raise ValueError('Summary/branch disagreement: '+field)
        for key2,source in [('integrity','petclinic_integrity.mjs'),('capture_integrity','petclinic_response_capture.mjs')]:
            if raw[key2]['helper_sha256']!=plan['source_sha256']['scripts/'+source]:raise ValueError('Changed executing helper')
        registered=next(c for c in registry['candidates'] if c['id']==key[0]);control=next(c for c in expected if c['id']==key[0])
        result=reduce_control(raw,registered,registry,control)
        result['case_id']=name[:-5];result['candidate_id']=key[0]
        observations.append(result)
    return {'kind':'petclinic_integrity_component_observations','status':'complete_observations' if all(c['execution_evidence_complete'] for c in observations) else 'incomplete_or_invalid_evidence',
        'scope':'twelve_previously_examined_hosted_integrity_control_branches','source_runner_sha256':RUNNER,
        'source_plan_sha256':sha(directory/'petclinic-integrity-plan.json'),'input_file_sha256':inputs,
        'reducer_sha256':sha(Path(__file__)),'dependency_sha256':{'legacy_reducer':BASE_REDUCER,'integrity_validator':VALIDATOR},
        'case_count':len(observations),'cases':observations,'primary_freeze_complete':False,'application_executions_added':0}
