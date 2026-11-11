"""Replay manually supplied write contracts without application-specific logic.

This is a competent baseline and artifact interface, not contract inference.
Absent measurements are unavailable; absent keys in measured views differ from null.
"""
import argparse
import json
from pathlib import Path
from .write_frame import equal, evaluate


def check(record):
    contract = record['contract']
    derived_values = contract.get('derived_assignments', {})
    derived_fields = set(contract.get('derived_fields', [])) | set(derived_values)
    frame = evaluate(record['before'], record['after'], contract['assignments'], derived_fields)
    derived_failures = sorted(k for k, value in derived_values.items()
                              if k not in record['after'] or not equal(value, record['after'][k]))
    agreements = []
    for obligation in contract.get('agreements', []):
        left_name, right_name = obligation['left'], obligation['right']
        left = record.get('views', {}).get(left_name)
        right = record.get('views', {}).get(right_name)
        available = isinstance(left, dict) and isinstance(right, dict)
        failures = sorted(k for k in obligation['fields']
                          if available and (k not in left or k not in right or not equal(left[k], right[k])))
        agreements.append({'left': left_name, 'right': right_name,
                           'status': ('fail' if failures else 'pass') if available else 'unavailable',
                           'mismatched_or_missing_fields': failures})
    violation = bool(frame['failed_assignments'] or frame['frame_violations']
                     or derived_failures or any(a['status'] == 'fail' for a in agreements))
    return {'id': record['id'], 'frame': frame, 'derived_assignment_failures': derived_failures,
            'agreements': agreements, 'contract_violation': violation,
            'all_declared_observations_available': all(a['status'] != 'unavailable' for a in agreements)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    bundle = json.loads(args.input.read_text())
    result = {'scores': [check(r) for r in bundle['records']]}
    encoded = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end='')


if __name__ == '__main__':
    main()
