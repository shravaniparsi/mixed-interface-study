#!/usr/bin/env python3
"""Replay one known historical defect; retain raw observations and build failures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', choices=['historical', 'fixed'], required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = args.source.resolve()
    output = args.output.resolve()
    registry_path = ROOT / 'manifests/write-preservation-calibration-v1.json'
    registry = json.loads(registry_path.read_text())
    report = {'kind': 'historical_write_preservation_calibration_v1',
              'version': args.version, 'status': 'incomplete', 'commands': [],
              'registry_sha256': digest(registry_path),
              'study_commit': os.environ.get('GITHUB_SHA'),
              'run_id': os.environ.get('GITHUB_RUN_ID'),
              'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT')}
    def run(command, timeout=60, env=None):
        start = time.monotonic()
        log_path = output / ('command-%02d.log' % len(report['commands']))
        with log_path.open('w') as log:
            proc = subprocess.run(command, cwd=source, stdout=log, stderr=subprocess.STDOUT,
                                  timeout=timeout, env=env, text=True)
        report['commands'].append({'args': command, 'returncode': proc.returncode,
                                  'elapsed_seconds': time.monotonic() - start,
                                  'log': log_path.name})
        if proc.returncode:
            raise RuntimeError('Command failed: ' + ' '.join(command))
        return log_path.read_text()
    try:
        for path, expected in registry['source_sha256'].items():
            assert digest(ROOT / path) == expected, 'Study source drift: ' + path
        commit = run(['git', 'rev-parse', 'HEAD']).strip()
        assert commit == registry['versions'][args.version], 'Upstream commit drift'
        assert not run(['git', 'status', '--porcelain']).strip(), 'Upstream checkout not pristine'
        report['upstream_commit'] = commit
        report['rustc'] = run(['rustc', '--version', '--verbose'])
        report['cargo'] = run(['cargo', '--version'])
        report['cargo_lock_sha256'] = digest(source / 'Cargo.lock')
        original = source / 'src/mcp/mod.rs'
        report['original_module_sha256'] = digest(original)
        original.write_bytes(original.read_bytes() + b'\n' + (ROOT / 'scripts/extension/write_preservation_tiller_v1.rs').read_bytes())
        report['instrumented_module_sha256'] = digest(original)
        env = dict(os.environ)
        env['STUDY_RAW_OUTPUT'] = str(output / 'observations.json')
        env['CARGO_TERM_COLOR'] = 'never'
        run(['cargo', 'test', '--locked', '--lib', 'study_write_preservation_v1', '--',
             '--nocapture', '--test-threads=1'], timeout=1200, env=env)
        records = json.loads((output / 'observations.json').read_text())
        assert {(r['case'], r['channel']) for r in records} == {
            (case, channel) for case in registry['cases'] for channel in ['direct', 'mcp']}
        assert len(records) == 6
        from jsonschema import Draft202012Validator
        schemas = {r['case']: r['schema'] for r in records if r['channel'] == 'mcp'}
        scored = []
        for record in records:
            before, after = record['before'], record['after']
            changed = sorted(k for k in set(before) | set(after)
                             if k not in before or k not in after or before[k] != after[k])
            schema = schemas[record['case']]
            Draft202012Validator.check_schema(schema)
            errors = [e.message for e in Draft202012Validator(schema).iter_errors(record['input'])]
            scored.append({'case': record['case'], 'channel': record['channel'],
                           'schema_valid': not errors, 'schema_errors': errors,
                           'operation_success': record['operation_success'],
                           'requested_edit_persisted': after['note'] == record['input']['updates']['note'],
                           'changed_columns': changed,
                           'frame_violations': sorted(set(changed) - {'note'})})
        report['scores'] = scored
        report['status'] = 'observed'
    except BaseException as error:
        report.update(error_type=type(error).__name__, error=str(error))
    finally:
        report['files_sha256'] = {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file() and p.name != 'report.json'}
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['status'] == 'observed' else 1

if __name__ == '__main__':
    raise SystemExit(main())
