#!/usr/bin/env python3
"""Check paired observations against raw service events and final SQLite state."""
import argparse
import json
from pathlib import Path
import sqlite3
from score_adapter_comparison_v1 import classify, typed

ROOT = Path(__file__).resolve().parents[2]

def verify(folder):
    observed = json.loads((folder / 'observations.json').read_text())
    eventfile = folder / 'events.jsonl'
    captured = [json.loads(line) for line in eventfile.read_text().splitlines()] if eventfile.exists() else []
    if not eventfile.exists():
        assert observed['terminal'] == 'failed' and not observed['records']
    inventory = json.loads((ROOT / 'manifests/openapi-adapter-input-inventory-v1.json').read_text())['cases']
    ordered = [c for c in inventory if c['id'].endswith(':all-ordinary')] + [c for c in inventory if not c['id'].endswith(':all-ordinary')]
    scheduled = [(repeat, case) for repeat in [1, 2] for case in ordered]
    assert observed['paid_model_calls'] == 0
    assert observed['backend_reaped'] and observed['converter_reaped']
    offset = 0; rows = []
    for index, row in enumerate(observed['records']):
        repetition, case = scheduled[index]
        assert (row['repetition'], row['case_id']) == (repetition, case['id'])
        arguments = dict(case['body'])
        if case['operation_id'] == 'patch_record':
            arguments['record_id'] = 'seed'
        assert typed(arguments) == typed(row['tool_arguments'])
        for route in (['rest', 'mcp'] if repetition == 1 else ['mcp', 'rest']):
            current = row['routes'][route]
            reset = captured[offset]; offset += 1
            assert (reset['method'], reset['path'], reset['status']) == ('POST', '/__study/reset', 200)
            assert typed(json.loads(reset['raw_body'])) == typed({'records': case['initial_records']})
            count = len(current['captured_requests'])
            assert captured[offset:offset + count] == current['captured_requests']; offset += count
            read = captured[offset]; offset += 1
            assert (read['method'], read['path']) == ('GET', '/records/' + case['target_id'])
            assert read['status'] == current['read_status'] and typed(read['response']) == typed(current['readback'])
            state = current['database_records']
            assert current['expected_state_match'] is (typed(state) == typed(case['expected_records']))
            if case['target_id'] in state:
                assert current['read_status'] == 200
                assert typed(current['readback']) == typed({'id': case['target_id'], 'data': state[case['target_id']]})
            else:
                assert current['read_status'] == 404
            last_state = state
        rows.append(classify(row))
    if observed['terminal'] == 'completed':
        assert len(rows) == 96 and offset == len(captured)
    # A stopped call can leave additional raw events; never discard them.
    if rows and offset == len(captured):
        with sqlite3.connect('file:' + str(folder / 'records.sqlite') + '?mode=ro', uri=True) as connection:
            final = {k: json.loads(v) for k, v in connection.execute('SELECT id,data FROM records')}
        assert typed(final) == typed(last_state)
    scores = json.loads((folder / 'scores.json').read_text())
    assert scores['records'] == rows and scores['paired_observations'] == len(rows)
    return {'subject': observed['subject'], 'terminal': observed['terminal'], 'verified_pairs': len(rows), 'matched_http_events': offset, 'additional_unpaired_http_events': len(captured) - offset}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('archive', type=Path); args = parser.parse_args()
    print(json.dumps(verify(args.archive.resolve()), indent=2))
