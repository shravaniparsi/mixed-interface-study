#!/usr/bin/env python3
"""Inventory public instructions only; lexical signals are not task eligibility."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/agentcompany-feasibility-v1'


def build():
    collection = json.loads((BASE / 'collection.json').read_text())
    tree = json.loads((BASE / 'task-tree.json').read_text())
    expected = {e['path']: e['sha'] for e in tree
                if e['path'].startswith('workspaces/tasks/') and e['path'].endswith('/task.md')}
    tasks = {}
    hashes = {}
    for row in collection['files']:
        path = BASE / 'source' / row['path']
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        assert len(raw) == row['bytes'] and digest == row['sha256']
        assert blob == row['git_blob_sha1']
        hashes[row['path']] = digest
        if row['path'] in expected:
            assert blob == expected[row['path']]
            tasks[Path(row['path']).parent.name] = raw.decode('utf-8')
    assert len(tasks) == len(expected) == 175
    catalog = (BASE / 'source/workspaces/README.md').read_text()
    listed = re.findall(r'^- ghcr\.io/theagentcompany/(.+)-image:1\.0\.0\s*$', catalog, re.M)
    assert len(listed) == len(set(listed)), 'Duplicate catalog entries'
    # Recognize only literal service names/host:port references. No action,
    # oracle type, API capability, dependency edge or NPC need is inferred.
    patterns = {
        'gitlab': r'\bgitlab\b|the-agent-company\.com:8929\b',
        'plane': r'\bplane\b|the-agent-company\.com:8091\b',
        'owncloud': r'\bowncloud\b|the-agent-company\.com:8092\b',
        'rocketchat': r'\brocket\s*chat\b|the-agent-company\.com:3000\b',
    }
    rows = []
    for name, instruction in sorted(tasks.items()):
        services = [s for s, pattern in patterns.items() if re.search(pattern, instruction, re.I)]
        rows.append({'task': name, 'listed_image_v1': name in listed,
                     'literal_service_mentions': services,
                     'eligibility': 'not_assessed'})
    screen = json.loads((ROOT / 'manifests/agentcompany-plane-instruction-screen-v1.json').read_text())
    assert screen['revision'] == collection['revision']
    screened = [r['task'] for r in screen['tasks']]
    assert len(screened) == len(set(screened))
    assert set(screened) == {r['task'] for r in rows if 'plane' in r['literal_service_mentions']}
    capability_base = ROOT / 'results/agentcompany-plane-capability-v1'
    capability = json.loads((capability_base / 'collection.json').read_text())
    for item in capability['files']:
        raw = (capability_base / item['local']).read_bytes()
        assert len(raw) == item['bytes']
        assert hashlib.sha256(raw).hexdigest() == item['sha256']
    return {
        'kind': 'agentcompany_instruction_inventory_v1',
        'revision': collection['revision'],
        'instruction_files': len(tasks), 'listed_images': len(listed),
        'instructions_without_listed_image': sorted(set(tasks) - set(listed)),
        'listed_images_without_instruction': sorted(set(listed) - set(tasks)),
        'literal_service_mentions': dict(sorted(Counter(s for r in rows for s in r['literal_service_mentions']).items())),
        'service_mention_set_counts': dict(sorted(Counter('+'.join(r['literal_service_mentions']) or 'none' for r in rows).items())),
        'rules': patterns, 'tasks': rows, 'source_sha256': hashes,
        'applications_executed': 0, 'graders_inspected': False,
        'interpretation': 'Lexical inventory of public task instructions, not a count of eligible workflows, independent defects, required services, deterministic graders, or API/native equivalent operations. Full instruction catalog is now exposed to this study; no outcomes were used.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    result = build()
    path = ROOT / 'manifests/agentcompany-instruction-inventory-v1.json'
    if args.verify:
        assert json.loads(path.read_text()) == result
    else:
        path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('tasks', 'source_sha256')}, indent=2))
