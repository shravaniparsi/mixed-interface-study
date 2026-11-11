#!/usr/bin/env python3
"""Run pinned upstream scoring on a disclosed, disposable file-based fixture.

Actual upstream mutation, subprocess test execution and evaluation; no REST service.
This is a source-informed harness qualification probe, not benchmark replication.
"""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import platform
import shlex
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / 'evidence/restestbench-source-v1'


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Preserve previous observations; choose a new path.'
    pins = json.loads((ROOT / 'manifests/restestbench-source-pins-v1.json').read_text())
    for row in pins['files']:
        data = (UPSTREAM / row['path']).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == row['git_blob']
    sys.path.insert(0, str(UPSTREAM))
    from src.executor import TestExecutor
    from src.evaluator import Evaluator
    from src.generator import GeneratedTest, GenerationMode
    from src.mutator import Mutator, Mutant, Requirement
    import src.executor
    import requests
    assert Path(src.executor.__file__).resolve() == UPSTREAM / 'src/executor.py'

    class Tool:
        def get_test_command(self, path):
            return shlex.quote(sys.executable) + ' ' + shlex.quote(path)

    class DiskFixture:
        """No service process: reset a file, use upstream Mutator, record calls."""
        def __init__(self, folder):
            self.folder = folder; self.application_results = []
        def reset_working_copy(self, service):
            (self.folder / 'value.py').write_text('value = 1\n')
        def wait_for_service_health(self, service, port):
            pass  # explicitly inapplicable: this is a file fixture, not a REST host
        def call_reset_script(self, service, port):
            pass
        def apply_mutation(self, service, mutant):
            result = Mutator(self.folder).apply_mutation(mutant)
            self.application_results.append(result)
            return result

    definitions = [
        ('changed_value', 'value = 1', 'value = 2', 1),
        ('unapplied_mutation', 'value = 99', 'value = 2', 1),
        ('equivalent_comment', 'value = 1', 'value = 1 # equivalent', 1),
        ('invalid_test_control', 'value = 1', 'value = 2', 2),
    ]
    observations = []
    for name, original, mutated, expected in definitions:
        with tempfile.TemporaryDirectory(prefix='restestbench-probe-') as directory:
            folder = Path(directory); test_file = folder / 'test_fixture.py'
            test_code = ("from pathlib import Path\n"
                         "with Path('executed.txt').open('a') as f: f.write('executed\\n')\n"
                         "values = {}\nexec(Path('value.py').read_text(), values)\n"
                         f"assert values['value'] == {expected}\n")
            test_file.write_text(test_code)
            fixture = DiskFixture(folder)
            test = GeneratedTest(1, 'synthetic_file_fixture', GenerationMode.VALID, None, test_file, test_code)
            requirement = Requirement(1, 'synthetic_file_fixture', 'fixture', 'fixture', [Mutant('value.py', original, mutated)])
            log = io.StringIO()
            with contextlib.redirect_stdout(log):
                results = TestExecutor(Tool(), fixture).execute_full(test, requirement)
            score = Evaluator().evaluate_test(results, 1)
            observations.append({'case': name, 'mutant': {'original': original, 'mutated': mutated},
                                 'application_results': fixture.application_results,
                                 'actual_test_process_executions': len((folder / 'executed.txt').read_text().splitlines()),
                                 'results': [r.to_dict(folder) for r in results],
                                 'score': score.to_dict(), 'executor_log': log.getvalue()})
    report = {'kind': 'restestbench_scoring_qualification_probe_v1', 'upstream_commit': pins['commit'],
              'python': platform.python_version(), 'requests_version': requests.__version__,
              'scope': 'Synthetic file fixture; real upstream Mutator, TestExecutor and Evaluator. No REST application, Docker, model call or benchmark paper result reproduced.',
              'observations': observations,
              'source_sha256': {str((UPSTREAM / r['path']).relative_to(ROOT)): hashlib.sha256((UPSTREAM / r['path']).read_bytes()).hexdigest() for r in pins['files']},
              'instrument_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps([{'case': r['case'], 'applied': r['application_results'], 'test_executions': r['actual_test_process_executions'], 'score': r['score']['score']} for r in observations]))


if __name__ == '__main__': main()
