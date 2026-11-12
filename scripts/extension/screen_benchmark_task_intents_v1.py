#!/usr/bin/env python3
"""Permissive lexical inventory; never reads evaluator values or outcomes."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
CREATE = ['create', 'add', 'post', 'publish', 'register', 'submit', 'open']
CHANGE = ['edit', 'update', 'change', 'rename', 'modify', 'revise', 'set']

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--verify', action='store_true'); args = parser.parse_args()
    source = ROOT / 'results/benchmark-frame-screen-v1/assets/dataset/webarena-verified.json'
    records = []
    for task in sorted(json.loads(source.read_text()), key=lambda x: x['task_id']):
        words = set(re.findall(r'\b[a-z]+\b', task['intent_template'].lower()))
        records.append({'task_id': task['task_id'], 'sites': task['sites'], 'template_id': task['intent_template_id'], 'template': task['intent_template'], 'create_words': sorted(words.intersection(CREATE)), 'change_words': sorted(words.intersection(CHANGE))})
    result = {'kind': 'benchmark_task_intent_lexical_screen_v1', 'tasks': len(records), 'create_candidate_tasks': sum(bool(r['create_words']) for r in records), 'change_candidate_tasks': sum(bool(r['change_words']) for r in records), 'both_candidate_tasks': sum(bool(r['create_words']) and bool(r['change_words']) for r in records), 'unmatched_tasks': sum(not r['create_words'] and not r['change_words'] for r in records), 'qualified_continuation_pairs': None, 'scientific_execution_authorized': False, 'records': records, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    target = ROOT / 'manifests/benchmark-task-intent-screen-v1.json'
    if args.verify:
        assert json.loads(target.read_text()) == result
    else:
        target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'records'}, indent=2))

if __name__ == '__main__':
    main()
