"""Reconcile verified generated attempts without changing primary readiness."""
from collections import Counter
from copy import deepcopy
from .evaluation import digest
from .coverage_review_v2 import require

GENERATED_GAPS = {'generated_normalization_and_extractor_case_binding',
                  'generated_realworld_v2_job_dispatch', 'generated_realworld_v2_terminal_bridge'}
EXPECTED = {(42729694261, f'generated-{i:03d}') for i in range(2)} | {
            (42761024624, f'generated-{i:03d}') for i in range(1,9)}


def reconcile(previous, attempts):
    require(previous['execution_authorized'] is False and previous['primary_freeze_complete'] is False,
            'Previous review promoted')
    rows=deepcopy(previous['rows'])
    require(len(rows)==75 and not any(r['primary_dispatch_ready'] for r in rows), 'Corpus changed or promoted')
    index={r['inventory_entry']['pair_id']:r for r in rows if r['path_family']=='realworld_generated'}
    require(len(index)==9, 'Generated inventory differs')
    seen=set()
    for row in index.values():
        row['observed_generated_attempts']=[]
        row['generated_resolved_for_observed_path']=[]
    for a in attempts:
        job=a['job'];key=(a['application_run'],job['job_id'])
        require(key in EXPECTED and key not in seen, 'Foreign or duplicate attempt');seen.add(key)
        pid=job['pair']['pair_id'];require(pid in index,'Foreign generated pair');row=index[pid]
        require(job['pair']==row['inventory_entry'] and row['entry_kind']=='pair','Pair semantics differ')
        require(job['reference_pair_id']==row['reference_control_pair_id'], 'Reference binding differs')
        declared={b['channel']:b for b in job['branches']}
        require(len(job['branches'])==2 and set(declared)==set(a['specs'])==set(a['branch_observations'])=={'api','ui'},'Branch inventory differs')
        for b in row['branches']:
            channel=b['continuation_interface'];spec=a['specs'][channel];d=declared[channel]
            require(d['case_id']==b['source_case_id']==spec['case_id'] and
                    d['source_case_sha256']==b['source_case_sha256']==digest(spec), 'Source case differs')
            require(d['fresh_reset_required'] is True and
                    [o['interface'] for o in spec['operations']]==[row['inventory_entry']['producer_interface'],channel], 'Route or reset differs')
        require(a['new_primary_samples']==0 and a['primary_freeze_complete'] is False,'Attempt promoted')
        observation={k:deepcopy(v) for k,v in a.items() if k not in ('job','specs')}
        observation['job_id']=job['job_id']
        row['observed_generated_attempts'].append(observation)
        if a['evidence'] not in row['recorded_engineering_evidence']:row['recorded_engineering_evidence'].append(a['evidence'])
        resolved=[g for g in row['remaining_execution_requirements'] if g in GENERATED_GAPS]
        row['generated_resolved_for_observed_path']+=resolved
        row['remaining_execution_requirements']=[g for g in row['remaining_execution_requirements'] if g not in GENERATED_GAPS]
        if 'generated_primary_campaign_binding' not in row['remaining_execution_requirements']:
            row['remaining_execution_requirements'].append('generated_primary_campaign_binding')
        limits=row['retained_outcome_limits']
        if a['terminal_kind']=='unresolved_policy':limits.append('generated_requirement_policy_unresolved')
        if a['terminal_kind']=='missing_evidence':limits.append('generated_semantic_evidence_incomplete')
        if not all(b['assigned_continuation_reached'] for b in a['branch_observations'].values()):
            limits.append('generated_assigned_continuation_not_exercised')
        # Unknown policy remains unknown even if missing evidence dominates its terminal.
        if any(s['expectation']['outcome']=='unknown' for s in a['specs'].values()):
            limits.append('generated_requirement_policy_unresolved')
    require(seen==EXPECTED and all(r['observed_generated_attempts'] for r in index.values()),'Attempt inventory incomplete')
    for row in index.values():
        for key in ('remaining_execution_requirements','retained_outcome_limits','generated_resolved_for_observed_path'):
            row[key]=list(dict.fromkeys(row[key]))
    result=deepcopy(previous);result.update(schema_version=4,rows=rows)
    result['counts'].update(entries_with_recorded_engineering_evidence=sum(bool(r['recorded_engineering_evidence']) for r in rows),
        generated_entries_with_observed_attempt=len(index),generated_observed_attempts=len(attempts),
        generated_entries_with_both_continuations_reached=sum(any(all(b['assigned_continuation_reached'] for b in a['branch_observations'].values()) for a in r['observed_generated_attempts']) for r in index.values()))
    result['remaining_execution_requirement_counts']=dict(sorted(Counter(g for r in rows for g in r['remaining_execution_requirements']).items()))
    result['retained_outcome_limit_counts']=dict(sorted(Counter(g for r in rows for g in r['retained_outcome_limits']).items()))
    result['interpretation']='Exact generated reference and mutation attempts supplement v3. Repeated reference attempts are not new catalog entries. Rejected or unreadable prefixes do not exercise assigned continuations. The final semantic halt and unknown requirements remain attached to their attempts. Observed-path qualification does not authorize primary dispatch; P2-P5 remain open.'
    return result
