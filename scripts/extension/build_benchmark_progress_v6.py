#!/usr/bin/env python3
"""Close selected-cohort accounting without upgrading partial comparisons."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def build():
    hashes = {}

    def read(name):
        path = ROOT / 'manifests' / (name + '.json')
        raw = path.read_bytes()
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    prior = read('benchmark-progress-v5')
    selection = read('benchmark-continuation-selection-v1')
    issue = read('benchmark-gitlab-issue-results-v1')
    readme = read('benchmark-gitlab-readme-results-v1')
    compute = read('benchmark-archived-compute-v1')
    inventory = read('benchmark-gitlab-input-inventory-v1')
    assert issue['scheduled_execution_complete'] and not readme['scheduled_execution_complete']
    families = prior['families']
    for family in families:
        if family['family'] == 'gitlab.repository_readme':
            reached = {t['case_id'] for t in readme['triples'] if t['observed_branches']}
            assert reached == set(family['frozen_specifications'])
            family.update(status='closed_partial_execution_failed_first_starting_control',
                          executed_specifications=len(reached), unexecuted_specifications=0,
                          scheduled_execution_complete=False,
                          evidence='manifests/benchmark-gitlab-readme-results-v1.json')
    triples = issue['triples'] + readme['triples']
    counts = dict(Counter(t['classification'] for t in triples))
    reached_specs = {t['case_id'] for t in triples if t['observed_branches']}
    scientific_records = sum(len(t['observed_branches']) for t in triples)
    assert scientific_records == issue['scheduled_scientific_branches'] + readme['scientific_branch_records']
    run_ids = {r['run_id'] for r in compute['runs']}
    assert issue['run_id'] in run_ids and readme['run_id'] not in run_ids
    total_seconds = compute['job_seconds'] + readme['job_seconds']
    return {
        'kind': 'benchmark_continuation_progress_snapshot_v6',
        'snapshot_scope': 'All selected families closed; README stopped partly under registered controls. Closure is not full execution or Q1 readiness.',
        'selected_family_count': len(families) + len(prior['retained_unqualified_families']),
        'selected_task_instances': selection['candidate_task_count'],
        'frozen_specifications': inventory['specification_count'],
        'specifications_with_any_scientific_record': len(reached_specs),
        'specifications_with_no_scientific_record': inventory['specification_count'] - len(reached_specs),
        'fully_executed_scientific_workflows': 1,
        'partially_executed_scientific_workflows': 1,
        'applications_with_scientific_execution': 1,
        'families': families,
        'retained_family_eligibility': prior['retained_family_eligibility'],
        'scientific_accounting': {
            'scheduled_triples': len(triples),
            'triples_with_all_three_records': sum(len(t['observed_branches']) == 3 for t in triples),
            'scheduled_branch_entries': issue['scheduled_scientific_branches'] + readme['scheduled_scientific_branches'],
            'recorded_branch_entries': scientific_records,
            'unreached_branch_entries': issue['scheduled_scientific_branches'] + readme['scheduled_scientific_branches'] - scientific_records,
            'production_phase_entries': issue['production_phase_entries'] + readme['production_phase_entries'],
            'observed_controls': issue['controls_observed'] + readme['controls_observed'],
            'scheduled_controls': issue['scheduled_control_branches'] + readme['scheduled_control_branches'],
            'classification_counts': counts,
            'all_paths_preserve_unique_specifications': len({t['case_id'] for t in triples if t['classification'] == 'all_paths_preserve'}),
            'candidate_incremental_signals': sum(t['candidate_incremental_signal'] for t in triples),
            'confirmed_natural_defects': sum(t['confirmed_natural_defect'] for t in triples),
            'job_seconds': issue['job_seconds'] + readme['job_seconds'],
        },
        'compute_scope': {
            'scope': 'Explicit terminal benchmark archives only; excludes other studies, unit workflows, local work and unlisted runs. Not an invoice.',
            'run_count': len(run_ids) + 1,
            'job_count': compute['job_count'] + len(readme['repetitions']),
            'job_seconds': total_seconds,
            'job_minutes': total_seconds / 60,
            'billed_dollars': None,
        },
        'interpretation': 'Records, attempts, qualified triples, correlated specifications and independent defects are distinct. No population prevalence, equivalence or detector-superiority conclusion follows.',
        'q1_contribution_established': False,
        'source_sha256': hashes,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    value = build()
    target = ROOT / 'manifests/benchmark-progress-v6.json'
    if args.verify:
        assert json.loads(target.read_text()) == value
    else:
        target.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: value[k] for k in ('scientific_accounting', 'compute_scope', 'q1_contribution_established')}, indent=2))
