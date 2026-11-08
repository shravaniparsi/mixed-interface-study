#!/usr/bin/env python3
"""Own one complete RealWorld control attempt without changing its adapter."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from owned_process_scope import interruption_as_exception, defer_stop_signals, stop_owned_group

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from validate_realworld_paired_controls import validate


def main():
    artifact = Path(os.environ['CI_ARTIFACT_DIR'])
    runtime = Path(os.environ['STUDY_RUNTIME'])
    execution = runtime/'realworld-execution'
    execution.mkdir(exist_ok=True)
    output = artifact/'realworld-paired-controls'
    output.mkdir(exist_ok=False)
    command = [sys.executable, str(ROOT/'scripts/run_realworld_paired_controls.py'),
               '--subject', str(runtime/'realworld/realworld-django-ninja'),
               '--python', str(runtime/'realworld/venv/bin/python'), '--node', shutil.which('node'),
               '--runtime-root', str(execution), '--registry', str(ROOT/'manifests/realworld-paired-controls-v1.json'),
               '--output-root', str(output)]
    child = None
    cleanup = {}
    with interruption_as_exception():
        try:
            child = subprocess.Popen(command, start_new_session=True)
            if child.wait(timeout=180) != 0:
                raise RuntimeError('Control attempt failed; preserve all evidence')
            summaries = list(output.glob('*/summary.json'))
            if len(summaries) != 1:
                raise RuntimeError('Expected exactly one attempt')
            result = validate(summaries[0].parent)
            (output/'validation.json').write_text(json.dumps(result, indent=2)+'\n')
        finally:
            with defer_stop_signals():
                if child is not None:
                    cleanup['runner'] = stop_owned_group(child)
                (artifact/'realworld-owned-process-cleanup.json').write_text(json.dumps(cleanup, indent=2)+'\n')
    if not cleanup or any(not r['exit_confirmed'] or r['errors'] for r in cleanup.values()):
        raise RuntimeError('Owned process cleanup failed')


if __name__ == '__main__':
    main()
