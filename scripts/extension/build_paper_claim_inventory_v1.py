#!/usr/bin/env python3
"""Index principal evidence for the original RQs; do not pool study counts."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    'primary-results-v1': ['counts', 'assigned_overlap_counts', 'defects_confirmed', 'claim_scope', 'interpretation'],
    'experiment-completion-v3': ['remaining_registered_units', 'not_established', 'corrected_category_counts', 'scope'],
    'production-extension-summary-v1': ['initial_boundary_counts', 'initial_pairs', 'initial_valid_controls', 'finite_pairs', 'baseline_native_only_signals', 'natural_defects_confirmed', 'interpretation'],
    'independent-input-summary-v1': ['selected_inputs', 'executed_initial_inputs', 'initial_sample_counts', 'total_scientific_pairs', 'native_only_detections', 'natural_defects_confirmed', 'scope'],
    'benchmark-progress-v6': ['selected_family_count', 'frozen_specifications', 'scientific_accounting', 'q1_contribution_established'],
    'contract-information-ablation-v1': ['new_application_executions', 'aggregate_alert_records', 'agreement_increment_over_complete_transition', 'limits'],
    'netbox-information-reference-replay-v1': ['historical_faults_represented', 'independent_ground_truth', 'automatic_inference_evaluated', 'new_application_executions'],
    'restestbench-mutant-runtime-results-v1': ['all_trials_accounted_with_records', 'new_application_defects_claimed', 'candidate_detections_are_not_adjudicated_semantic_defects'],
    'vibe-per-test-pilot-results-v1': ['outcome_exposed_exploratory_pilot', 'semantic_fault_adjudication_complete'],
    'openapi-adapter-results-v1': ['subjects', 'case_repetitions_are_independent_defects', 'q1_readiness_established'],
}


def build():
    records, hashes = {}, {}
    for name, keys in SOURCES.items():
        p = ROOT / 'manifests' / (name + '.json')
        raw = p.read_bytes()
        data = json.loads(raw)
        records[name] = {key: data[key] for key in keys}
        hashes[str(p.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
    mutant = json.loads((ROOT / 'manifests/restestbench-mutant-runtime-results-v1.json').read_text())
    records['restestbench-mutant-runtime-results-v1']['service_counts'] = {
        name: {k: row[k] for k in ('recorded_controls', 'passing_controls', 'recorded_mutants', 'candidate_detections')}
        for name, row in mutant['services'].items()}
    vibe = json.loads((ROOT / 'manifests/vibe-per-test-pilot-results-v1.json').read_text())
    records['vibe-per-test-pilot-results-v1']['level_counts'] = {
        name: {k: row[k] for k in ('paired_qualified_mutant_comparisons', 'aggregate_kills_in_qualified_comparisons', 'identified_new_failures_in_qualified_comparisons', 'disagreements')}
        for name, row in vibe['levels'].items()}
    return {
        'kind': 'paper_principal_claim_evidence_inventory_v1',
        'scope': 'Principal stage summaries for the original four research questions, not a new raw-data validation or exhaustive catalog of every file.',
        'rq_assessment': {
            'RQ1_workflow_defects': 'Historical/exposed observations exist; newer independent-input and benchmark cohorts establish no new confirmed natural defects. Keep statuses separate.',
            'RQ2_guided_selection': 'Timed selector efficacy is explicitly not established in the original completion manifest. Engineering integration and later diagnostic counts do not establish it.',
            'RQ3_guidance_and_oracles': 'Information ablation and mutant qualification exist; neither supplies the original complete guidance-by-oracle efficacy comparison or a demonstrated new generator advantage.',
            'RQ4_agent_completion': 'No agent-performance intervention is established by these studies. Replaying released generated tests is not an agent task-completion experiment.',
        },
        'independent_sample_total': None,
        'reason_no_pooled_total': 'Initial cases, controls, repeated variants, historic faults, mutants and workflows are different dependent units and study populations.',
        'records': records, 'source_sha256': hashes,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    value = build()
    path = ROOT / 'manifests/paper-claim-inventory-v1.json'
    if args.verify:
        assert json.loads(path.read_text()) == value
    else:
        path.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(value['rq_assessment'], indent=2))
