#!/usr/bin/env python3
"""Predeclared per-input request/state classifications; never a bug counter."""
import argparse
from collections import Counter
import json
from pathlib import Path

def typed(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))

def same_request(left, right):
    if left['method'] != right['method'] or left['path'] != right['path']:
        return False
    allowed = ['application/json', 'application/merge-patch+json'] if left['method'] == 'PATCH' else ['application/json']
    if left['content_type'].split(';')[0].strip().lower() not in allowed or right['content_type'].split(';')[0].strip().lower() not in allowed:
        return False
    try:
        return typed(json.loads(left['raw_body'])) == typed(json.loads(right['raw_body']))
    except ValueError:
        return False

def classify(row):
    rest = row['routes']['rest']; mcp = row['routes']['mcp']
    assert rest['expected_state_match'] and len(rest['captured_requests']) == 1
    requests = mcp['captured_requests']
    equal = len(requests) == 1 and same_request(rest['captured_requests'][0], requests[0])
    response = mcp['call']
    error = 'error' in response or response.get('result', {}).get('isError', False)
    if not requests:
        category = 'no_outbound_request'
    elif not mcp['expected_state_match']:
        category = 'persisted_state_difference'
    elif not equal:
        category = 'request_difference_without_state_difference'
    elif error:
        category = 'preserved_state_with_tool_error'
    else:
        category = 'preserved'
    return {'repetition': row['repetition'], 'case_id': row['case_id'], 'classification': category, 'tool_schema_valid': not row['tool_schema_errors'], 'request_equivalent': equal, 'state_preserved': mcp['expected_state_match'], 'tool_error': bool(error)}

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('archive', type=Path); args = parser.parse_args()
    observations = json.loads((args.archive / 'observations.json').read_text())
    rows = [classify(row) for row in observations['records']]
    result = {'subject': observations['subject'], 'terminal': observations['terminal'], 'paired_observations': len(rows), 'planned_paired_observations': 96, 'unexecuted_pairs': 96 - len(rows), 'counts': dict(Counter(row['classification'] for row in rows)), 'records': rows, 'independent_defect_count': None}
    (args.archive / 'scores.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}))

if __name__ == '__main__':
    main()
