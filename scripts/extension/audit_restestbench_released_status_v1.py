#!/usr/bin/env python3
"""Reconstruct exact-status audit from hash-verified released result files."""
import argparse
import collections
import csv
import hashlib
import gzip
import io
import json
from pathlib import Path
import tarfile
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/restestbench-released-status-v1'


def build():
    pins = json.loads((BASE / 'source-pins.json').read_text())
    trees = json.loads(gzip.decompress((BASE / 'source-trees.json.gz').read_bytes()))
    selected = {}
    for group, tree in trees.items():
        assert not tree['truncated']
        for row in tree['tree']:
            if row['path'].endswith(('execution_results.json', 'evaluation_results.json')) or row['path'] == 'benchmark_results.csv':
                selected['results/runs/' + group + '/' + row['path']] = row['sha']
    assert selected == pins['files']
    files = {}
    with tarfile.open(BASE / 'selected-results.tar.gz') as archive:
        for member in archive:
            assert member.isfile() and member.name not in files
            raw = archive.extractfile(member).read()
            blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            assert blob == pins['files'][member.name]
            files[member.name] = raw
    assert set(files) == set(pins['files']) and len(files) == 723
    executions = {p: json.loads(b) for p, b in files.items() if p.endswith('/execution_results.json')}
    evaluations = {p: json.loads(b) for p, b in files.items() if p.endswith('/evaluation_results.json')}
    assert len(executions) == len(evaluations) == 360
    assert {p.replace('execution_results.json', 'evaluation_results.json') for p in executions} == set(evaluations)
    csvs = {p: list(csv.DictReader(io.StringIO(b.decode()))) for p, b in files.items() if p.endswith('.csv')}
    matches = []
    counts = collections.Counter()
    requirement_sets = collections.defaultdict(set)
    for path, data in sorted(executions.items()):
        records = data['results']
        counts['execution_records'] += len(records)
        for record in records:
            counts['valid_context_records' if record['execution_context'] == 'valid' else 'mutated_context_records'] += 1
        evaluation = evaluations[path.replace('execution_results.json', 'evaluation_results.json')]
        service = path.split('/')[-2]
        requirement_sets[service].add(tuple(sorted(r['requirement_id'] for r in evaluation['requirements'])))
        for index, record in enumerate(records):
            if record.get('output') != 'Mutation could not be applied': continue
            assert not record['passed'] and record['return_code'] == -1 and record['duration_ms'] == 0
            assert record['generation_mode'] == 'valid'
            valid = [r for r in records if r['requirement_id'] == record['requirement_id'] and r['test_file'] == record['test_file'] and r['generation_mode'] == record['generation_mode'] and r['execution_context'] == 'valid']
            assert len(valid) == 1 and valid[0]['passed']
            score = next(r for r in evaluation['requirements'] if r['requirement_id'] == record['requirement_id'])['valid_test']
            credited = record['mutant_index_executed'] in score['mutants_killed']
            assert score['passes_on_valid'] and credited
            parts = path.split('/')
            csv_path = '/'.join(parts[:3]) + '/benchmark_results.csv'
            folder = '/'.join(parts[3:-1])
            csv_rows = [r for r in csvs[csv_path] if r['output_folder'].replace('\\', '/') == folder and r['generation_context'] == 'valid']
            assert len(csv_rows) <= 1
            if csv_rows:
                assert float(csv_rows[0]['score']) == evaluation['summary']['valid_score']
                assert int(csv_rows[0]['killed_mutations (TP)']) == evaluation['summary']['valid_score']
            matches.append({'execution_file': path, 'record_index': index, 'requirement_id': record['requirement_id'], 'mutant_index': record['mutant_index_executed'], 'credited_in_evaluation': credited, 'present_in_consolidated_csv': bool(csv_rows), 'csv_model': csv_rows[0]['model'] if csv_rows else None, 'csv_precise_description': csv_rows[0]['precise_description'] if csv_rows else None, 'original_file_score': evaluation['summary']['valid_score'], 'original_file_max_score': evaluation['summary']['valid_max_score']})
    assert len(matches) == 6
    return {'kind': 'restestbench_released_status_audit_v1', 'commit': pins['commit'], 'execution_files': len(executions), 'evaluation_files': len(evaluations), 'consolidated_csv_files': len(csvs), 'counts': dict(counts), 'exact_status_matches': len(matches), 'credited_in_evaluation': sum(r['credited_in_evaluation'] for r in matches), 'matches_in_consolidated_csv': sum(r['present_in_consolidated_csv'] for r in matches), 'matches': matches, 'released_requirement_id_sets': {k: [list(x) for x in sorted(v)] for k, v in sorted(requirement_sets.items())}, 'paper_ranking_effect_established': False, 'new_application_executions': 0, 'paid_model_calls': 0, 'archive_sha256': hashlib.sha256((BASE / 'selected-results.tar.gz').read_bytes()).hexdigest(), 'trees_sha256': hashlib.sha256((BASE / 'source-trees.json.gz').read_bytes()).hexdigest(), 'pins_sha256': hashlib.sha256((BASE / 'source-pins.json').read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--verify', action='store_true'); args = parser.parse_args()
    value = build(); path = ROOT / 'manifests/restestbench-released-status-v1.json'
    if args.verify: assert json.loads(path.read_text()) == value
    else:
        assert not path.exists(); path.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: v for k, v in value.items() if k not in ('matches', 'released_requirement_id_sets')}))
    for row in value['matches']: print(json.dumps(row))


if __name__ == '__main__': main()
