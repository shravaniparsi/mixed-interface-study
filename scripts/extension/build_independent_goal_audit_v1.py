#!/usr/bin/env python3
"""Keep prospective-study denominators separate from outcome-exposed calibration."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/independent-input-provenance-audit-v1'
SOURCES = [
    'manifests/independent-input-selection-v1.json',
    'manifests/independent-input-summary-v1.json',
    'manifests/independent-input-cost-v1.json',
    'manifests/netbox-config-defaults-registration-v2.json',
    'manifests/netbox-config-defaults-results-v2.json',
    'manifests/vibe-per-test-pilot-results-v1.json',
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def build():
    selection, summary, cost, netbox_reg, netbox, vibe = map(read, SOURCES)
    history = json.loads((BASE / 'history-check.json').read_text())
    expected_runs = {r['run_id'] for r in summary['runs']}
    assert {r['run_id'] for r in history['records']} == expected_runs
    paths = set()
    for r in history['records']:
        key = (r['run_id'], r['path']); assert key not in paths; paths.add(key)
        assert r['present_at_run_head']
        raw = (BASE / r['run_id'] / r['path']).read_bytes()
        assert sha(raw) == r['at_run_sha256']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == r['git_blob']
        current = (ROOT / r['path']).read_bytes()
        assert sha(current) == r['current_sha256']
        assert (raw == current) == r['unchanged_since_run']
        result = next(run for run in summary['runs'] if run['run_id'] == r['run_id'])
        assert read(result['proof'])['source_commit'] == r['source_commit']
    workflows = summary['workflow_selection']
    assert {r['workflow'] for r in workflows} == {r['id'] for r in selection['workflows']}
    assert summary['selected_inputs'] == sum(r['selected_inputs'] for r in workflows)
    assert summary['executed_initial_inputs'] == sum(r['executed_initial_inputs'] for r in workflows)
    assert summary['selected_inputs'] - summary['executed_initial_inputs'] == len(summary['unexecuted_selected_input_ids'])
    assert sum(summary['initial_sample_counts'].values()) == summary['executed_initial_inputs']
    assert summary['total_scientific_pairs'] == sum(summary[k] for k in ['executed_initial_inputs', 'initial_valid_control_pairs', 'followup_case_pairs', 'followup_valid_control_pairs'])
    job_ids = [j['id'] for r in cost['runs'] for j in r['jobs']]
    assert len(job_ids) == len(set(job_ids)) == cost['jobs']
    seconds = sum(j['elapsed_seconds'] for r in cost['runs'] for j in r['jobs'])
    assert abs(seconds / 60 - cost['job_elapsed_minutes']) < 0.001
    return {
        'kind': 'independent_input_goal_evidence_audit_v1',
        'run_head_file_checks': len(history['records']),
        'files_missing_at_run_head': sum(not r['present_at_run_head'] for r in history['records']),
        'files_changed_since_run': sum(not r['unchanged_since_run'] for r in history['records']),
        'chronology_scope': 'Git contents at scientific run heads; does not prove researcher blinding or absence of prior source inspection.',
        'workflow_candidates': len(workflows),
        'qualified_workflows': sum(r['executed_initial_inputs'] > 0 for r in workflows),
        'excluded_workflows': [r for r in workflows if r['executed_initial_inputs'] == 0],
        'selected_input_count': summary['selected_inputs'],
        'executed_initial_input_count': summary['executed_initial_inputs'],
        'unexecuted_selected_input_count': len(summary['unexecuted_selected_input_ids']),
        'scientific_pair_execution_count': summary['total_scientific_pairs'],
        'incremental_native_detections': summary['native_only_detections'],
        'confirmed_natural_defects': summary['natural_defects_confirmed'],
        'required_repeats_complete': summary['all_required_repeats_complete'],
        'application_holdout': selection['application_holdout'],
        'all_workflow_exposure_disclosures': selection['workflows'],
        'independent_study_application_jobs': len(job_ids),
        'independent_study_application_job_minutes': seconds / 60,
        'independent_study_paid_model_calls': cost['paid_model_calls'],
        'later_calibrations_add_independent_study_inputs': 0,
        'netbox_outcome_exposed': netbox_reg['outcome_exposed_historical_case'],
        'netbox_qualified_case_variants': sum(r['qualified_cases'] for r in netbox['versions'].values()),
        'netbox_targeted_historical_faults': netbox['historical_faults'],
        'vibe_outcome_exposed': vibe['outcome_exposed_exploratory_pilot'],
        'cash_invoice_verified': False,
        'publication_contribution_gate_passed': False,
        'independent_study_additional_reruns_justified': False,
        'source_sha256': {p: sha((ROOT / p).read_bytes()) for p in SOURCES},
        'history_evidence_sha256': {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted(BASE.rglob('*')) if p.is_file()},
    }


def main():
    p = argparse.ArgumentParser(); p.add_argument('--verify', action='store_true'); args = p.parse_args()
    value = build(); out = ROOT / 'manifests/independent-input-goal-audit-v1.json'
    if args.verify:
        assert json.loads(out.read_text()) == value
    else:
        assert not out.exists(); out.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: v for k, v in value.items() if k not in ['source_sha256', 'history_evidence_sha256', 'all_workflow_exposure_disclosures', 'excluded_workflows']}, indent=2))


if __name__ == '__main__':
    main()
