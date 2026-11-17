#!/usr/bin/env python3
"""Check capability-matrix coverage and archived source bytes, not runtime behavior."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    summary_path = ROOT / 'manifests/agentcompany-instruction-screen-summary-v1.json'
    summary = json.loads(summary_path.read_text())
    screen = json.loads((ROOT / 'manifests/agentcompany-instruction-screen-v1.json').read_text())
    matrix = json.loads((ROOT / 'manifests/agentcompany-capability-matrix-v1.json').read_text())
    assert matrix['instruction_screen_summary_sha256'] == sha(summary_path)
    assert [r['task'] for r in matrix['tasks']] == summary['explicit_without_reply_tasks']
    assert len({r['task'] for r in matrix['tasks']}) == len(matrix['tasks']) == 15
    original = {r['task']: r for r in screen['tasks']}
    assert set(matrix['families']) == {r['family'] for r in matrix['tasks']}
    for row in matrix['tasks']:
        source = original[row['task']]
        assert row['instruction_sha256'] == source['source_sha256']
        assert row['family'] == source['candidate_chain']['family']
        assert row['full_instruction_service_mentions'] == source['literal_service_mentions']
        assert row['required_assets_and_semantics']
        assert row['runtime_status'] == 'not_qualified'
    checked_files = set()
    for group in ('agentcompany-service-capability-v1', 'agentcompany-interface-source-v1'):
        base = ROOT / 'results' / group
        collection = json.loads((base / 'collection.json').read_text())
        for row in collection['files']:
            assert row.get('status', 200) == 200
            path = base / 'source' / row.get('local', row['path'])
            assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
            checked_files.add(str(path.relative_to(ROOT)))
    for family in matrix['families'].values():
        assert family['api'] and family['native'] and family['unresolved']
        for item in family['evidence']:
            path = ROOT / item['source']
            assert sha(path) == item['sha256']
            assert item['literal_anchor'] in path.read_text()
    assert not matrix['packaged_source_equivalence_verified']
    assert matrix['runtime_qualified_count'] == matrix['scientific_executions'] == 0
    print(json.dumps({'tasks': len(matrix['tasks']), 'families': len(matrix['families']),
                      'new_archived_source_files_verified': len(checked_files),
                      'runtime_qualified': 0,
                      'scope': 'Coverage, byte hashes and literal source anchors only; semantic interpretation and runtime equivalence are not certified.'}, indent=2))


if __name__ == '__main__':
    main()
