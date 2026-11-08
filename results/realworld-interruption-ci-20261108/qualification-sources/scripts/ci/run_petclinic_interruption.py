#!/usr/bin/env python3
"""Interrupt a real hosted control run, observe cleanup, then run fresh controls.

Linux-only qualification. Observations do not establish cleanup for unobserved
processes or other interruption phases. No mutation candidates are selected.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time

from owned_process_scope import interruption_as_exception, defer_stop_signals

ROOT = Path(__file__).resolve().parents[2]


def snapshot(proc=Path('/proc')):
    result = {}
    for directory in proc.iterdir():
        if not directory.name.isdigit():
            continue
        try:
            raw = (directory/'stat').read_text()
            fields = raw[raw.rindex(')')+2:].split()
            pid = int(directory.name)
            result[pid] = {'pid': pid, 'ppid': int(fields[1]), 'state': fields[0],
                           'start_ticks': fields[19],
                           'command': (directory/'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')}
        except (FileNotFoundError, ProcessLookupError):
            continue
    return result


def track(table, root_pid, known):
    """Expand only from the root or identities already observed as descendants."""
    parents = {root_pid} | {pid for pid, p in known.items()
                              if pid in table and table[pid]['start_ticks'] == p['start_ticks']}
    while True:
        added = {pid for pid, p in table.items() if p['ppid'] in parents} - parents
        if not added:
            break
        parents |= added
    for pid in parents - {root_pid}:
        if pid in table:
            known[pid] = table[pid]
    return known


def survivors(table, known):
    return [p for pid, p in table.items() if pid in known
            and p['start_ticks'] == known[pid]['start_ticks'] and p['state'] not in {'Z', 'X'}]


def port_open(port):
    with socket.socket() as connection:
        connection.settimeout(.2)
        return connection.connect_ex(('127.0.0.1', port)) == 0


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def main():
    if not Path('/proc/self/stat').exists():
        raise RuntimeError('Qualification requires Linux procfs')
    artifact = Path(os.environ['CI_ARTIFACT_DIR'])
    report = {'status': 'incomplete', 'scope': 'PetClinic ordinary controls; one SIGTERM checkpoint',
              'source_commit': os.environ['GITHUB_SHA'], 'primary_freeze_complete': False,
              'deadline_s': {'checkpoint': 180, 'wrapper_exit': 18, 'observed_descendants': 4, 'fresh_controls': 300},
              'timed_selector_calibration': False}
    source_names = ['scripts/ci/run_petclinic_interruption.py', 'scripts/ci/run_petclinic_integrity.py',
                    'scripts/ci/owned_process_scope.py', 'scripts/petclinic_boundary_slice.mjs',
                    'manifests/petclinic-integrity-controls-v1.json', '.github/workflows/applications.yml',
                    'scripts/ci/run_applications.sh']
    report['source_sha256'] = {n: hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in source_names}
    save(artifact/'petclinic-interruption-plan.json', report)
    child = None
    known = {}
    began = time.monotonic()
    try:
        for stage in ('interrupted', 'fresh'):
            destination = artifact/('petclinic-'+stage)
            destination.mkdir(exist_ok=False)
            for name in ('petclinic-bootstrap.json', 'runtime-versions.json', 'browser.json'):
                shutil.copyfile(artifact/name, destination/name)
            env = {**os.environ, 'CI_ARTIFACT_DIR': str(destination)}
            with (destination/'wrapper.log').open('x') as log:
                child = subprocess.Popen([sys.executable, str(ROOT/'scripts/ci/run_petclinic_integrity.py')],
                                         env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                known = {}
                if stage == 'interrupted':
                    deadline = time.monotonic()+180
                    while True:
                        table = snapshot(); track(table, child.pid, known)
                        # A completed first API control plus a live browser and the next
                        # JVM establishes entry into the paired native-control lifecycle.
                        observations = list((destination/'petclinic-integrity-controls').glob('*-api_semantic.json'))
                        api_pass = False
                        for path in observations:
                            try:
                                api_pass |= json.loads(path.read_text()).get('status') == 'continuation_passed'
                            except json.JSONDecodeError:
                                pass  # A result may still be in the middle of its write.
                        live = survivors(table, known)
                        chrome = [p for p in live if 'chrome' in p['command'].lower()]
                        java = [p for p in live if ' -jar ' in p['command']]
                        if api_pass and chrome and java and port_open(9966):
                            report['checkpoint'] = {'kind': 'first_API_control_completed_next_JVM_listening_browser_alive',
                                                    'observed_descendants': live, 'elapsed_s': time.monotonic()-began}
                            break
                        if child.poll() is not None:
                            raise RuntimeError('Wrapper exited before interruption checkpoint')
                        if time.monotonic() > deadline:
                            raise TimeoutError('Interruption checkpoint not reached')
                        time.sleep(.05)
                    sent = time.monotonic()
                    child.send_signal(signal.SIGTERM)
                    while child.poll() is None and time.monotonic()-sent < 18:
                        track(snapshot(), child.pid, known); time.sleep(.05)
                    if child.poll() is None:
                        raise TimeoutError('Wrapper did not exit within interruption deadline')
                    child.wait()
                    report['interruption'] = {'signal': 'SIGTERM', 'wrapper_returncode': child.returncode,
                                               'wrapper_exit_s': time.monotonic()-sent}
                    if child.returncode != 143:
                        raise RuntimeError('Unexpected interrupted-wrapper exit code')
                else:
                    deadline = time.monotonic()+300
                    while child.poll() is None and time.monotonic() < deadline:
                        track(snapshot(), child.pid, known); time.sleep(.1)
                    if child.poll() is None:
                        raise TimeoutError('Fresh-control deadline exceeded')
                    child.wait()
                    if child.returncode != 0:
                        raise RuntimeError('Fresh control run failed')
                    validation = json.loads((destination/'petclinic-integrity-validation.json').read_text())
                    report['fresh_control_validation'] = validation
                deadline = time.monotonic()+4
                while True:
                    remaining = survivors(snapshot(), known)
                    if not remaining or time.monotonic() >= deadline:
                        break
                    time.sleep(.05)
                cleanup = json.loads((destination/'petclinic-owned-process-cleanup.json').read_text())
                report[stage+'_cleanup'] = {'observed_processes': list(known.values()), 'live_survivors': remaining,
                                             'ports_open': {str(p): port_open(p) for p in (9966, 19766)},
                                             'wrapper_cleanup': cleanup}
                save(artifact/'petclinic-interruption-report.json', report)
                if remaining or any(report[stage+'_cleanup']['ports_open'].values()):
                    raise RuntimeError(stage+' cleanup left live observed processes or listeners')
                if not cleanup or not all(p['exit_confirmed'] and not p.get('errors') for p in cleanup.values()):
                    raise RuntimeError('Wrapper cleanup evidence incomplete')
        report['status'] = 'qualified_at_declared_checkpoint'
    except BaseException as error:
        report['error'] = type(error).__name__+': '+str(error)
        raise
    finally:
        with defer_stop_signals():
            # Rescue is recorded and can never turn the qualification into a pass.
            rescue = []
            if child is not None:
                if child.poll() is None:
                    child.kill(); child.wait(timeout=3); rescue.append({'wrapper_pid': child.pid})
                for p in survivors(snapshot(), known):
                    current = snapshot().get(p['pid'])
                    if current and current['start_ticks'] == p['start_ticks']:
                        try:
                            os.kill(p['pid'], signal.SIGKILL); rescue.append(p)
                        except ProcessLookupError:
                            pass
            if rescue:
                report['status'] = 'failed_rescue_required'
            report['rescue_actions'] = rescue
            report['elapsed_s'] = time.monotonic()-began
            save(artifact/'petclinic-interruption-report.json', report)
            if rescue:
                raise RuntimeError('Emergency cleanup was required; qualification failed')


if __name__ == '__main__':
    with interruption_as_exception():
        main()
