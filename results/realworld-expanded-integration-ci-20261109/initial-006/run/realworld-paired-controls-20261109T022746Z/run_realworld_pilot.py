#!/usr/bin/env python3
"""Run clean paired routes from identical offline SQLite snapshots.

Requires the pinned subject, its installed dependencies, built frontend, Node,
Playwright and Chrome. Does not install dependencies or change application code.
All database files are new, task-owned files under --runtime-root.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
from urllib.request import Request, urlopen


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree_sha(path):
    digest = hashlib.sha256()
    for item in sorted(Path(path).rglob('*')):
        if item.is_file():
            digest.update(item.relative_to(path).as_posix().encode() + b'\0')
            digest.update(bytes.fromhex(sha(item)))
    return digest.hexdigest()


def wait_http(url, process, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Server exited before becoming ready")
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.15)
    raise TimeoutError("Local server readiness timed out: " + url)


def stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--subject', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--node', type=Path, required=True)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--results', type=Path, default=Path(__file__).resolve().parents[1] / 'results')
    parser.add_argument('--repetitions', type=int, default=2)
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error('repetitions must be positive')
    subject = args.subject.resolve()
    frontend = subject / 'fronts/vue3-realworld-example-app'
    script = Path(__file__).with_name('realworld_route_smoke.mjs').resolve()
    for path in [subject/'manage.py', frontend/'dist/index.html', args.python, args.node, script]:
        if not path.exists():
            raise FileNotFoundError(path)
    for port in [18765, 18766]:
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1', port)) == 0:
                raise RuntimeError('Port already occupied: {}'.format(port))
    args.runtime_root.mkdir(parents=True, exist_ok=True)
    runtime = Path(tempfile.mkdtemp(prefix='paired-routes-', dir=args.runtime_root))
    run_id = dt.datetime.now(dt.timezone.utc).strftime('realworld-%Y%m%dT%H%M%SZ')
    output = args.results.resolve() / run_id
    output.mkdir(parents=True, exist_ok=False)
    database = runtime / 'active.sqlite3'
    snapshot = runtime / 'fixture.sqlite3'
    env = dict(os.environ, DEBUG='True', DATABASE_URL='file:' + str(database), TZ='UTC', PYTHONDONTWRITEBYTECODE='1',
               REALWORLD_API_BASE='http://127.0.0.1:18765', REALWORLD_UI_BASE='http://127.0.0.1:18766',
               REALWORLD_EMAIL='pilot@example.com', REALWORLD_PASSWORD='Pilot-Research-123!', REALWORLD_USERNAME='pilotresearch')
    report = {
        'kind': 'clean_workflow_feasibility_pilot', 'run_id': run_id,
        'independent_workflow_templates': 1, 'repetitions_per_route': args.repetitions,
        'not_a_defect_discovery_or_strategy_comparison': True,
        'backend_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=subject,text=True).strip(),
        'frontend_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=frontend,text=True).strip(),
        'script_sha256': {'orchestrator': sha(__file__), 'browser_runner': sha(script)},
        'frontend_dist_sha256': tree_sha(frontend/'dist'),
        'database_reset': 'Stop backend, copy immutable fixture, verify SHA256, restart; fresh browser each case.',
        'cases': [], 'status': 'running', 'cash_spent_usd': 0,
    }
    backend = frontend_process = None
    handles = []
    shutil.copyfile(__file__, output/'orchestrator-at-execution.py')
    shutil.copyfile(script, output/'runner-at-execution.mjs')

    def save():
        (output/'summary.json').write_text(json.dumps(report, indent=2)+'\n')

    def start_backend(label):
        log = open(output/(label+'-server.log'), 'w')
        handles.append(log)
        process = subprocess.Popen([str(args.python), 'manage.py', 'runserver', '127.0.0.1:18765', '--noreload'], cwd=subject, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            wait_http('http://127.0.0.1:18765/api/tags', process)
        except Exception:
            stop(process)
            raise
        return process

    try:
        with open(output/'migration.log', 'w') as log:
            subprocess.run([str(args.python),'manage.py','migrate','--noinput'], cwd=subject, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=60)
        backend = start_backend('fixture')
        fixture = {'user': {'username':'pilotresearch','email':'pilot@example.com','password':'Pilot-Research-123!'}}
        request = Request('http://127.0.0.1:18765/api/users', data=json.dumps(fixture).encode(), method='POST', headers={'Content-Type':'application/json'})
        with urlopen(request, timeout=10) as response:
            if response.status != 201:
                raise AssertionError('Fixture creation was not accepted')
        stop(backend)
        backend = None
        shutil.copyfile(database, snapshot)
        report['fixture_sha256'] = sha(snapshot)
        log = open(output/'frontend.log', 'w')
        handles.append(log)
        frontend_process = subprocess.Popen([str(args.node), 'node_modules/vite/bin/vite.js', 'preview', '--host', '127.0.0.1', '--port', '18766', '--strictPort'], cwd=frontend, env=env, stdout=log, stderr=subprocess.STDOUT)
        wait_http('http://127.0.0.1:18766', frontend_process)
        for repetition in range(1, args.repetitions+1):
            for route in ['ui-ui', 'api-ui', 'ui-api', 'api-api']:
                case_id = '{}-r{}'.format(route, repetition)
                shutil.copyfile(snapshot, database)
                reset_hash = sha(database)
                if reset_hash != report['fixture_sha256']:
                    raise AssertionError('Fixture restoration changed database bytes')
                backend = start_backend(case_id)
                result_path = output/(case_id+'.json')
                started = time.monotonic()
                with open(output/(case_id+'-runner.log'), 'w') as log:
                    completed = subprocess.run([str(args.node),str(script),'--route',route,'--case-id',case_id,'--output',str(result_path)], cwd=subject, env=env, stdout=subprocess.DEVNULL, stderr=log, timeout=180)
                stop(backend)
                backend = None
                result = json.loads(result_path.read_text()) if result_path.exists() else {}
                case = {'case_id':case_id,'route':route,'repetition':repetition,'reset_sha256':reset_hash,'exit_code':completed.returncode,'outcome':result.get('outcome','runner_failed_without_result'),'seconds':round(time.monotonic()-started,3),'evidence':result_path.name}
                report['cases'].append(case)
                save()
                print(json.dumps(case), flush=True)
        states = [json.loads((output/c['evidence']).read_text()).get('final_business_state') for c in report['cases'] if c['outcome']=='pass']
        expected = {'title': 'Pilot workflow article', 'description': 'Paired UI and API workflow control',
                    'body': 'Pilot body after a meaningful edit.', 'tagList': ['pilot'], 'author': 'pilotresearch'}
        report['all_passing_routes_agree_on_business_state'] = bool(states) and all(s == expected for s in states)
        passed = len(report['cases']) == 4*args.repetitions and all(c['outcome']=='pass' and c['exit_code']==0 for c in report['cases']) and report['all_passing_routes_agree_on_business_state']
        report['status'] = 'passed' if passed else 'failed'
    except Exception as exc:
        report['status'] = 'environment_or_runner_error'
        report['error'] = '{}: {}'.format(type(exc).__name__, exc)
    finally:
        stop(backend)
        stop(frontend_process)
        for handle in handles:
            handle.close()
        report['finished_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
        save()
        print(json.dumps({'status':report['status'],'summary':str(output/'summary.json'),'error':report.get('error')}), flush=True)
    return 0 if report['status']=='passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
