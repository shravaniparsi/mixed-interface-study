#!/usr/bin/env python3
"""Verified immutable archive -> separate retrospective comparison report."""
import argparse, json
from realworld_terminal_campaign import ROOT, read, sha
from verify_realworld_fresh_legacy_archive import verify, MANIFEST
from realworld_reference_comparison_v1 import compare

OUTPUT = ROOT/'manifests/realworld-reference-replay-v1.json'


def inputs(directory):
    root = next((directory/'run').glob('*/summary.json')).parent
    summary = read(root/'summary.json'); job = read(directory/'job.json')
    spec = next(c for c in read(root/'registered-candidates.json')['cases'] if c['candidate_id'] == job['candidate_id'])
    branches = {b['continuation']: (read(root/b['evidence']), b) for b in summary['branches']}
    return (job, branches, spec, read(root/'fixture-references.json'), summary['fixture_sha256'], True,
            {b['evidence']: sha(root/b['evidence']) for b in summary['branches']})


def replay():
    verify()
    root = ROOT/read(MANIFEST)['archive_root']/'realworld-legacy-v9'
    results = {}
    for directory in sorted(root.glob('legacy-*')):
        job = read(directory/'job.json')
        if job['entry_kind'] == 'singleton':
            results[job['job_id']] = {'entry_kind': 'singleton', 'unchanged': True, 'paired_comparison_eligible': False}
        else:
            results[job['job_id']] = compare(*inputs(directory))
    return {'kind': 'retrospective_generated_reference_comparison_v1',
            'archive_manifest_sha256': sha(MANIFEST),
            'source_sha256': {p: sha(ROOT/p) for p in ('scripts/realworld_reference_comparison_v1.py', 'scripts/replay_realworld_references_v1.py')},
            'jobs': results, 'original_archive_modified': False, 'new_primary_samples': 0,
            'primary_freeze_complete': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--verify', action='store_true'); args = parser.parse_args()
    value = replay()
    if args.verify:
        if read(OUTPUT) != value: raise ValueError('Reference replay differs')
        print('Verified separate reference replay; frozen classifications preserved')
    else:
        OUTPUT.write_text(json.dumps(value, indent=2)+'\n')
        print(json.dumps({j: v.get('derived_kind', 'singleton') for j, v in value['jobs'].items()}, indent=2))
