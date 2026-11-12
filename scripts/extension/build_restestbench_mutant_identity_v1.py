#!/usr/bin/env python3
"""Describe repeated installed programs without changing the registered trial unit."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]


def build():
    source = ROOT / 'manifests/restestbench-applicability-v1.json'
    inventory = json.loads(source.read_text())
    grouped = defaultdict(list)
    for row in inventory['observations']:
        key = (row['service'], row['target'], row['before_sha256'], row['after_sha256'])
        grouped[key].append({'requirement_id': row['requirement_id'], 'mutant_index': row['mutant_index']})
    groups = [{'service': key[0], 'target': key[1], 'before_sha256': key[2], 'after_sha256': key[3], 'trials': sorted(trials, key=lambda r: (r['requirement_id'], r['mutant_index']))} for key, trials in sorted(grouped.items())]
    services = {}
    for service in sorted({g['service'] for g in groups}):
        selected = [g for g in groups if g['service'] == service]
        services[service] = {'registered_mutant_trials': sum(len(g['trials']) for g in selected), 'distinct_installed_source_changes': len(selected), 'repeated_change_groups': sum(len(g['trials']) > 1 for g in selected)}
    return {'kind': 'restestbench_mutant_identity_v1', 'post_hoc': True, 'registered_mutant_trials': len(inventory['observations']), 'distinct_installed_source_changes': len(groups), 'services': services, 'groups': groups, 'source_manifest_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'grouping_establishes_semantic_independence': False, 'registered_trial_denominator_unchanged': True, 'new_application_executions': 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    result = build()
    path = ROOT / 'manifests/restestbench-mutant-identity-v1.json'
    if args.verify:
        assert json.loads(path.read_text()) == result
    else:
        assert not path.exists()
        path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'groups'}, indent=2))


if __name__ == '__main__':
    main()
