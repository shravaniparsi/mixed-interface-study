"""Verify the two-attempt Gotify closure without treating setup failures as findings."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / 'results/maintained-gotify-controls-v1-ci-44228851199'
DEST = ROOT / 'manifests/maintained-gotify-closure-v1.json'


def reconstruct():
    def read(name):
        return json.loads((ARCHIVE / name).read_text())
    run, build, controls = read('run.json'), read('gotify-build.json'), read('gotify-controls-summary.json')
    assert run['id'] == 44228851199 and run['head_sha'] == 'a7656dba8dc4d38cd0629128c5eb7b0111719473'
    assert run['status'] == 'completed' and run['conclusion'] == 'failure'
    assert build['status'] == 'built' and build['source_revision'] == '01086b95a8b69ee87383f6e8bcae601d8c33384b'
    assert controls['status'] == 'unavailable' and controls['scientific_cases'] == 0
    assert len(controls['arms']) == 1 and controls['arms'][0]['arm'] == 'ui-ui'
    assert {'status': 200} in controls['arms'][0]['readiness']
    assert controls['snapshots'] == []
    native = read('ui-ui/control.json')
    assert native['status'] == 'unavailable' and native['native_mutations'] == []
    assert len(native['mutations']) == 1 and native['mutations'][0]['path'] == '/auth/local/login'
    assert native['mutations'][0]['status'] == 200
    assert "getByRole('link', { name: 'Applications', exact: true })" in native['error']
    assert native['blocked'] == [] and native['page_errors'] == []
    container = read('ui-ui-container.json')
    assert container['Config']['User'] == '1001:1001' and container['State']['ExitCode'] == 0
    first = json.loads((ROOT / 'manifests/maintained-gotify-attempt1-v1.json').read_text())
    original_bases = json.loads((ROOT / 'results/maintained-gotify-controls-v1-ci-44227938136/gotify-base-images.json').read_text())
    assert {k:v['digest'] for k,v in original_bases.items()} == {k:v['digest'] for k,v in read('gotify-base-images.json').items()}
    return {
        'repository': 'gotify/server', 'source_revision': build['source_revision'],
        'status': 'closed_runtime_unqualified', 'ordinary_jobs_used': 2, 'ordinary_jobs_remaining': 0,
        'runs': [first['run_id'], run['id']], 'final_execution_freeze': run['head_sha'],
        'first_attempt': 'Source built; startup failed creating plugins directory.',
        'final_attempt': 'Source built; startup and same-actor authentication succeeded; native navigation selector timed out.',
        'native_ui_rendered': True, 'ordinary_controls_qualified': 0,
        'ordinary_native_adapter_invocations': 1, 'ordinary_application_create_edit_writes': 0,
        'api_application_producers': 0, 'paired_states': 0, 'scientific_cases': 0,
        'interface_incompatibilities_established': 0,
        'interpretation': 'Harness qualification failure; no positive or negative compatibility inference.',
        'screenshot_review': 'Rendered authenticated UI shows APPS, while the frozen locator expected Applications. No locator change or third attempt is permitted.',
        'source_dependency_files_used': 24, 'final_image_id': build['image_id'],
        'build_seconds': build['elapsed_seconds'], 'final_timing': read('timing.json'),
        'combined_reported_run_duration_ms': first['timing']['run_duration_ms'] + read('timing.json')['run_duration_ms'],
        'cost_scope': 'Both retained Actions timing responses report zero billable milliseconds; no total-project invoice claim.',
        'artifact_hashes': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted(ARCHIVE.rglob('*')) if p.is_file()},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--verify', action='store_true'); args = parser.parse_args()
    result = reconstruct()
    if args.verify:
        assert json.loads(DEST.read_text()) == result
    else:
        DEST.write_text(json.dumps(result, indent=2) + '\n')
    print('Gotify closed: two ordinary jobs, zero qualified workflows, zero scientific cases.')
