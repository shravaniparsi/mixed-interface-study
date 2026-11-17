#!/usr/bin/env python3
"""Verify allowlisted task assets and declared dependencies, never execute them."""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    base = ROOT / 'results/agentcompany-task-asset-inventory-v1'
    tree = json.loads((base / 'tree.json').read_text())
    collection = json.loads((base / 'collection.json').read_text())
    summary = json.loads((ROOT / 'manifests/agentcompany-instruction-screen-summary-v1.json').read_text())
    assert tree['revision'] == collection['revision'] == '98b68ef82a47690c316f42fddb05baafaab56851'
    assert tree['source_tree_truncated'] is False
    metadata = {r['path']: r for r in tree['files']}
    allowed = {'dependencies.yml', 'Dockerfile', 'template.md', 'requirement.txt', 'instructions.md', 'populate_data.py', 'post_init.sh'}
    assert set(collection['allowed_basenames']) == allowed
    expected = {p for p in metadata if Path(p).name in allowed}
    assert {r['path'] for r in collection['files']} == expected
    assert len(expected) == len(collection['files'])
    for row in collection['files']:
        raw = (base / 'source' / row['path']).read_bytes()
        assert len(raw) == row['bytes'] == metadata[row['path']]['size']
        assert hashlib.sha256(raw).hexdigest() == row['sha256']
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        assert blob == row['git_blob_sha1'] == metadata[row['path']]['sha']
    tasks = summary['explicit_without_reply_tasks']
    assert {Path(p).parts[2] for p in metadata} == set(tasks)
    counts = Counter()
    for task in tasks:
        path = base / 'source/workspaces/tasks' / task / 'dependencies.yml'
        lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
        assert all(line.startswith('- ') for line in lines)
        services = [line[2:] for line in lines]
        assert set(services) <= {'gitlab', 'owncloud', 'rocketchat', 'plane'}
        assert len(services) == len(set(services))
        counts.update(services)
    print(json.dumps({'tasks': len(tasks), 'allowlisted_files_verified': len(expected),
                      'declared_service_task_counts': dict(sorted(counts.items())),
                      'runtime_assets_qualified': False,
                      'scope': 'Repository metadata and setup assets only; images, cloud documents and task completion remain unverified.'}, indent=2))


if __name__ == '__main__':
    main()
