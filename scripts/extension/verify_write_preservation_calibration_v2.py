#!/usr/bin/env python3
"""Independently reconstruct the historical calibration from immutable raw rows."""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from jsonschema.validators import validator_for

ROOT = Path(__file__).resolve().parents[2]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify_cost():
    saved = json.loads((ROOT / 'manifests/write-preservation-calibration-cost-v1.json').read_text())
    for path, expected in saved['raw_sha256'].items():
        assert sha(ROOT / path) == expected
    rows = []
    for path in sorted((ROOT / 'results/write-preservation-accounting-v1').glob('*-jobs.json')):
        value = json.loads(path.read_text())
        assert value['total_count'] == len(value['jobs']) == 2
        for job in value['jobs']:
            parse = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00'))
            rows.append({'run_id': int(path.name.split('-')[0]), 'job_id': job['id'],
                         'name': job['name'], 'conclusion': job['conclusion'],
                         'job_elapsed_seconds': (parse(job['completed_at']) - parse(job['started_at'])).total_seconds()})
    assert rows == saved['jobs']
    assert saved['runs'] == 2 and saved['paid_model_calls'] == 0
    assert saved['job_elapsed_minutes'] == sum(r['job_elapsed_seconds'] for r in rows) / 60

def build(archive):
    registry_path = ROOT / 'manifests/write-preservation-calibration-v2.json'
    registry = json.loads(registry_path.read_text())
    assert sha(ROOT / 'manifests/write-preservation-calibration-v1.json') == registry['previous_registry_sha256']
    for path, expected in {**registry['source_sha256'], **registry['failed_attempt_sha256']}.items():
        assert sha(ROOT / path) == expected, path
    reports = list(archive.rglob('report.json'))
    assert len(reports) == 2
    reconstructed = []
    versions = {}
    raw_hashes = {}
    run_ids = set()
    for path in reports:
        report = json.loads(path.read_text())
        version = report['version']
        assert version not in versions
        assert report['registry_sha256'] == sha(registry_path)
        assert report['upstream_commit'] == registry['versions'][version]
        assert report['status'] == 'observed', report.get('error')
        run_ids.add(report['run_id'])
        for name, expected in report['files_sha256'].items():
            assert sha(path.parent / name) == expected, name
        records = json.loads((path.parent / 'observations.json').read_text())
        indexed = {(r['case'], r['channel']): r for r in records}
        assert len(indexed) == len(records) == 6
        assert set(indexed) == {(c, h) for c in registry['cases'] for h in registry['channels']}
        scores = []
        for record in records:
            case, channel = record['case'], record['channel']
            expected_note = '' if case == 'explicit_empty' else 'study edited note'
            expected_input = {'ids': ['study-transaction'], 'updates': {'note': expected_note}}
            assert record['input'] == expected_input
            before, after = record['before'], record['after']
            assert before.keys() == after.keys()
            assert before['transaction_id'] == after['transaction_id'] == 'study-transaction'
            assert (before['original_order'] is None) == (case == 'unordered')
            assert before['note'] != expected_note
            schema = indexed[(case, 'mcp')]['schema']
            validator = validator_for(schema)
            validator.check_schema(schema)
            errors = [e.message for e in validator(schema).iter_errors(expected_input)]
            changes = sorted(k for k in before if type(before[k]) != type(after[k]) or before[k] != after[k])
            score = {'case': case, 'channel': channel, 'schema_valid': not errors,
                     'schema_errors': errors, 'operation_success': record['operation_success'],
                     'requested_edit_persisted': after['note'] == expected_note,
                     'changed_columns': changes,
                     'frame_violations': [k for k in changes if k != 'note']}
            if channel == 'mcp':
                assert record['operation_success'] == (not record['response'].get('isError', False))
            else:
                assert record['operation_success'] == record['response']['ok']
            scores.append(score)
            reconstructed.append(dict(version=version, **score))
        assert scores == report['scores'], 'Saved scoring differs from independent reconstruction'
        for case in registry['cases']:
            direct, mcp = indexed[(case, 'direct')], indexed[(case, 'mcp')]
            assert direct['before'] == mcp['before'], 'Incomparable branch fixture'
            assert direct['input'] == mcp['input']
        versions[version] = {'rustc': report['rustc'], 'cargo': report['cargo'],
                             'cargo_lock_sha256': report['cargo_lock_sha256'],
                             'study_commit': report['study_commit'], 'records': indexed}
        for file in path.parent.iterdir():
            if file.is_file():
                raw_hashes[str(file.relative_to(ROOT))] = sha(file)
    assert set(versions) == {'historical', 'fixed'}
    assert len(run_ids) == 1
    for key in ('rustc', 'cargo', 'cargo_lock_sha256', 'study_commit'):
        assert versions['historical'][key] == versions['fixed'][key], 'Cross-version environment mismatch: ' + key
    for key, historical in versions['historical']['records'].items():
        assert historical['before'] == versions['fixed']['records'][key]['before']
    complete = all(r['schema_valid'] and r['operation_success'] and r['requested_edit_persisted'] for r in reconstructed)
    matches = all(versions[v]['records'][(c, 'direct')]['after'] == versions[v]['records'][(c, 'mcp')]['after']
                  for v in versions for c in registry['cases'])
    expected_pattern = all(r['frame_violations'] == (
        ['original_order'] if r['version'] == 'historical' and r['case'] != 'unordered' else []) for r in reconstructed)
    return {'kind': 'historical_write_preservation_reconstruction_v2',
            'run_id': next(iter(run_ids)), 'status': 'reconstructed',
            'calibration_gate_passed': complete and matches and expected_pattern,
            'executions': len(reconstructed), 'known_mechanisms': 1,
            'new_defects_claimed': 0, 'mcp_direct_state_matches': matches,
            'published_regression_pattern_reproduced': expected_pattern,
            'schema_success_postcondition_all_pass': complete,
            'frame_alerts': sum(bool(r['frame_violations']) for r in reconstructed),
            'scores': sorted(reconstructed, key=lambda r: (r['version'], r['case'], r['channel'])),
            'raw_sha256': raw_hashes,
            'limits': ['Known outcome-selected defect; not held-out efficacy or prevalence.',
                       'Real MCP dispatch over in-memory transport and real SQLite; no external Sheets or model behavior.',
                       'Full-row frame check is a competent baseline, not a novel intervention.']}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    result = build(args.archive.resolve())
    verify_cost()
    if args.verify:
        assert result == json.loads(args.verify.read_text()), 'Saved reconstruction drift'
    if args.output:
        assert not args.output.exists(), 'Refuse to overwrite a proof'
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('scores', 'raw_sha256', 'limits')}, indent=2))

if __name__ == '__main__':
    main()
