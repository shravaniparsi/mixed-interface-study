#!/usr/bin/env python3
"""Post hoc trace audit; never changes frozen scientific classifications."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def build():
    source_dir = ROOT / 'results/gitlab-readback-source-v1'
    source = json.loads((source_dir / 'source.json').read_text())
    hashes = {}
    for item in source['sources']:
        p = source_dir / item['path']
        raw = p.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item['sha256']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == item['git_blob_sha']
        hashes[str(p.relative_to(ROOT))] = item['sha256']
    archive = ROOT / 'results/benchmark-gitlab-readme-inputs-v1-ci-44033922143'
    rows = []
    for p in sorted(archive.glob('gitlab-readme-inputs-r*-44033922143/*/readme-case.json')):
        raw = p.read_bytes()
        r = json.loads(raw)
        hashes[str(p.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
        if r.get('final_branches') != []:
            continue
        expected = [{'name': 'main', 'default': True}]
        failure = r.get('failure_repository', {})
        pid = r['project_id']
        endpoint = f'/api/v4/projects/{pid}/repository/branches?per_page=100'
        rows.append({
            'source': str(p.relative_to(ROOT)), 'case_id': r['case_id'],
            'role': r['case_role'], 'branch': r['branch'],
            'producer_branches': r.get('producer_repository', {}).get('branches'),
            'immediate_final_branches': r['final_branches'],
            'later_failure_branches': failure.get('branches'),
            'later_main_observed': failure.get('branches') == expected,
            'identical_branch_list_get_statuses': [q['status'] for q in r['api_requests']
                                                 if q['method'] == 'GET' and q['path'] == endpoint],
            'case_passed': r['case_passed'],
        })
    return {
        'kind': 'readme_readback_posthoc_diagnostic_v1',
        'scope': 'Archived sequential observations and official pinned source only; no new application execution or reclassification.',
        'immediate_empty_later_main_records': sum(r['later_main_observed'] for r in rows),
        'rows': rows,
        'source_revision': source['revision'],
        'source_observation': 'Branch-list endpoint wraps response generation in cache_action with expires_in 30.seconds; helper cache.fetch stores serialized response and pagination headers.',
        'causal_status': 'Plausible cache mechanism, not demonstrated cache hits. No request timestamps, runtime cache keys or cache-hit tracing were captured. These source files were not extracted from the packaged image.',
        'scientific_classifications_changed': False,
        'source_sha256': hashes,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    value = build()
    target = ROOT / 'manifests/readme-readback-diagnostic-v1.json'
    if args.verify:
        assert json.loads(target.read_text()) == value
    else:
        target.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: v for k, v in value.items() if k not in ('rows', 'source_sha256')}, indent=2))
