"""Deterministic retained-corpus bindings. Describes evidence; never launches jobs."""
from collections import Counter
from copy import deepcopy
from .evaluation import digest, generated_pairs, legacy_pairs

CATALOGS = ('realworld_development','petclinic_development','realworld_generated_integration','quartz_generated_v2')


def require(value, message):
    if not value: raise ValueError(message)


def reconstruct(registries, contracts):
    workflows = {c['registry_workflow']:name for name,c in contracts['workflows'].items()}
    pairs=[]; singletons=[]
    for catalog in CATALOGS[:2]:
        p,s=legacy_pairs(registries[catalog],catalog,workflows,petclinic=catalog=='petclinic_development')
        pairs.extend(p);singletons.extend(s)
    for catalog,workflow,exposure in (
        ('realworld_generated_integration','realworld.article_create_body_edit',{'route_only':'examined_engineering_control','payload_mutation':'examined_engineering_candidate'}),
        ('quartz_generated_v2','quartz.stored_job_create_description_edit',{'route_only':'examined_source_inspected_control','payload_mutation':'source_inspected_boundary_not_executed'})):
        pairs.extend(generated_pairs(registries[catalog],catalog,workflow,exposure))
    return pairs,singletons


def build(inventory, registries, contracts, selections):
    require(set(registries)==set(CATALOGS),'Catalog coverage differs')
    pairs,singletons=reconstruct(registries,contracts)
    require(pairs==inventory['pairs'] and singletons==inventory['unpaired_controls'],'Inventory semantics or exposure differ from registered sources')
    require(len(pairs)==inventory['pair_entries'] and len(singletons)==inventory['singleton_control_entries'],'Inventory counts differ')
    require(set(p['workflow_id'] for p in pairs)==set(contracts['workflows']),'Workflow contract coverage differs')
    by_id={p['pair_id']:p for p in pairs+singletons}
    require(len(by_id)==len(pairs)+len(singletons),'Duplicate pair identity')
    case_indexes={c:{r['id' if c=='petclinic_development' else 'candidate_id' if c=='realworld_development' else 'case_id']:r for r in registries[c]['candidates' if c=='petclinic_development' else 'cases']} for c in CATALOGS}
    rw_controls={c['candidate_id']:c for c in selections['realworld_paired']['cases']}
    rw_rejections={c['candidate_id']:c for c in selections.get('realworld_rejection',{}).get('cases',[]) if c['expectation']['outcome']=='reject'}
    rw_fields={c['candidate_id']:c for c in selections.get('realworld_fields',{}).get('cases',[])}
    pc_controls={c['id'] for c in selections['petclinic_integrity']['cases']}
    rw_legacy={c['candidate_id'] for c in selections['realworld_integrity']['legacy_branches']}
    rw_generated={c['case_id'] for c in selections['realworld_integrity']['generated_cases']}
    generated_controls={}
    for p in pairs:
        if p.get('intervention')=='route_only':
            key=(p['catalog'],p['workflow_id'],p['producer_interface'])
            require(key not in generated_controls,'Ambiguous generated reference control')
            generated_controls[key]=p['pair_id']
    rows=[]
    for p in pairs+singletons:
        catalog=p['catalog'];wf=contracts['workflows'][p['workflow_id']]
        paired=p in pairs
        channels=list(p.get('case_ids',{})) if 'case_ids' in p else p['continuations']
        channels=sorted(channels)
        specs={c:case_indexes[catalog][p['case_ids'][c] if 'case_ids' in p else p['candidate_id']] for c in channels}
        evidence=[]; gaps=[]
        if not paired:
            reference=None
        elif 'case_ids' in p:
            reference=generated_controls.get((catalog,p['workflow_id'],p['producer_interface']))
            require(reference is not None,'Missing same-producer generated reference')
        else:
            reference=catalog+'::'+wf['reference_control_candidate']
        if reference is not None:
            require(reference in by_id and by_id[reference] in pairs,'Reference control is absent or unpaired')
            control=by_id[reference]
            require((control['catalog'],control['workflow_id'],control['producer_interface'])==(catalog,p['workflow_id'],p['producer_interface']),'Reference crosses catalog, workflow or producer')
            if 'case_ids' in control:
                control_specs=[case_indexes[catalog][cid] for cid in control['case_ids'].values()]
                require(all(c['intervention']=='route_only' and c.get('mutation') is None and c['expectation']['outcome']=='accept' for c in control_specs),'Generated reference is not an accepted route control')
            else:
                c=case_indexes[catalog][control['candidate_id']]
                require(c.get('kind')=='valid_control' if catalog=='petclinic_development' else c['expectation']['outcome']=='accept','Reference is not a positive control')
        if catalog=='realworld_development':
            cid=p['candidate_id'];spec=specs[channels[0]]
            exact=cid in rw_controls and rw_controls[cid]==spec
            rejected_exact=cid in rw_rejections and rw_rejections[cid]==spec
            field_exact=cid not in rw_controls and cid not in rw_rejections and cid in rw_fields and rw_fields[cid]==spec
            family='realworld_paired_controls' if exact else 'realworld_rejection_controls' if rejected_exact else 'realworld_field_controls' if field_exact else 'realworld_legacy'
            if exact:evidence.append('manifests/realworld-paired-runner-qualification.json')
            if cid in rw_legacy:evidence.append('manifests/realworld-execution-integrity.json')
            gaps=['realworld_v2_terminal_bridge','realworld_v2_job_dispatch']
            qualification=contracts['path_families'][family].get('engineering_qualification')
            if exact and qualification:
                evidence.append(qualification)
                gaps=[]
            if rejected_exact and qualification:
                evidence.append(qualification)
                gaps=['unexpected_acceptance_normalization_and_continuation']
            elif field_exact and qualification:
                evidence.append(qualification)
                gaps=['unexpected_acceptance_normalization_and_continuation'] if spec['expectation']['outcome']=='reject' else []
            elif not exact:gaps.append('prospective_normalization_and_extractor_case_binding')
            if p['workflow_id'].endswith('profile_update_settings_edit') and any(k not in ('bio','image') for k in spec['prefix_payload']):gaps.append('profile_identity_fields_outside_normalization_helper')
        elif catalog=='petclinic_development':
            family='petclinic_integrity'
            if p['candidate_id'] in pc_controls:evidence.append('manifests/petclinic-execution-integrity.json')
            gaps=['petclinic_v2_terminal_bridge','petclinic_v2_job_dispatch']
            if p['candidate_id'] not in pc_controls:gaps.append('petclinic_extractor_beyond_six_control_candidates')
            selected=selections.get('petclinic_terminal',{})
            qualified=contracts['path_families'].get('petclinic_terminal_controls',{}).get('engineering_qualification')
            exact=digest(registries[catalog])==selected.get('registry_semantic_sha256')
            if exact and qualified and p['candidate_id'] in {c['id'] for c in selected.get('selection',[])}:
                family='petclinic_terminal_controls';evidence.append(qualified)
                gaps=['petclinic_unexpected_prefix_outcome_extraction']
            expanded=selections.get('petclinic_expanded',{})
            qualified=contracts['path_families'].get('petclinic_expanded',{}).get('engineering_qualification')
            if qualified and digest(registries[catalog])==expanded.get('registry_semantic_sha256') and p['candidate_id'] in expanded.get('qualified_candidate_ids',[]):
                family='petclinic_expanded';evidence.append(qualified);gaps=[]
                kinds=expanded['verification']['candidate_terminal_kinds'][p['candidate_id']]
                for kind,gap in [('application_response_failure','petclinic_response_semantics_incomplete'),('unresolved_policy','petclinic_domain_policy_unresolved'),('incomparable_observation','petclinic_state_comparability_unresolved')]:
                    if kind in kinds:gaps.append(gap)
                for report in expanded['verification']['batches'].values():
                    if any(row['pair_id']==p['candidate_id'] and row['status']=='variable_observations' for row in report['repeat_summary']['pairs']):gaps.append('petclinic_variable_observations')
        elif catalog=='realworld_generated_integration':
            family='realworld_generated'
            if set(p['case_ids'].values())<=rw_generated:evidence.append('manifests/realworld-execution-integrity.json')
            gaps=['generated_realworld_v2_terminal_bridge','generated_realworld_v2_job_dispatch','generated_normalization_and_extractor_case_binding']
        else:
            family='quartz_terminal'
            if p['intervention']=='route_only':evidence.append('manifests/quartz-terminal-integration-qualification.json')
            else:gaps=['quartz_primary_campaign_selection_and_case_binding']
        if not paired:gaps.append('singleton_accounting_without_paired_contrast')
        path=contracts['path_families'][family]
        branches=[]
        for channel in channels:
            spec=specs[channel]
            branches.append({'logical_branch_id':p['pair_id']+'::continuation='+channel,
                'source_case_id':p['case_ids'][channel] if 'case_ids' in p else p['candidate_id'],
                'producer_interface':p['producer_interface'],'continuation_interface':channel,
                'source_case_sha256':digest(spec),
                'runner_channel':{'api':'api_semantic','ui':'fresh_ui'}[channel] if catalog=='petclinic_development' else channel})
        rows.append({'inventory_entry':deepcopy(p),'entry_kind':'pair' if paired else 'singleton',
            'source_registry':contracts['catalog_sources'][catalog], 'branches':branches,
            'reference_control_pair_id':reference,'workflow_contract':p['workflow_id'],'path_family':family,
            'available_adapter':path['adapter'],'available_runner':path['runner'],'available_extractor':path['extractor'],
            'terminal_v2_bridge':path['terminal_v2_bridge'],'selection_scope':path['selection_scope'],
            'recorded_engineering_evidence':evidence,
            'evidence_limit':'Named archived cohort only; does not qualify this entire workflow, changed inputs or all failure paths.',
            'open_binding_gaps':gaps,'primary_dispatch_ready':False})
    return {'schema_version':1,'kind':'retained_corpus_executable_coverage','primary_freeze_complete':False,
        'execution_authorized':False,'independent_sample_size':None,
        'counts':{'pair_entries':len(pairs),'singletons':len(singletons),'logical_branches':sum(len(r['branches']) for r in rows),
                  'workflow_templates':len(contracts['workflows']),'by_path_family':dict(Counter(r['path_family'] for r in rows)),
                  'entries_with_recorded_engineering_evidence':sum(bool(r['recorded_engineering_evidence']) for r in rows),
                  'primary_dispatch_ready':0},
        'open_gap_counts':dict(sorted(Counter(g for r in rows for g in r['open_binding_gaps']).items())),
        'engineering_controls_outside_retained_inventory':[cid for cid in rw_controls if cid not in case_indexes['realworld_development']],
        'rows':rows}


def validate(saved, inventory, registries, contracts, selections):
    require(saved==build(inventory,registries,contracts,selections),'Coverage, qualification or dispatch flags differ from source-derived map')
    return True


def require_primary_dispatch(coverage, entry_ids):
    """No implementation here can authorize primary dispatch from a coverage map."""
    require(bool(entry_ids) and len(entry_ids)==len(set(entry_ids)),'Empty or duplicate selection')
    rows={r['inventory_entry']['pair_id']:r for r in coverage['rows']}
    require(set(entry_ids)<=set(rows),'Foreign entry selection')
    raise ValueError('Coverage inventory is not a frozen execution manifest; P2 bindings and P3-P5 remain required')
