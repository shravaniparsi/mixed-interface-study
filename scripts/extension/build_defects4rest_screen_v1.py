#!/usr/bin/env python3
"""Complete frozen metadata census; documentation is not execution qualification."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/evaluation-feasibility-screen-v1'
PIN = '265db1165e54b01a0698af0fd28d345169a5449f'


def build():
    tree = json.loads((BASE / 'defects4rest-tree.json').read_text()); assert not tree['truncated']
    objects = {r['path']: r for r in tree['tree']}
    for filename in ['defects4rest-pins.json', 'defects4rest-guide-pins.json']:
        pins = json.loads((BASE / filename).read_text()); assert pins['commit'] == PIN
        for row in pins['files']:
            raw = (BASE / 'defects4rest' / row['path']).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == row['sha256']
            assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['git_blob'] == objects[row['path']]['sha']
    metadata = {}; metadata_count = 0
    for path in sorted((BASE / 'defects4rest/defects4rest/data/defect_data').glob('*.csv')):
        rows = list(csv.DictReader(path.open())); metadata_count += len(rows)
        for row in rows:
            key = (row['repo'].lower(), row['issue_no'])
            assert key not in metadata; metadata[key] = row
    cases = []
    for directory, entry in sorted(objects.items()):
        if entry['type'] != 'tree' or not directory.startswith('bug_replication/') or len(directory.split('/')) != 3:
            continue
        project = directory.split('/')[1]; issue = directory.rsplit('#', 1)[-1]
        row = metadata.get((project.lower(), issue))
        guide = directory + '/README.md'; guide_bytes = objects.get(guide, {}).get('size', 0)
        specs = [p for p in objects if p.startswith(directory + '/') and p.endswith(('.json', '.yaml', '.yml'))]
        cases.append({'project': project, 'issue': issue, 'directory': directory, 'guide_path': guide if guide in objects else None, 'guide_bytes': guide_bytes, 'spec_paths': specs, 'metadata_match': row is not None, 'title': row['title'] if row else None, 'issue_url': row['issue_url'] if row else None, 'buggy_sha': row.get('buggy_sha') if row else None, 'patch_sha': row.get('patch_sha') if row else None, 'runtime_qualified': False})
    return {'kind': 'defects4rest_feasibility_screen_v1', 'upstream_commit': PIN, 'readme_advertised_replicable_defects': 110, 'observed_case_directories': len(cases), 'metadata_rows_across_12_projects': metadata_count, 'case_counts_by_project': dict(Counter(r['project'] for r in cases)), 'cases_with_nonempty_guide': sum(r['guide_bytes'] > 0 for r in cases), 'cases_with_spec_file': sum(bool(r['spec_paths']) for r in cases), 'cases_with_metadata': sum(r['metadata_match'] for r in cases), 'cases_with_two_commit_ids': sum(bool(re.fullmatch('[0-9a-f]{40}', r.get('buggy_sha') or '') and re.fullmatch('[0-9a-f]{40}', r.get('patch_sha') or '')) for r in cases), 'cases': cases, 'runtime_qualified_cases': 0, 'new_application_executions': 0, 'source_tree_sha256': hashlib.sha256((BASE / 'defects4rest-tree.json').read_bytes()).hexdigest()}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--verify', action='store_true'); args = p.parse_args(); value = build()
    out = ROOT / 'manifests/defects4rest-feasibility-screen-v1.json'
    if args.verify:
        assert json.loads(out.read_text()) == value
    else:
        assert not out.exists(); out.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: v for k, v in value.items() if k != 'cases'}, indent=2))


if __name__ == '__main__':
    main()
