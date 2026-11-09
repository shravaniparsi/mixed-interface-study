"""Add exact exposed legacy attempts and separate database observations to v2."""
from collections import Counter
from copy import deepcopy
from .evaluation import digest
from .coverage_review_v2 import require

LEGACY_GAPS = {'realworld_v2_terminal_bridge', 'realworld_v2_job_dispatch',
               'prospective_normalization_and_extractor_case_binding',
               'singleton_accounting_without_paired_contrast'}


def reconcile(previous, attempts, diagnostics):
    require(previous['primary_freeze_complete'] is False and previous['execution_authorized'] is False,
            'Previous review promoted')
    rows = deepcopy(previous['rows'])
    require(len(rows) == 75 and not any(r['primary_dispatch_ready'] for r in rows), 'Corpus changed or promoted')
    index = {r['inventory_entry']['candidate_id']: r for r in rows
             if r['inventory_entry']['catalog'] == 'realworld_development'}
    seen = set()
    for r in rows:
        r['observed_legacy_attempts'] = []
        r['isolated_database_observations'] = []
        r['legacy_resolved_for_observed_path'] = []
    for a in attempts:
        cid = a['spec']['candidate_id']; key = (a['application_run'], a['job_id'])
        require(key not in seen, 'Duplicate attempt'); seen.add(key)
        require(cid in index, 'Foreign legacy candidate'); row = index[cid]
        require(a['entry_kind'] == row['entry_kind'], 'Pair/singleton changed')
        require(all(b['source_case_sha256'] == digest(a['spec']) for b in row['branches']), 'Source case differs')
        require(set(a['channels']) == {b['continuation_interface'] for b in row['branches']}, 'Branch cardinality differs')
        require(a['primary_freeze_complete'] is False and a['new_primary_samples'] == 0, 'Attempt promoted')
        observation = {k: deepcopy(v) for k,v in a.items() if k != 'spec'}
        row['observed_legacy_attempts'].append(observation)
        if a['evidence'] not in row['recorded_engineering_evidence']: row['recorded_engineering_evidence'].append(a['evidence'])
        resolved = [g for g in row['remaining_execution_requirements'] if g in LEGACY_GAPS]
        row['legacy_resolved_for_observed_path'] += resolved
        row['remaining_execution_requirements'] = [g for g in row['remaining_execution_requirements'] if g not in LEGACY_GAPS]
        if resolved: row['remaining_execution_requirements'].append('legacy_primary_campaign_binding')
        limits = row['retained_outcome_limits']
        if a['spec']['expectation']['outcome'] == 'unknown': limits.append('legacy_requirement_policy_unresolved')
        if a['terminal_kind'] == 'missing_evidence': limits.append('legacy_semantic_evidence_incomplete')
        if a['terminal_kind'] == 'incomparable_observation': limits.append('legacy_archived_pair_incomparable')
        replay = a.get('retrospective_comparison')
        if replay and replay['reference_comparison_qualified']:
            require(a['entry_kind'] == 'pair' and replay['original_kind'] == a['terminal_kind'], 'Replay scope differs')
            require(replay['prospective_dispatch_qualified'] is False and replay['new_primary_samples'] == 0, 'Replay promoted')
            if replay['derived_kind'] != a['terminal_kind']:
                row['remaining_execution_requirements'].append('prospective_reference_comparison_binding')
    require(len(seen) == 11 and sum(bool(r['observed_legacy_attempts']) for r in rows) == 9, 'Observed legacy inventory differs')
    seen_db = set()
    for d in diagnostics:
        cid = d['measurement']['candidate_id']; key = (d['evidence'], cid)
        require(key not in seen_db and cid in index, 'Duplicate or foreign database case'); seen_db.add(key)
        row = index[cid]
        require(all(b['source_case_sha256'] == digest(d['spec']) for b in row['branches']), 'Database source case differs')
        require(d['measurement']['requirement_policy'] == d['spec']['expectation'], 'Database policy differs')
        require(d['new_primary_samples'] == 0 and d['primary_freeze_complete'] is False, 'Database observation promoted')
        row['isolated_database_observations'].append({k:deepcopy(v) for k,v in d.items() if k != 'spec'})
        if d['evidence'] not in row['recorded_engineering_evidence']: row['recorded_engineering_evidence'].append(d['evidence'])
    require(len(seen_db) == 6, 'Database diagnostic inventory differs')
    for r in rows:
        for k in ('remaining_execution_requirements', 'retained_outcome_limits', 'legacy_resolved_for_observed_path'):
            r[k] = list(dict.fromkeys(r[k]))
    result = deepcopy(previous)
    result.update(schema_version=3, rows=rows)
    result['counts'].update(entries_with_recorded_engineering_evidence=sum(bool(r['recorded_engineering_evidence']) for r in rows),
                            legacy_entries_with_observed_attempt=9, isolated_database_entries=6)
    result['remaining_execution_requirement_counts'] = dict(sorted(Counter(g for r in rows for g in r['remaining_execution_requirements']).items()))
    result['retained_outcome_limit_counts'] = dict(sorted(Counter(g for r in rows for g in r['retained_outcome_limits']).items()))
    result['interpretation'] = ('Exact exposed attempts only. v8 remains halted; v9 is separate. Isolated database measurements do not fill missing continuation evidence. Retrospective comparison does not rewrite archived terminals. Counts are catalog entries, not independent samples. P2-P5 remain open.')
    return result
