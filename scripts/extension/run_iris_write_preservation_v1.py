#!/usr/bin/env python3
"""Compose predeclared upstream components, then retain all observer outcomes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cell', required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--fixed', type=Path, required=True)
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    output, source, fixed = args.output.resolve(), args.source.resolve(), args.fixed.resolve()
    registry_path = ROOT / 'manifests/iris-write-preservation-calibration-v1.json'
    registry = json.loads(registry_path.read_text())
    cell = registry['cells'][args.cell]
    report = {'kind': 'iris_component_calibration_v1', 'cell': args.cell, 'status': 'incomplete',
              'registry_sha256': sha(registry_path), 'study_commit': os.environ['GITHUB_SHA'],
              'run_id': os.environ['GITHUB_RUN_ID'], 'run_attempt': os.environ['GITHUB_RUN_ATTEMPT'],
              'commands': []}
    def run(command, cwd=source, timeout=30, env=None):
        path = output / ('command-%02d.log' % len(report['commands']))
        started = time.monotonic()
        with path.open('w') as log:
            result = subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                                    env=env, timeout=timeout, text=True)
        report['commands'].append({'args': command, 'returncode': result.returncode,
                                  'elapsed_seconds': time.monotonic() - started, 'log': path.name})
        if result.returncode:
            raise RuntimeError('Command failed: ' + ' '.join(command))
        return path.read_text()
    try:
        for name, expected in registry['source_sha256'].items():
            assert sha(ROOT / name) == expected, name
        assert run(['git', 'rev-parse', 'HEAD']).strip() == registry['historical_commit']
        assert run(['git', 'rev-parse', 'HEAD'], cwd=fixed).strip() == registry['fixed_commit']
        assert not run(['git', 'status', '--porcelain']).strip()
        assert not run(['git', 'status', '--porcelain'], cwd=fixed).strip()
        for component, paths in registry['component_files'].items():
            if cell[component] == 'fixed':
                for name in paths:
                    shutil.copyfile(fixed / name, source / name)
        expected_paths = {name for component, paths in registry['component_files'].items()
                          if cell[component] == 'fixed' for name in paths}
        changed = set(run(['git', 'diff', '--name-only']).splitlines())
        assert changed == expected_paths, (changed, expected_paths)
        source_hashes = {}
        for component, paths in registry['component_files'].items():
            for name in paths:
                origin = fixed if cell[component] == 'fixed' else source
                assert sha(source / name) == sha(origin / name)
                dest = output / 'component-source' / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / name, dest)
                source_hashes[name] = sha(dest)
        for name in ('LICENSE', 'LICENSE.md', 'NOTICE'):
            if (source / name).is_file():
                shutil.copyfile(source / name, output / name)
        report['component_sha256'] = source_hashes
        shutil.copyfile(args.lock, output / 'requirements.txt')
        report['lock_sha256'] = sha(args.lock)
        report['python_version'] = run(['python', '--version'])
        run(['python', '-m', 'pip', 'freeze', '--all'])
        env = dict(os.environ)
        env['PYTHONPATH'] = os.pathsep.join(str(source / p) for p in ['backend', 'mcp/src', 'iris-client/src'])
        env['STUDY_APP_ROOT'] = str(source)
        run(['python', str(ROOT / 'scripts/extension/observe_iris_write_preservation_v1.py'),
             '--output', str(output / 'observations')], timeout=480, env=env)
        paths = sorted((output / 'observations').glob('*.json'))
        records = [json.loads(p.read_text()) for p in paths]
        assert len(records) == 6
        assert all(r['status'] == 'observed' for r in records)
        report['scores'] = [{'case': r['case'], 'channel': r['channel'], **r['scores']} for r in records]
        report['status'] = 'observed'
    except BaseException as error:
        report.update(error_type=type(error).__name__, error=str(error))
    finally:
        report['files_sha256'] = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob('*'))
                                  if p.is_file() and p != output / 'report.json'}
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['status'] == 'observed' else 1

if __name__ == '__main__':
    raise SystemExit(main())
