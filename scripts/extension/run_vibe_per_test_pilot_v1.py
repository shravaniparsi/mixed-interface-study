#!/usr/bin/env python3
"""Bounded unchanged-suite replay with original controls and per-test evidence."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / 'results/evaluation-feasibility-screen-v1/vibe-testing-replication-package.zip'
DIGEST = 'd3ba05db5587ce8fcec62cbcb0096d30e10534088ee3012c3f712be84e5a18ec'
PREFIX = 'vibe-testing-replication-package/'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def totals(path):
    suites = list(ET.parse(path).getroot().iter('testsuite'))
    value = {k: sum(int(s.get(k, 0)) for s in suites) for k in ['tests', 'failures', 'errors', 'skipped']}
    value['passed'] = value['tests'] - value['failures'] - value['errors'] - value['skipped']
    return value


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--level', choices=['L0', 'L4'], required=True); parser.add_argument('--output', type=Path, required=True); args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    work = out / 'working'; work.mkdir(); app = work / 'app'; app.mkdir()
    plugin = out / 'plugin'; plugin.mkdir(); shutil.copyfile(Path(__file__).with_name('vibe_trace_plugin_v1.py'), plugin / 'vibe_trace_plugin_v1.py')
    assert sha(ARCHIVE.read_bytes()) == DIGEST
    with zipfile.ZipFile(ARCHIVE) as archive:
        files = {n[len(PREFIX):]: archive.read(n) for n in archive.namelist() if not n.endswith('/')}
    sources = {p: b for p, b in files.items() if p.startswith('02_target_api/app/') and p.endswith('.py')}
    for name, raw in sources.items():
        relative = Path(name).relative_to('02_target_api'); target = work / relative; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
    original = files['02_target_api/app/crud.py']; operators = None
    for node in ast.parse(files['07_mutation_testing/scripts/_mutation_worker.py']).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'MUTATIONS' for t in node.targets):
            operators = ast.literal_eval(node.value)
    assert len(operators) == 15
    suites = sorted(p for p in files if p.startswith('04_context_axis/generated_suites/') and p.endswith(f'__bookstore__{args.level}__run1__t0_4.py'))
    assert len(suites) == 5
    expected = [f'{Path(s).parent.name}--{name}' for s in suites for name in ['original-before'] + [o[0] for o in operators] + ['original-after']]
    report = {'kind': 'vibe_per_test_pilot_v1', 'level': args.level, 'archive_sha256': DIGEST, 'expected_keys': expected, 'trials': [], 'terminal': 'running', 'paid_model_calls': 0, 'source_hashes': {p: sha(b) for p, b in sources.items()}}
    started = time.monotonic(); deadline = started + 17 * 60
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(plugin), PYTHONUNBUFFERED='1', API_KEY='test-api-key', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    def save():
        report['unattempted_keys'] = expected[len(report['trials']):]
        (out / 'observations.tmp').write_text(json.dumps(report, indent=2) + '\n'); (out / 'observations.tmp').replace(out / 'observations.json')
    def stop(process):
        if process and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL); process.wait(timeout=3)
    def trial(key, suite, name, code):
        directory = out / key; directory.mkdir(); row = {'key': key, 'suite': suite, 'operator': name, 'suite_sha256': sha(files[suite]), 'source_sha256': sha(code), 'test_executed': False}
        service = None; stage = 'restore'
        try:
            for path, raw in sources.items():
                (work / Path(path).relative_to('02_target_api')).write_bytes(raw)
            (app / 'crud.py').write_bytes(code); (work / 'test_suite.py').write_bytes(files[suite])
            for p in work.glob('bookstore.db*'):
                p.unlink()
            assert not list(work.rglob('*.pyc'))
            stage = 'startup'
            launch = "import hashlib,json,os;import app.crud;print(json.dumps({'pid':os.getpid(),'source_sha256':hashlib.sha256(open(app.crud.__file__,'rb').read()).hexdigest()}),flush=True);import uvicorn;uvicorn.run('app.main:app',host='127.0.0.1',port=8000,log_level='warning')"
            with (directory / 'service.log').open('w') as stream:
                service = subprocess.Popen([sys.executable, '-c', launch], cwd=work, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            row['pid'] = service.pid; attempts = []
            health_deadline = min(deadline, time.monotonic() + 20)
            while time.monotonic() < health_deadline:
                if service.poll() is not None:
                    break
                try:
                    with urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2) as response:
                        attempts.append({'status': response.status, 'body': response.read().decode()})
                    if attempts[-1]['status'] == 200:
                        break
                except Exception as error:
                    attempts.append({'exception': type(error).__name__})
                time.sleep(0.25)
            row['health'] = attempts
            assert attempts and attempts[-1].get('status') == 200 and service.poll() is None
            imported = json.loads((directory / 'service.log').read_text().splitlines()[0])
            assert imported['pid'] == service.pid and imported['source_sha256'] == sha(code)
            row['imported'] = imported; stage = 'reset'
            with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/reset', method='POST'), timeout=5) as response:
                row['reset'] = {'status': response.status, 'body': response.read().decode()}
            assert row['reset']['status'] == 200 and json.loads(row['reset']['body'])['status'] == 'ok'
            with sqlite3.connect(work / 'bookstore.db') as connection:
                tables = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
                assert tables
                counts = {t: connection.execute('SELECT COUNT(*) FROM "' + t.replace('"', '""') + '"').fetchone()[0] for t in tables}
            row['reset_counts'] = counts; assert all(n == 0 for n in counts.values())
            stage = 'test'; remaining = max(1, min(60, deadline - time.monotonic())); row['timeout_seconds'] = remaining
            test_env = dict(env, VIBE_TRACE_EVENTS=str(directory / 'events.jsonl'))
            command = [sys.executable, '-m', 'pytest', 'test_suite.py', '-p', 'vibe_trace_plugin_v1', '-p', 'no:cacheprovider', '-v', '--tb=short', '--junitxml=' + str(directory / 'junit.xml')]
            with (directory / 'pytest.log').open('w') as stream:
                process = subprocess.Popen(command, cwd=work, env=test_env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
                row['test_executed'] = True; row['timeout'] = False
                try:
                    process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    row['timeout'] = True; stop(process)
            row['return_code'] = process.returncode
            xml = directory / 'junit.xml'
            if xml.exists():
                row['junit'] = totals(xml)
            row['outcome'] = 'timeout' if row['timeout'] else 'reported' if xml.exists() and process.returncode in [0, 1] else 'execution_failure'
        except Exception as error:
            row.update(outcome=stage + '_failure', error=type(error).__name__ + ': ' + str(error))
        finally:
            stop(service)
            if service:
                row['server_exit_code'] = service.returncode
            (app / 'crud.py').write_bytes(original)
        return row
    save()
    for suite in suites:
        usable = False
        for name, pattern, replacement in [('original-before', None, None)] + operators + [('original-after', None, None)]:
            if time.monotonic() >= deadline:
                report['terminal'] = 'soft_limit'; save(); return 1
            key = f'{Path(suite).parent.name}--{name}'; code = original; skipped = None
            if pattern is not None:
                text, count = re.subn(pattern, replacement, original.decode(), count=1); code = text.encode()
                if not count:
                    skipped = 'not_applied'
                else:
                    try:
                        ast.parse(text)
                    except SyntaxError:
                        skipped = 'syntax_invalid'
                if not skipped and not usable:
                    skipped = 'unusable_original_control'
            if skipped:
                row = {'key': key, 'suite': suite, 'operator': name, 'suite_sha256': sha(files[suite]), 'source_sha256': sha(code), 'test_executed': False, 'outcome': skipped}
            else:
                row = trial(key, suite, name, code)
            report['trials'].append(row); save()
            if name == 'original-before':
                usable = row['outcome'] == 'reported' and row.get('junit', {}).get('passed', 0) > 0
    report['terminal'] = 'completed'; report['elapsed_seconds'] = time.monotonic() - started; save()
    print(json.dumps({'level': args.level, 'terminal': report['terminal'], 'records': len(report['trials'])}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
