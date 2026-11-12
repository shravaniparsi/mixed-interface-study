#!/usr/bin/env python3
"""Extend v1's explicit marker inventory with remote disconnects and output caps."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from audit_restestbench_nestjs_unready_v1 import build as build_v1, ROOT


def build():
    previous_path = ROOT / 'manifests/restestbench-nestjs-unready-released-v1.json'
    previous = build_v1()
    assert json.loads(previous_path.read_text()) == previous
    rows = []
    for old in previous['rows']:
        row = dict(old)
        markers = list(row['recorded_failure_markers'])
        if 'RemoteDisconnected' in row['record']['output']:
            markers.append('RemoteDisconnected')
        row['recorded_failure_markers'] = markers
        row['at_serialized_output_cap'] = len(row['record']['output']) == 2000
        rows.append(row)
    executor = ROOT / 'evidence/restestbench-source-v1/src/executor.py'
    assert 'self.output[:2000] if len(self.output) > 2000 else self.output' in executor.read_text()
    result = dict(previous)
    result.update(kind='restestbench_nestjs_unready_released_audit_v2', rows=rows,
                  marker_counts=dict(Counter(m for r in rows for m in r['recorded_failure_markers'])),
                  credited_with_connectivity_marker=sum(r['credited_in_evaluation'] and any('Connection' in m or 'Timeout' in m or m == 'RemoteDisconnected' for m in r['recorded_failure_markers']) for r in rows),
                  outputs_at_2000_character_cap=sum(r['at_serialized_output_cap'] for r in rows),
                  records_without_explicit_failure_marker=sum(not r['recorded_failure_markers'] for r in rows),
                  previous_analysis_sha256=hashlib.sha256(previous_path.read_bytes()).hexdigest(),
                  output_serialization_source_sha256=hashlib.sha256(executor.read_bytes()).hexdigest(),
                  revision='Added RemoteDisconnected after inspecting unmatched outputs; v1 retained unchanged. No new runtime observations.')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    result = build()
    path = ROOT / 'manifests/restestbench-nestjs-unready-released-v2.json'
    if args.verify:
        assert json.loads(path.read_text()) == result
    else:
        assert not path.exists()
        path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ['rows', 'files_without_selected_record']}, indent=2))


if __name__ == '__main__':
    main()
