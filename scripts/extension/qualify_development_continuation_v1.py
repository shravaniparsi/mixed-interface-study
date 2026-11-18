#!/usr/bin/env python3
"""One seed and two supported search restores; no scientific perturbations."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
import urllib.error
import urllib.request

JAR_SHA = '1c7500685740eb01994aa13ea381f3eb9af2c65bfb92f2379e42bb909225c71b'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def tree_hashes(root):
    result = {}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():
            raise ValueError('Symlink in relational checkpoint')
        if p.is_file():
            result[str(p.relative_to(root))] = digest(p.read_bytes())
    if not result or not any(k.endswith('.mv.db') for k in result):
        raise ValueError('No H2 database in checkpoint')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['java', 'jar', 'node', 'output']:
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    out = Path(args.output).resolve(); out.mkdir(parents=True, exist_ok=True)
    private = out / 'runtime'; private.mkdir(exist_ok=False)
    runtime = private / 'warm'; runtime.mkdir()
    checkpoint = out / 'checkpoint-private'
    result = {'kind': 'ordinary_development_continuation_control', 'status': 'failed',
              'requests': [], 'phases': [], 'independent_evaluation_cases': 0}
    proc = None
    start = time.monotonic()

    def request(port, method, path, body=None, timeout=30):
        raw = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request('http://127.0.0.1:' + str(port) + path,
                                     data=raw, method=method,
                                     headers={'Content-Type': 'application/json'})
        row = {'port': port, 'method': method, 'path': path}
        result['requests'].append(row)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read(8 * 1024 * 1024 + 1)
            row['status'] = response.status
        if len(data) > 8 * 1024 * 1024:
            raise ValueError('Response size limit')
        row.update(bytes=len(data), sha256=digest(data))
        return json.loads(data)

    def stop():
        nonlocal proc
        if proc is None:
            return
        if proc.poll() is not None:
            raise RuntimeError('Application exited before requested shutdown')
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            code = proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL); proc.wait(timeout=10)
            proc = None
            raise RuntimeError('Graceful shutdown deadline; no checkpoint')
        result['phases'][-1]['shutdown_code'] = code
        proc = None
        if code not in (0, 143, -15):
            raise RuntimeError('Unexpected shutdown exit')

    def observe(phase):
        nonlocal proc
        row = {'phase': phase}; result['phases'].append(row)
        command = [args.java, '-Xmx1g', '-jar', str(Path(args.jar).resolve()),
                   '--spring.profiles.active=dev,api-docs', '--server.address=127.0.0.1', '--server.port=8080']
        with (runtime / (phase + '-application.log')).open('w') as log:
            proc = subprocess.Popen(command, cwd=runtime, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        ready = False
        for _ in range(60):
            if proc.poll() is not None:
                raise RuntimeError('Application exited during startup')
            try:
                health = request(8080, 'GET', '/management/health', timeout=3)
                if health.get('status') == 'UP':
                    ready = True; break
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
            time.sleep(2)
        if not ready:
            raise RuntimeError('Readiness deadline')
        script = Path(__file__).with_name('measure_development_continuation_v1.mjs')
        completed = subprocess.run([args.node, str(script), '--phase', phase, '--out', str(out)], timeout=180)
        row['browser_exit'] = completed.returncode
        if completed.returncode:
            raise RuntimeError('Native observation failed')
        row['browser'] = json.loads((out / (phase + '-browser.json')).read_text())
        row['search_before'] = row['browser']['search_before']
        stop()
        row['relational_files_after_shutdown'] = tree_hashes(runtime / 'build/h2db')
        log_text = (runtime / (phase + '-application.log')).read_text(errors='replace')
        row['application_log_sha256'] = digest(log_text.encode())
        row['startup_reindex_completed'] = 'Elasticsearch: Successfully performed reindexing' in log_text
        row['mail_send_failure_observed'] = 'Email could not be sent to user' in log_text

    try:
        if digest(Path(args.jar).read_bytes()) != JAR_SHA:
            raise ValueError('Application identity mismatch')
        result['jar_sha256'] = JAR_SHA
        interfaces = json.loads(subprocess.check_output(['ip', '-j', 'link'], text=True))
        if {i['ifname'] for i in interfaces} != {'lo'}:
            raise ValueError('Network isolation required')
        result['interfaces'] = interfaces
        version = subprocess.run([args.java, '-version'], capture_output=True, text=True, check=True)
        if 'Temurin-17.0.2+8' not in version.stdout + version.stderr:
            raise ValueError('Java version mismatch')
        result['java_version'] = version.stdout + version.stderr
        observe('warm')
        runtime = private / 'seed'; runtime.mkdir()
        observe('seed')
        shutil.copytree(runtime / 'build/h2db', checkpoint)
        original = tree_hashes(checkpoint)
        result['checkpoint_relational_files'] = original
        registered = request(9200, 'PUT', '/_snapshot/study_checkpoint', {'type': 'fs', 'settings': {'location': '/study-snapshots'}})
        if registered.get('acknowledged') is not True:
            raise ValueError('Repository registration failed')
        snapshot = request(9200, 'PUT', '/_snapshot/study_checkpoint/ordinary?wait_for_completion=true', {'include_global_state': True, 'partial': False}, timeout=120)
        result['snapshot'] = snapshot
        snap = snapshot['snapshot']
        if snap['state'] != 'SUCCESS' or snap['shards']['failed'] != 0:
            raise ValueError('Snapshot incomplete')
        indices = snap['indices']
        if not indices or not all(re.fullmatch('[a-z][a-z0-9_-]*', name) for name in indices):
            raise ValueError('Unexpected index inventory; no deletion attempted')
        for phase in ['native', 'api']:
            # Exact enumerated isolated indices only; never a wildcard delete.
            deleted = request(9200, 'DELETE', '/' + ','.join(sorted(indices)))
            if deleted.get('acknowledged') is not True:
                raise ValueError('Isolated index cleanup failed')
            restored = request(9200, 'POST', '/_snapshot/study_checkpoint/ordinary/_restore?wait_for_completion=true', {'indices': indices, 'include_global_state': True, 'partial': False}, timeout=120)
            result.setdefault('restores', []).append({'phase': phase, 'response': restored})
            if restored['snapshot']['shards']['failed'] != 0:
                raise ValueError('Restore shard failure')
            shutil.rmtree(runtime / 'build/h2db')
            shutil.copytree(checkpoint, runtime / 'build/h2db')
            if tree_hashes(runtime / 'build/h2db') != original:
                raise ValueError('Restored H2 bytes differ before startup')
            result['restores'][-1]['relational_bytes_match_before_startup'] = True
            observe(phase)
        phases = {p['phase']: p['browser'] for p in result['phases']}
        native, api = phases['native'], phases['api']
        result['comparisons'] = {
            'restored_start_full_record_equal': native['record'] == api['record'],
            'restored_start_actor_equal': native['actor'] == api['actor'],
            'restored_start_search_equal': native['search_before'] == api['search_before'],
            'complete_update_body_equal': native['consumer']['body'] == api['consumer']['body'],
            'both_updates_200': native['consumer']['status'] == api['consumer']['status'] == 200,
            'after_record_equal_except_lastModifiedDate': {k:v for k,v in native['after_edit'].items() if k != 'lastModifiedDate'} == {k:v for k,v in api['after_edit'].items() if k != 'lastModifiedDate'},
            'warm_native_update_200': phases['warm']['consumer']['status'] == 200,
            'post_update_search_equal': native['search_after'] == api['search_after'],
        }
        result['status'] = 'measurement_complete'
        result['general_continuation_equivalence_qualified'] = False
        result['scope'] = 'One exposed ordinary workflow; warm reference has a separately initialized state.'
    except Exception as error:
        result.update(error_type=type(error).__name__, error=str(error))
    finally:
        if proc is not None and proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL); proc.wait(timeout=10)
        result['elapsed_seconds'] = time.monotonic() - start
        (out / 'continuation-measurement.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['status'] == 'measurement_complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
