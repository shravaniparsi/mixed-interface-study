"""Reconstruct the first Gotify qualification outcome from retained evidence."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / 'results/maintained-gotify-controls-v1-ci-44227938136'
DEST = ROOT / 'manifests/maintained-gotify-attempt1-v1.json'


def reconstruct():
    def read(name):
        return json.loads((ARCHIVE / name).read_text())
    run, build, controls = read('run.json'), read('gotify-build.json'), read('gotify-controls-summary.json')
    assert run['id'] == 44227938136
    assert run['head_sha'] == '8ee7020d7d231c2d04ba20a04c19f51066a34811'
    assert run['status'] == 'completed' and run['conclusion'] == 'failure'
    assert build['status'] == 'built' and build['source_revision'] == '01086b95a8b69ee87383f6e8bcae601d8c33384b'
    assert controls['status'] == 'unavailable' and controls['scientific_cases'] == 0
    assert len(controls['arms']) == 1 and controls['arms'][0]['arm'] == 'ui-ui'
    assert not (ARCHIVE / 'ui-ui/control.json').exists()
    assert controls['snapshots'] == []
    container = read('final-inspect.txt')[0]
    assert container['State']['ExitCode'] == 1 and container['HostConfig']['CapDrop'] == ['ALL']
    logs = (ARCHIVE / 'final-logs.txt').read_text()
    assert 'Cannot create plugins directory' in logs and 'permission denied' in logs
    return {
        'run_id': run['id'], 'freeze': run['head_sha'], 'status': 'initialization_unavailable',
        'source_build': 'succeeded', 'build_seconds': build['elapsed_seconds'], 'image_id': build['image_id'],
        'native_ui_delivery_verified': False, 'ordinary_browser_controls_executed': 0,
        'api_producers_executed': 0, 'scientific_cases': 0, 'paired_states': 0,
        'observed_failure': 'Application exited while creating data/plugins: permission denied.',
        'interpretation': 'Runtime setup failure; no interface-compatibility observation.',
        'remaining_ordinary_jobs': 1, 'timing': read('timing.json'),
        'cost_limit': 'GitHub reported timing only; zero reported billable milliseconds is not a total-project invoice.',
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
    print('First attempt: source built; initialization unavailable; zero executed controls/variants.')
