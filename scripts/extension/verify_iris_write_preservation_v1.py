#!/usr/bin/env python3
"""Reconstruct Iris factorial effects from raw rows and outgoing HTTP payloads."""
import argparse
import hashlib
import json
from pathlib import Path
from jsonschema.validators import validator_for

ROOT = Path(__file__).resolve().parents[2]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def git_blob(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()

def normalized(row, refs):
    result = dict(row)
    for key in ('created_at', 'updated_at'):
        result.pop(key)
    for column, ref, label in [('id', 'set_id', 'SET'), ('collection_id', 'collection_id', 'COLLECTION'),
                               ('created_by', 'actor_id', 'ACTOR')]:
        if result[column] == refs[ref]:
            result[column] = label
    return result

def build(archive):
    registry_path = ROOT / 'manifests/iris-write-preservation-calibration-v1.json'
    registry = json.loads(registry_path.read_text())
    blobs = json.loads((ROOT / 'manifests/iris-component-git-blobs-v1.json').read_text())
    assert blobs['versions']['old']['commit'] == registry['historical_commit']
    assert blobs['versions']['fixed']['commit'] == registry['fixed_commit']
    for name, digest in registry['source_sha256'].items():
        assert sha(ROOT / name) == digest, name
    paths = list(archive.rglob('report.json'))
    assert len(paths) == 4
    environment_locks = list(archive.glob('iris-write-environment-*/requirements.txt'))
    assert len(environment_locks) == 1
    all_records, hashes, cells, locks, runs, commits = [], {}, {}, set(), set(), set()
    for path in paths:
        report = json.loads(path.read_text())
        cell = report['cell']
        assert cell not in cells
        assert report['status'] == 'observed', report.get('error')
        assert report['registry_sha256'] == sha(registry_path)
        runs.add(report['run_id']); commits.add(report['study_commit'])
        for name, expected in report['files_sha256'].items():
            assert sha(path.parent / name) == expected, name
        for component, names in registry['component_files'].items():
            version = registry['cells'][cell][component]
            for name in names:
                file = path.parent / 'component-source' / name
                assert git_blob(file) == blobs['versions'][version]['files'][name], (cell, name)
                assert sha(file) == report['component_sha256'][name]
        assert sha(path.parent / 'requirements.txt') == report['lock_sha256']
        assert sha(environment_locks[0]) == report['lock_sha256']
        freeze = next(c for c in report['commands'] if c['args'] == ['python', '-m', 'pip', 'freeze', '--all'])
        assert set((path.parent / freeze['log']).read_text().splitlines()) == set(environment_locks[0].read_text().splitlines())
        locks.add(report['lock_sha256'])
        records = [json.loads(p.read_text()) for p in sorted((path.parent / 'observations').glob('*.json'))]
        assert len(records) == 6
        indexed = {(r['case'], r['channel']): r for r in records}
        assert set(indexed) == {(c, h) for c in registry['cases'] for h in registry['channels']}
        scores = []
        for record in records:
            assert record['status'] == 'observed'
            case, channel, refs = record['case'], record['channel'], record['refs']
            before, after = record['before'], record['after']
            assert before.keys() == after.keys()
            assert before['id'] == after['id'] == refs['set_id']
            assert before['description'] == 'Original description'
            grouped, clear = case != 'ungrouped_edit', case == 'explicit_clear'
            assert before['collection_id'] == (refs['collection_id'] if grouped else None)
            assert record['members_before'] == ([refs['set_id']] if grouped else [])
            intent = {'set_id': refs['set_id'], **({'collection_id': None} if clear else {'description': 'Edited description'})}
            assert record['intent'] == intent
            if channel == 'mcp_dispatch':
                expected_input, schema = intent, record['tool_schema']
                contents = record['tool_result']
                assert len(contents) == 1
                try:
                    response = json.loads(contents[0]['text'])
                except json.JSONDecodeError:
                    response = {}
                success = isinstance(response, dict) and response.get('id') == refs['set_id']
            else:
                schema = record['api_schema']
                expected_input = {k: record['api_before'][k] for k in schema['properties'] if k in record['api_before']}
                expected_input.update({'collection_id': None} if clear else {'description': 'Edited description'})
                result = record['direct_result']
                success = result['status'] == 200 and result['body'].get('id') == refs['set_id']
            assert record['input'] == expected_input
            validator = validator_for(schema); validator.check_schema(schema)
            errors = [e.message for e in validator(schema).iter_errors(expected_input)]
            assert errors == record['schema_errors']
            changed = sorted(k for k in before if type(before[k]) != type(after[k]) or before[k] != after[k])
            allowed = {'collection_id', 'updated_at'} if clear else {'description', 'updated_at'}
            computed = {'schema_valid': not errors, 'operation_success': success,
                        'requested_postcondition': after['collection_id'] is None if clear else after['description'] == 'Edited description',
                        'changed_columns': changed, 'frame_violations': sorted(set(changed) - allowed),
                        'naive_membership_preservation_alert': before['collection_id'] != after['collection_id']}
            assert computed == record['scores']
            assert success == record['operation_success']
            puts = [x for x in record['effect_http'] if x['method'] == 'PUT']
            assert len(puts) == 1 and puts[0] == record['outgoing_put']
            assert puts[0]['path'] == '/api/sets/' + refs['set_id']
            assert record['api_after']['collection_id'] == after['collection_id']
            assert record['members_after'] == ([refs['set_id']] if after['collection_id'] == refs['collection_id'] else [])
            scores.append({'case': case, 'channel': channel, **computed})
            all_records.append({'cell': cell, 'case': case, 'channel': channel, **computed,
                                'put_has_collection_id': 'collection_id' in puts[0]['body'],
                                'membership_after': 'grouped' if after['collection_id'] is not None else 'ungrouped'})
        assert scores == report['scores']
        for case in registry['cases']:
            direct, mcp = indexed[(case, 'direct_complete')], indexed[(case, 'mcp_dispatch')]
            assert normalized(direct['before'], direct['refs']) == normalized(mcp['before'], mcp['refs'])
        cells[cell] = indexed
    assert set(cells) == set(registry['cells']) and len(locks) == len(runs) == len(commits) == 1
    for key in cells['old_old']:
        initial = cells['old_old'][key]
        for cell in cells.values():
            assert normalized(initial['before'], initial['refs']) == normalized(cell[key]['before'], cell[key]['refs'])
    for p in sorted(archive.rglob('*')):
        if p.is_file():
            hashes[str(p.relative_to(ROOT))] = sha(p)
    basic = all(r['schema_valid'] and r['operation_success'] and r['requested_postcondition'] for r in all_records)
    expected = all(r['frame_violations'] == (['collection_id'] if (r['cell'], r['case'], r['channel']) ==
                    ('old_old', 'grouped_edit', 'mcp_dispatch') else []) for r in all_records)
    payloads = all(r['put_has_collection_id'] == (r['channel'] == 'direct_complete' or r['case'] == 'explicit_clear'
                    or registry['cells'][r['cell']]['adapter'] == 'fixed') for r in all_records)
    return {'kind': 'iris_component_calibration_reconstruction_v1', 'run_id': next(iter(runs)),
            'study_commit': next(iter(commits)), 'status': 'reconstructed', 'executions': len(all_records),
            'known_mechanisms': 1, 'new_defects_claimed': 0,
            'calibration_gate_passed': basic and expected and payloads,
            'all_schema_success_requested_postcondition_pass': basic,
            'published_component_effects_reproduced': expected,
            'component_payload_effects_reproduced': payloads,
            'frame_alerts': sum(bool(r['frame_violations']) for r in all_records),
            'naive_false_alarms_on_intentional_clears': sum(r['naive_membership_preservation_alert']
                and not r['frame_violations'] for r in all_records if r['case'] == 'explicit_clear'),
            'scores': sorted(all_records, key=lambda r: (r['cell'], r['case'], r['channel'])),
            'raw_sha256': hashes, 'shared_dependency_lock_sha256': next(iter(locks)),
            'limits': ['Outcome-selected historical case, not independent efficacy or prevalence.',
                       'Actual MCP dispatcher and ASGI backend, no MCP session/wire or browser execution.',
                       'Hybrid component combinations are experimental, not released versions.',
                       'Preservation frame is a competent baseline, not a new method.']}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    result = build(args.archive.resolve())
    if args.output:
        assert not args.output.exists()
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    if args.verify:
        assert result == json.loads(args.verify.read_text())
    print(json.dumps({k: v for k, v in result.items() if k not in ('scores', 'raw_sha256', 'limits')}, indent=2))

if __name__ == '__main__':
    main()
