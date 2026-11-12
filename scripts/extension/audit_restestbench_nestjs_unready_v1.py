#!/usr/bin/env python3
"""Inspect all released valid-generation executions of the newly unready mutant."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import tarfile
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/restestbench-released-status-v1'


def build():
    pins = json.loads((BASE / 'source-pins.json').read_text())
    files = {}
    with tarfile.open(BASE / 'selected-results.tar.gz') as archive:
        for member in archive:
            if not member.name.endswith(('/nestjs-realworld/execution_results.json', '/nestjs-realworld/evaluation_results.json')):
                continue
            raw = archive.extractfile(member).read()
            assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == pins['files'][member.name]
            files[member.name] = json.loads(raw)
    rows = []
    absent = []
    paths = sorted(p for p in files if p.endswith('/execution_results.json'))
    for path in paths:
        records = files[path]['results']
        selected = [(i, r) for i, r in enumerate(records) if r['requirement_id'] == 5 and r.get('mutant_index_executed') == 0 and r['generation_mode'] == 'valid' and r['execution_context'] == 'mutated_0']
        if not selected:
            absent.append(path)
        for index, record in selected:
            valid = [r for r in records if r['requirement_id'] == 5 and r['test_file'] == record['test_file'] and r['generation_mode'] == 'valid' and r['execution_context'] == 'valid']
            assert len(valid) == 1
            evaluation = files[path.replace('execution_results.json', 'evaluation_results.json')]
            scores = [r for r in evaluation['requirements'] if r['requirement_id'] == 5]
            assert len(scores) == 1
            score = scores[0]['valid_test']
            credited = 0 in score['mutants_killed']
            output = record['output']
            markers = [m for m in ['ConnectionResetError', 'ConnectionRefusedError', 'ConnectionError', 'ReadTimeout', 'ConnectTimeout', 'TSError', 'TS2741'] if m in output]
            rows.append({'execution_file': path, 'record_index': index, 'original_control_passed': valid[0]['passed'], 'credited_in_evaluation': credited, 'recorded_failure_markers': markers, 'record': record})
    log = ROOT / 'results/restestbench-mutant-runtime-v1-ci-43144135284/nestjs-realworld/req-5-mut-0-service-logs.log'
    assert "error TS2741: Property 'raw' is missing" in log.read_text()
    return {'kind': 'restestbench_nestjs_unready_released_audit_v1', 'post_hoc': True, 'execution_files_examined': len(paths), 'selected_records': len(rows), 'files_without_selected_record': absent, 'original_control_passed': sum(r['original_control_passed'] for r in rows), 'mutant_passed': sum(r['record']['passed'] for r in rows), 'credited': sum(r['credited_in_evaluation'] for r in rows), 'credited_with_connectivity_marker': sum(r['credited_in_evaluation'] and any('Connection' in m or 'Timeout' in m for m in r['recorded_failure_markers']) for r in rows), 'marker_counts': dict(Counter(m for r in rows for m in r['recorded_failure_markers'])), 'rows': rows, 'historical_compile_failure_established': False, 'additional_unsupported_credits_claimed': 0, 'current_compile_failure_log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(), 'released_archive_sha256': hashlib.sha256((BASE / 'selected-results.tar.gz').read_bytes()).hexdigest(), 'new_application_executions': 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    value = build()
    path = ROOT / 'manifests/restestbench-nestjs-unready-released-v1.json'
    if args.verify:
        assert json.loads(path.read_text()) == value
    else:
        assert not path.exists()
        path.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: v for k, v in value.items() if k != 'rows'}, indent=2))


if __name__ == '__main__':
    main()
