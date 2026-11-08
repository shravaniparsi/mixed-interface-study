#!/usr/bin/env python3
"""Interrupt a real hosted control run, observe cleanup, then run two separate fresh controls.

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
sys.path.insert(0, str(ROOT/'scripts'))


from run_petclinic_interruption import snapshot, track, survivors, port_open, save


def main():
    if not Path('/proc/self/stat').exists():
        raise RuntimeError('Qualification requires Linux procfs')
    artifact = Path(os.environ['CI_ARTIFACT_DIR'])
    report = {'status': 'incomplete', 'scope': 'RealWorld ordinary controls; one SIGTERM checkpoint',
              'source_commit': os.environ['GITHUB_SHA'], 'primary_freeze_complete': False,
              'deadline_s': {'checkpoint': 180, 'wrapper_exit': 18, 'observed_descendants': 4, 'fresh_controls': 300},
              'timed_selector_calibration': False}
    source_names = ['scripts/ci/run_realworld_interruption.py', 'scripts/ci/run_realworld_supervised.py',
                    'scripts/ci/owned_process_scope.py', 'scripts/run_realworld_paired_controls.py', 'scripts/realworld_paired_case.mjs',
                    'manifests/realworld-paired-controls-v1.json', 'scripts/validate_realworld_paired_controls.py', '.github/workflows/applications.yml',
                    'scripts/ci/run_applications.sh', 'scripts/validate_realworld_interruption.py',
                    'scripts/ci/run_petclinic_interruption.py']
    report['source_sha256'] = {n: hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in source_names}
    save(artifact/'realworld-interruption-plan.json', report)
    child = None
    known = {}
    began = time.monotonic()
    try:
        for stage in ('interrupted', 'fresh', 'repeat'):
            destination = artifact/('realworld-'+stage)
            destination.mkdir(exist_ok=False)
            for name in ('realworld-bootstrap.json', 'runtime-versions.json', 'browser.json'):
                shutil.copyfile(artifact/name, destination/name)
            env = {**os.environ, 'CI_ARTIFACT_DIR': str(destination)}
            with (destination/'wrapper.log').open('x') as log:
                child = subprocess.Popen([sys.executable, str(ROOT/'scripts/ci/run_realworld_supervised.py')],
                                         env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                known = {}
                if stage == 'interrupted':
                    deadline = time.monotonic()+180
                    while True:
                        table = snapshot(); track(table, child.pid, known)
                        observations = list((destination/'realworld-paired-controls').glob('*/*-api-r1.json'))
                        api_pass = False
                        for path in observations:
                            try:
                                raw = json.loads(path.read_text())
                                api_pass |= raw.get('execution_status') == 'completed' and raw.get('observations', {}).get('continuation_outcome') == 'passed'
                            except json.JSONDecodeError:
                                pass
                        live = survivors(table, known)
                        chrome = [p for p in live if 'chrome' in p['command'].lower()]
                        native = [p for p in live if 'realworld_paired_case.mjs' in p['command'] and '--continuation ui' in p['command']]
                        if api_pass and chrome and native and port_open(18765) and port_open(18766):
                            report['checkpoint'] = {'kind': 'API_control_completed_native_adapter_and_browser_alive_both_ports_listening',
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
                    validation = json.loads((destination/'realworld-paired-controls/validation.json').read_text())
                    report[stage+'_control_validation'] = validation
                deadline = time.monotonic()+4
                while True:
                    remaining = survivors(snapshot(), known)
                    if not remaining or time.monotonic() >= deadline:
                        break
                    time.sleep(.05)
                cleanup = json.loads((destination/'realworld-owned-process-cleanup.json').read_text())
                report[stage+'_cleanup'] = {'observed_processes': list(known.values()), 'live_survivors': remaining,
                                             'ports_open': {str(p): port_open(p) for p in (18765, 18766)},
                                             'wrapper_cleanup': cleanup}
                save(artifact/'realworld-interruption-report.json', report)
                if remaining or any(report[stage+'_cleanup']['ports_open'].values()):
                    raise RuntimeError(stage+' cleanup left live observed processes or listeners')
                if not cleanup or not all(p['exit_confirmed'] and not p.get('errors') for p in cleanup.values()):
                    raise RuntimeError('Wrapper cleanup evidence incomplete')
        from validate_realworld_interruption import compare_repeats
        report['repeat_comparison'] = compare_repeats(artifact/'realworld-fresh', artifact/'realworld-repeat')
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
            save(artifact/'realworld-interruption-report.json', report)
            if rescue:
                raise RuntimeError('Emergency cleanup was required; qualification failed')


if __name__ == '__main__':
    with interruption_as_exception():
        main()
