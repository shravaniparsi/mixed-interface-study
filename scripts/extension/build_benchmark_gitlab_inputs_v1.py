#!/usr/bin/env python3
"""Reconstruct source-anchored input specifications; never inspect UI or evaluators."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / 'results/benchmark-gitlab-image-inspection-v1-ci-43166622248/gitlab-image-inspection-43166622248/extracted/doc/api'
SECTIONS = {
    'project_create': ('projects.md', 'Create project'),
    'issue_create': ('issues.md', 'New issue'),
    'issue_update': ('issues.md', 'Edit issue'),
    'mr_create': ('merge_requests.md', 'Create MR'),
    'mr_update': ('merge_requests.md', 'Update MR'),
    'member_create': ('members.md', 'Add a member to a group or project'),
    'file_create': ('repository_files.md', 'Create new file in repository'),
    'commit_create': ('commits.md', 'Create a commit with multiple files and actions'),
}

def build():
    contracts = {}
    for key, (filename, heading) in SECTIONS.items():
        path = DOCS / filename
        lines = path.read_text().splitlines()
        start = lines.index('## ' + heading)
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith('## ')), len(lines))
        section = lines[start:end]
        fields = []
        for offset, line in enumerate(section):
            if line.startswith('| `'):
                cells = [x.strip() for x in line.strip('|').split('|')]
                if len(cells) == 4:
                    fields.append({'name': re.search(r'`([^`]+)`', cells[0]).group(1), 'type': cells[1], 'required_text': cells[2], 'description': cells[3], 'source_line': start + offset + 1})
        assert fields, key
        contracts[key] = {'source': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'heading': heading, 'start_line': start + 1, 'fields': fields}
    selected = json.loads((ROOT / 'manifests/benchmark-continuation-selection-v1.json').read_text())
    rules = [
        ('gitlab.repository_readme', 'project_create', 'file_create', 'initialize_with_readme'),
        ('gitlab.issue_assignment', 'issue_create', 'issue_update', 'confidential'),
        ('gitlab.merge_request_reviewer', 'mr_create', 'mr_update', 'squash'),
        ('gitlab.project_members', 'project_create', 'member_create', 'initialize_with_readme'),
    ]
    families = []
    for family, producer, continuation, flag in rules:
        original = next(x for x in selected['candidate_families'] if x['family'] == family)
        known = {x['name']: x for x in contracts[producer]['fields']}
        assert known['description']['type'] == 'string'
        assert known[flag]['type'] == 'boolean'
        specs = [('ordinary', {}), ('description_empty', {'description': ''}), ('description_ascii', {'description': 'Continuation study'}), ('description_unicode', {'description': 'Café 東京'}), (flag + '_false', {flag: False}), (flag + '_true', {flag: True})]
        cases = []
        for label, patch in specs:
            lifecycle = family == 'gitlab.repository_readme' and patch.get('initialize_with_readme') is True
            cases.append({'id': family + '.' + label, 'optional_field_patch': patch, 'required_bindings_status': 'unresolved_until_fixture_freeze', 'stratum': 'lifecycle_control' if lifecycle else 'task_compatibility_pending', 'runtime_validity': 'unobserved', 'native_representability': 'unobserved'})
        families.append({'family': family, 'representative_task_id': original['representative_task_id'], 'producer_contract': producer, 'continuation_contract': continuation, 'specifications': cases})
    protocol = ROOT / 'protocol/benchmark-gitlab-input-inventory-v1.md'
    return {'kind': 'benchmark_gitlab_input_inventory_v1', 'application_version': '15.7.5', 'application_revision': '358d690d91c', 'scientific_execution_authorized': False, 'specification_count': sum(len(x['specifications']) for x in families), 'contracts': contracts, 'families': families, 'retained_unqualified_families': ['reddit.post_comment', 'gitlab.directory_file'], 'protocol_sha256': hashlib.sha256(protocol.read_bytes()).hexdigest(), 'selection_sha256': hashlib.sha256((ROOT / 'manifests/benchmark-continuation-selection-v1.json').read_bytes()).hexdigest()}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    result = build()
    path = ROOT / 'manifests/benchmark-gitlab-input-inventory-v1.json'
    if args.verify:
        if json.loads(path.read_text()) != result:
            raise ValueError('Source-derived input inventory changed')
    else:
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'specifications': result['specification_count'], 'families': len(result['families']), 'scientific_execution_authorized': False}))

if __name__ == '__main__':
    main()
