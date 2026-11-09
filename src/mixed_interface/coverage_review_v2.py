"""Reconcile observed identity paths while retaining the registered corpus and gates."""
from collections import Counter
from copy import deepcopy
from .evaluation import digest


def require(condition, message):
    if not condition: raise ValueError(message)


IDENTITY_GAPS = {'realworld_v2_terminal_bridge', 'realworld_v2_job_dispatch',
                 'prospective_normalization_and_extractor_case_binding',
                 'profile_identity_fields_outside_normalization_helper'}
OUTCOME_GAPS = {'petclinic_domain_policy_unresolved', 'petclinic_response_semantics_incomplete',
                'petclinic_state_comparability_unresolved', 'petclinic_variable_observations'}
V7_IDS = ('profile-bio-valid', 'profile-username-null', 'profile-username-length60', 'profile-username-length61')


def reconcile(base, registry, paired, halted):
    require(base['execution_authorized'] is False and base['primary_freeze_complete'] is False,
            'Base coverage promoted')
    require(len(base['rows']) == base['counts']['pair_entries'] + base['counts']['singletons'], 'Base row count differs')
    require(not any(r['primary_dispatch_ready'] for r in base['rows']), 'Base row promoted')
    specs = {c['candidate_id']: c for c in registry['cases']}
    require(len(specs) == len(registry['cases']) == 5, 'Identity registry inventory differs')
    results = paired['verification']['results']
    require(tuple(r['candidate_id'] for r in results) == V7_IDS, 'Paired diagnostic selection differs')
    require(paired['verification']['verified'] is True and paired['verification']['pairs'] == 4
            and paired['verification']['branches'] == 8 and paired['verification']['database_backups'] == 20
            and paired['new_primary_samples'] == 0 and paired['primary_freeze_complete'] is False, 'Diagnostic scope differs')
    require(halted['verification']['verified_halted_ledger'] is True
            and halted['verification']['initial_pair_attempts'] == 5
            and halted['verification']['branches_executed'] == 10
            and halted['campaign_completed'] is False and halted['coverage_promoted'] is False, 'Halted evidence scope differs')
    sequence = halted['verification']['terminal_sequence']
    require(len(sequence) == len(specs), 'Halted terminal inventory differs')
    old = {c['candidate_id']: kind for c, kind in zip(registry['cases'], sequence)}
    current = {r['candidate_id']: r for r in results}
    rows = []
    for original in base['rows']:
        row = deepcopy(original)
        entry = row['inventory_entry']; cid = entry.get('candidate_id')
        execution = [g for g in row['open_binding_gaps'] if g not in OUTCOME_GAPS]
        outcome = [g for g in row['open_binding_gaps'] if g in OUTCOME_GAPS]
        observed = None; resolved = []
        if entry['catalog'] == 'realworld_development' and cid in specs:
            require(row['entry_kind'] == 'pair' and entry['producer_interface'] == 'api', 'Identity route differs')
            require(all(b['source_case_sha256'] == digest(specs[cid]) for b in row['branches']), 'Identity source case differs')
            require({b['continuation_interface'] for b in row['branches']} == {'api', 'ui'}, 'Identity branches differ')
            if cid in current:
                evidence = current[cid]
                require(set(evidence['measurements']) == {'api', 'ui'}, 'Diagnostic branch inventory differs')
                for channel, m in evidence['measurements'].items():
                    require(m['qualified'] is True and m['requirement_policy'] == specs[cid]['expectation'], 'Unqualified or changed requirement')
                    require(m['measurement']['continuation']['interface'] == channel, 'Diagnostic channel differs')
                observed = {'evidence': 'manifests/realworld-paired-database-integration.json',
                            'terminal_kind': evidence['terminal_kind'], 'database_capture': True,
                            'adapter': 'scripts/realworld_identity_case_v2.mjs',
                            'loader': 'scripts/realworld_identity_database_job_v7.py',
                            'scope': 'one exposed engineering pair, bounded diagnostic; not a primary campaign binding'}
            else:
                require(cid == 'profile-username-empty' and old[cid] == 'matched_rejection', 'Unsupported historical identity qualification')
                observed = {'evidence': 'manifests/realworld-identity-halted-integration.json',
                            'terminal_kind': old[cid], 'database_capture': False,
                            'adapter': 'scripts/realworld_identity_case_v1.mjs',
                            'loader': 'scripts/realworld_identity_campaign.py',
                            'scope': 'completed rejection pair within a halted campaign; no database observation'}
            resolved = [g for g in execution if g in IDENTITY_GAPS]
            execution = [g for g in execution if g not in IDENTITY_GAPS]
            # Only three legacy identity rows lack a general prospective campaign binding.
            if row['path_family'] == 'realworld_legacy': execution.append('identity_primary_campaign_binding')
            if specs[cid]['expectation']['outcome'] == 'reject' and 'unexpected_acceptance_normalization_and_continuation' not in execution:
                execution.append('unexpected_acceptance_normalization_and_continuation')
            if specs[cid]['expectation']['outcome'] == 'unknown' or specs[cid]['expectation']['category'] == 'unresolved':
                outcome.append('identity_requirement_policy_unresolved')
            if observed['terminal_kind'] == 'missing_evidence': outcome.append('identity_semantic_evidence_incomplete')
            if observed['evidence'] not in row['recorded_engineering_evidence']:
                row['recorded_engineering_evidence'].append(observed['evidence'])
        row.update(observed_identity_path=observed, resolved_for_observed_path=resolved,
                   remaining_execution_requirements=execution, retained_outcome_limits=outcome)
        rows.append(row)
    require(sum(r['observed_identity_path'] is not None for r in rows) == 5, 'Retained identity coverage differs')
    return {'schema_version': 2, 'kind': 'retained_corpus_readiness_review',
            'execution_authorized': False, 'primary_freeze_complete': False, 'independent_sample_size': None,
            'counts': {**deepcopy(base['counts']), 'entries_with_recorded_engineering_evidence': sum(bool(r['recorded_engineering_evidence']) for r in rows),
                       'identity_entries_with_observed_path': 5, 'identity_entries_with_branch_database_capture': 4},
            'remaining_execution_requirement_counts': dict(sorted(Counter(g for r in rows for g in r['remaining_execution_requirements']).items())),
            'retained_outcome_limit_counts': dict(sorted(Counter(g for r in rows for g in r['retained_outcome_limits']).items())),
            'rows': rows,
            'interpretation': 'Original path-family and gap fields describe the v1 baseline. Supplementary observed-path resolution is limited to exact exposed cases. Outcome limits are retained observations, not permission to erase cases or claim defects. P2-P5 remain open.'}
