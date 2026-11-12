#!/usr/bin/env python3
"""Reproduce analyst-coded candidate families and outcome-independent representatives."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--verify', action='store_true'); args = parser.parse_args()
    source = ROOT / 'results/benchmark-frame-screen-v1/assets/dataset/webarena-verified.json'
    tasks = json.loads(source.read_text())
    rules = [('reddit.post_comment', [9]), ('gitlab.repository_readme', [87,88]), ('gitlab.issue_assignment', [327]), ('gitlab.merge_request_reviewer', [335]), ('gitlab.project_members', [332,2100]), ('gitlab.directory_file', [84])]
    families = []; exclusions = []
    for name, templates in rules:
        candidates = []
        for task in tasks:
            if task['intent_template_id'] not in templates:
                continue
            if task['intent_template_id'] == 332 and 'as members' not in task['intent'].lower():
                exclusions.append({'task_id': task['task_id'], 'reason': 'creation-only instance; no explicit member-addition continuation'})
                continue
            identity = task['task_id']
            candidates.append({'task_id': identity, 'template_id': task['intent_template_id'], 'sites': task['sites'], 'intent': task['intent'], 'selection_sha256': hashlib.sha256(('benchmark-continuation-v1:' + str(identity)).encode()).hexdigest()})
        candidates.sort(key=lambda x:x['task_id'])
        representative = min(candidates, key=lambda x:x['selection_sha256'])['task_id']
        families.append({'family': name, 'candidate_task_count': len(candidates), 'representative_task_id': representative, 'qualification_status': 'not_started', 'candidates': candidates})
    protocol = ROOT / 'protocol/benchmark-continuation-selection-v1.md'
    result = {'kind':'benchmark_continuation_selection_v1','frame_tasks':len(tasks),'candidate_families':families,'candidate_task_count':sum(x['candidate_task_count'] for x in families),'reviewed_creation_only_exclusions':exclusions,'scientific_execution_authorized':False,'no_replacements':True,'sampling':'analyst-coded benchmark-derived capability candidates; not random or outcome-selected','source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,protocol]}}
    p=ROOT/'manifests/benchmark-continuation-selection-v1.json'
    if args.verify:
        assert json.loads(p.read_text()) == result
    else:
        p.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'candidate_tasks':result['candidate_task_count'],'families':[{k:v for k,v in x.items() if k != 'candidates'} for x in families],'exclusions':exclusions},indent=2))

if __name__ == '__main__':
    main()
