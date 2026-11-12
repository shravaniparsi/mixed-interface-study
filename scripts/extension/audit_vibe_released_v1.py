#!/usr/bin/env python3
"""Reconstruct an independent API benchmark's released scoring without executions."""
import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import itertools
import json
from pathlib import Path
import zipfile
ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / 'results/evaluation-feasibility-screen-v1/vibe-testing-replication-package.zip'
DIGEST = 'd3ba05db5587ce8fcec62cbcb0096d30e10534088ee3012c3f712be84e5a18ec'
PREFIX = 'vibe-testing-replication-package/'


def build():
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == DIGEST
    with zipfile.ZipFile(ARCHIVE) as archive:
        assert len(archive.namelist()) == len(set(archive.namelist()))
        files = {n[len(PREFIX):]: archive.read(n) for n in archive.namelist() if not n.endswith('/')}
    manifest = {}
    for line in files['MANIFEST.sha256'].decode().splitlines():
        digest, name = line.split('  ', 1)
        assert name not in manifest
        manifest[name] = digest
        assert hashlib.sha256(files[name]).hexdigest() == digest, name
    unlisted = sorted(set(files) - set(manifest) - {'MANIFEST.sha256'})
    worker_path = '07_mutation_testing/scripts/_mutation_worker.py'
    module = ast.parse(files[worker_path].decode())
    models = None
    for node in module.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'MODEL_DIRS' for t in node.targets):
            models = ast.literal_eval(node.value)
    assert models and len(models) == 5
    expected = set(itertools.product(models, [f'L{i}' for i in range(5)], range(1, 6)))
    paths = sorted(n for n in files if n.startswith('07_mutation_testing/per_suite_results/') and n.endswith('.json'))
    assert len(paths) == 125
    seen = set(); rows = []; discrepancies = []; mutations = Counter(); baselines = Counter(); cells = defaultdict(Counter)
    evidence_fields = Counter()
    for path in paths:
        data = json.loads(files[path]); key = (data['model'], data['level'], data['run'])
        assert key in expected and key not in seen; seen.add(key)
        baseline = data.get('baseline')
        if baseline is None:
            baseline_kind = 'unavailable'
        elif data.get('status') == 'degenerate_baseline':
            baseline_kind = 'degenerate'
        elif baseline['failed'] == baseline['errored'] == 0 and baseline['passed'] > 0:
            baseline_kind = 'fully_passing'
        else:
            baseline_kind = 'partially_failing'
        baselines[baseline_kind] += 1
        cell = cells[(key[0], key[1])]; cell['suites'] += 1; cell['baseline_' + baseline_kind] += 1
        records = data.get('mutations', []); names = [r['name'] for r in records]; assert len(names) == len(set(names))
        for r in records:
            if not r.get('applied'):
                kind = 'not_applied'
            elif 'error' in r:
                kind = 'execution_error'
            elif 'killed' in r:
                kind = 'credited_kill' if r['killed'] else 'survived'
                derived = r['passed'] < baseline['passed'] or r['failed'] > baseline['failed'] or r['errored'] > baseline['errored']
                if derived != r['killed']:
                    discrepancies.append({'path': path, 'mutation': r['name'], 'kind': 'kill_rule_mismatch', 'recorded': r['killed'], 'reconstructed': derived})
                if r['killed']:
                    cell['kills_under_' + baseline_kind + '_baseline'] += 1
            else:
                kind = 'missing_outcome'
            mutations[kind] += 1; cell[kind] += 1
            for field in r:
                evidence_fields[field] += 1
        eligible = [r for r in records if r.get('applied') and 'killed' in r]
        if 'score' in data:
            killed = sum(r['killed'] for r in eligible)
            derived_score = {'killed': killed, 'applied': len(eligible), 'pct': round(100 * killed / len(eligible), 1) if eligible else 0.0}
            if data['score'] != derived_score:
                discrepancies.append({'path': path, 'kind': 'summary_mismatch', 'recorded': data['score'], 'reconstructed': derived_score})
        rows.append({'path': path, 'sha256': hashlib.sha256(files[path]).hexdigest(), 'baseline_kind': baseline_kind, 'data': data})
    assert seen == expected
    return {'kind': 'vibe_released_evaluation_audit_v1', 'dataset_doi': '10.17632/2xfm6z2p5v.1', 'archive_sha256': DIGEST, 'internal_manifest_files_verified': len(manifest), 'files_not_in_internal_manifest': unlisted, 'expected_suites': 125, 'observed_suites': len(rows), 'complete_factorial_inventory': seen == expected, 'baseline_counts': dict(baselines), 'mutation_record_counts': dict(mutations), 'discrepancies': discrepancies, 'mutation_record_field_counts': dict(evidence_fields), 'cells': [{'model': k[0], 'level': k[1], **dict(v)} for k, v in sorted(cells.items())], 'rows': rows, 'worker_source_sha256': hashlib.sha256(files[worker_path]).hexdigest(), 'actual_semantic_misclassifications_established': False, 'new_application_executions': 0, 'paid_model_calls': 0}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--verify', action='store_true'); args = parser.parse_args()
    value = build(); output = ROOT / 'manifests/vibe-released-evaluation-audit-v1.json'
    if args.verify:
        assert json.loads(output.read_text()) == value
    else:
        assert not output.exists(); output.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: v for k, v in value.items() if k not in ['rows', 'cells']}, indent=2))


if __name__ == '__main__':
    main()
