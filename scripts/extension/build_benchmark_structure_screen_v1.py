#!/usr/bin/env python3
"""Inventory benchmark identifiers only; do not inspect intents or evaluation labels."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def build():
    relative = 'results/benchmark-frame-screen-v1/assets/dataset/webarena-verified.json'
    p = ROOT / relative
    data = json.loads(p.read_text())
    groups = defaultdict(list)
    for row in data:
        groups['+'.join(sorted(row['sites']))].append(row)
    return {'kind': 'benchmark_structure_screen_v1', 'task_records': len(data), 'unique_task_ids': len({r['task_id'] for r in data}), 'unique_template_ids': len({r['intent_template_id'] for r in data}), 'groups': {name: {'tasks': len(rows), 'template_ids': len({r['intent_template_id'] for r in rows})} for name, rows in sorted(groups.items())}, 'inspected_fields': ['sites', 'task_id', 'intent_template_id'], 'task_intents_or_evaluators_inspected': False, 'scientific_selection_frozen': False, 'execution_authorized': False, 'source_sha256': {relative: hashlib.sha256(p.read_bytes()).hexdigest()}}

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--verify', action='store_true'); args = parser.parse_args()
    result = build(); path = ROOT / 'manifests/benchmark-structure-screen-v1.json'
    if args.verify:
        assert json.loads(path.read_text()) == result
    else:
        path.write_text(json.dumps(result, indent=2) + '\n')
    print('Benchmark metadata verified:', result['task_records'], 'tasks;', result['unique_template_ids'], 'template identifiers')

if __name__ == '__main__':
    main()
