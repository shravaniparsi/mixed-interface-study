#!/usr/bin/env python3
"""Verify screen coverage/provenance and summarize analyst labels, not their accuracy."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODES = {'explicit_chain', 'conditional_chain', 'ambiguous_chain',
         'write_without_produced_state_consumer', 'no_web_state_write'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    path = ROOT / 'manifests/agentcompany-instruction-screen-v1.json'
    screen = json.loads(path.read_text())
    inventory = json.loads((ROOT / 'manifests/agentcompany-instruction-inventory-v1.json').read_text())
    protocol = ROOT / 'protocol/agentcompany-instruction-eligibility-v1.md'
    assert sha(protocol) == screen['protocol_sha256']
    assert screen['source_revision'] == inventory['revision']
    expected = sorted(r['task'] for r in inventory['tasks'])
    rows = screen['tasks']
    assert [r['task'] for r in rows] == expected and len(rows) == 175
    for i, row in enumerate(rows):
        assert row['index'] == i
        assert row['code'] in CODES
        assert row['coworker_response'] in ('yes', 'no', 'optional')
        assert row['reason'] and row['runtime_eligibility'] == 'not_assessed'
        source = ROOT / 'results/agentcompany-feasibility-v1/source/workspaces/tasks' / row['task'] / 'task.md'
        assert sha(source) == row['source_sha256']
        chain = row['candidate_chain']
        if row['code'] in ('explicit_chain', 'conditional_chain'):
            assert chain and all(chain[k] for k in ('family', 'applications', 'producer', 'consumer', 'dependency', 'uncertainty'))
        elif row['code'] == 'ambiguous_chain':
            assert chain and chain['uncertainty']
        else:
            assert chain is None
    explicit = [r for r in rows if r['code'] == 'explicit_chain']
    no_reply = [r for r in explicit if r['coworker_response'] == 'no']
    return {
        'kind': 'agentcompany_instruction_screen_summary_v1',
        'rule_freeze_commit': screen['rule_freeze_commit'],
        'screen_sha256': sha(path), 'protocol_sha256': sha(protocol),
        'task_count': len(rows),
        'code_counts': dict(sorted(Counter(r['code'] for r in rows).items())),
        'explicit_family_counts': dict(sorted(Counter(r['candidate_chain']['family'] for r in explicit).items())),
        'explicit_tasks_without_requested_coworker_reply': len(no_reply),
        'explicit_without_reply_family_counts': dict(sorted(Counter(r['candidate_chain']['family'] for r in no_reply).items())),
        'explicit_without_reply_tasks': [r['task'] for r in no_reply],
        'conditional_family_counts': dict(sorted(Counter(r['candidate_chain']['family'] for r in rows if r['code'] == 'conditional_chain').items())),
        'scientific_executions': 0, 'runtime_qualified_workflows': 0,
        'interpretation': 'Complete single-pass instruction coding. Family counts are descriptive groupings, not independent samples; no native/API equivalence, causal dependency, classifier accuracy, selector advantage or publication sufficiency has been established.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    result = build()
    path = ROOT / 'manifests/agentcompany-instruction-screen-summary-v1.json'
    if args.verify:
        assert json.loads(path.read_text()) == result
    else:
        path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
