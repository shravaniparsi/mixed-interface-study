#!/usr/bin/env python3
"""Freeze and verify the prospective twenty-two-branch execution integrity controls."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil

from summarize_realworld_oracle_components import summarize_run, capture_integrity_issues, execution_integrity_issues

ROOT = Path(__file__).resolve().parents[1]
SELECTION = json.loads((ROOT / 'manifests/realworld-integrity-controls-v1.json').read_text())
LEGACY_IDS = SELECTION['legacy_candidate_ids']
SOURCES = ['scripts/realworld_integrity.mjs', 'scripts/response_capture.mjs', 'scripts/realworld_generated_case.mjs',
           'scripts/realworld_boundary_case.mjs', 'scripts/run_generated_integration.py',
           'scripts/run_realworld_boundaries.py', 'scripts/realworld_case_worker.py',
           'scripts/run_realworld_pilot.py', 'scripts/validate_realworld_integrity.py',
           'scripts/summarize_realworld_oracle_components.py', 'scripts/ci/run_applications.sh',
           '.github/workflows/applications.yml', 'protocol/realworld-integrity-validation-v1.md',
           'protocol/runtime-integration-v1.md',
           'manifests/realworld-article-generated-pool-v1.json', 'manifests/realworld-boundary-registry-v1.json']
SOURCES += ['manifests/realworld-integrity-controls-v1.json']
SOURCES += sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'src/mixed_interface').glob('*.py'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def save_new(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def expected_ids():
    registry = load(ROOT / 'manifests/realworld-boundary-registry-v1.json')
    selected = [c for c in registry['cases'] if c['candidate_id'] in LEGACY_IDS]
    legacy = [f"{c['candidate_id']}-{branch}-r1" for c in selected for branch in c['continuations']]
    generated = [c['case_id'] for c in load(ROOT / 'manifests/realworld-article-generated-pool-v1.json')['cases']
                 if c['case_id'] in {x['case_id'] for x in SELECTION['generated_cases']}]
    if legacy != [x['case_id'] for x in SELECTION['legacy_branches']] or len(legacy) != 16:
        raise ValueError('Legacy integrity selection changed')
    if generated != [x['case_id'] for x in SELECTION['generated_cases']] or len(generated) != 6:
        raise ValueError('Generated integrity selection changed')
    return {'legacy': legacy, 'generated': generated}


def validate_case_capture(result, case_id):
    issues = capture_integrity_issues(result, required=True) + execution_integrity_issues(result, required=True)
    if issues:
        raise ValueError('Incomplete capture/integrity: ' + ','.join(issues))
    declared = next(c for c in SELECTION['legacy_branches'] + SELECTION['generated_cases'] if c['case_id'] == case_id)
    obs = result if 'application_outcome' in result else result['observations']
    if obs.get('prefix_status') != declared['expected_prefix_status']:
        raise ValueError('Prefix status differs from declared control: ' + case_id)
    checks = result.get('checks', [])
    if any(c.get('passed') is not True for c in checks):
        raise ValueError('Control business check failed')
    outcome = result.get('application_outcome', obs.get('continuation_outcome'))
    if declared['outcome'] == 'accept':
        if not checks or outcome != 'passed':
            raise ValueError('Positive control did not pass')
    else:
        if outcome not in ('prefix_rejected', 'not_executed_prefix_unsuccessful'):
            raise ValueError('Rejection control executed an unexpected continuation')
        if result['integrity']['rejection']['status'] != 'unchanged':
            raise ValueError('Rejected request did not preserve readable observable state')
        if any(g['stage'] == 'continuation' for g in result['integrity']['guards']):
            raise ValueError('Continuation guard present after rejection')
        if obs.get('ui_continuation_started') or obs.get('api_continuation_started'):
            raise ValueError('Continuation started after rejection')
    return {'contexts': len(result['capture_integrity']['contexts']),
            'requests': sum(c['admitted'] for c in result['capture_integrity']['contexts']),
            'business_checks': len(checks), 'integrity_guards': len(result['integrity']['guards']),
            'declared_outcome': declared['outcome']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--artifact-root', type=Path, required=True)
    parser.add_argument('--generated-root', type=Path, required=True)
    args = parser.parse_args()
    artifact = args.artifact_root.resolve()
    plan_path = artifact / 'integrity-validation-plan.json'
    expected = expected_ids()
    if args.prepare:
        if list(args.generated_root.glob('*/evidence/summary.json')) or list((artifact / 'realworld-legacy-controls').glob('*/summary.json')):
            raise ValueError('Existing run evidence: no resume or cross-attempt merging')
        snapshot = artifact / 'integrity-validation-sources'
        snapshot.mkdir(exist_ok=False)
        for name in SOURCES:
            dest = snapshot / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        plan = {'kind': 'realworld_integrity_control_plan', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'source_commit': os.environ.get('GITHUB_SHA'), 'expected_case_ids': expected,
                'source_sha256': {name: sha(ROOT / name) for name in SOURCES},
                'sidecar_sha256': {name: sha(artifact / name) for name in ['runtime-versions.json', 'browser.json', 'realworld-bootstrap.json']},
                'runtime_root': os.environ.get('STUDY_RUNTIME'), 'generated_root': str(args.generated_root.resolve()),
                'node': shutil.which('node'), 'python': shutil.which('python'),
                'case_scope': 'fourteen positive and eight previously examined rejection branches',
                'execution_order': ['generated', 'legacy'], 'generated_phase': 'integrity-controls',
                'legacy_candidate_ids': LEGACY_IDS, 'repetitions': 1,
                'outer_timeout_s': {'generated': 180, 'legacy': 240}, 'outer_kill_grace_s': 20,
                'capture_drain_timeout_ms': 5000, 'primary_freeze_complete': False,
                'repeat_policy': 'No automatic retry, resume, partial replacement or cross-attempt merge.'}
        save_new(plan_path, plan)
        print('Saved integrity-control plan before application dispatch.')
        return
    plan = load(plan_path)
    if plan['expected_case_ids'] != expected or set(plan['source_sha256']) != set(SOURCES):
        raise ValueError('Pre-dispatch source/control inventory changed')
    for name, digest in plan['source_sha256'].items():
        if sha(ROOT / name) != digest or sha(artifact / 'integrity-validation-sources' / name) != digest:
            raise ValueError('Source differs from saved plan: ' + name)
    for name, digest in plan['sidecar_sha256'].items():
        if sha(artifact / name) != digest:
            raise ValueError('Environment sidecar changed: ' + name)
    locations = {'generated': list(args.generated_root.glob('*/evidence/summary.json')),
                 'legacy': list((artifact / 'realworld-legacy-controls').glob('*/summary.json'))}
    results = {}
    for family, paths in locations.items():
        if len(paths) != 1:
            raise ValueError('Exactly one complete attempt required for ' + family)
        directory = paths[0].parent
        summary = load(paths[0])
        reduced = summarize_run(directory)
        entries = summary['validation' if family == 'generated' else 'branches']
        if [e['case_id'] for e in entries] != expected[family] or reduced['status'] != 'complete_observations':
            raise ValueError('Control ordering, completeness or source-qualified extraction failed: ' + family)
        if family == 'generated' and (summary.get('phase') != 'integrity-controls' or summary['calibration'] or summary['sessions']):
            raise ValueError('Generated execution exceeded controls-only scope')
        if family == 'legacy' and (summary.get('candidate_subset') != LEGACY_IDS or summary['repetitions_per_branch'] != 1):
            raise ValueError('Legacy execution exceeded declared control scope')
        for name, digest in summary['source_sha256'].items():
            matches = [value for path, value in plan['source_sha256'].items()
                       if path in ('scripts/' + name, 'src/mixed_interface/' + name, 'protocol/' + name)]
            if len(matches) != 1 or digest != matches[0]:
                raise ValueError('Executed source differs from pre-dispatch plan: ' + name)
        counts = []
        for entry in entries:
            path = (directory / entry['details']['evidence'] / 'observation.json') if family == 'generated' else (directory / entry['evidence'])
            counts.append({'case_id': entry['case_id'], 'observation_sha256': sha(path), **validate_case_capture(load(path), entry['case_id'])})
        save_new(artifact / (family + '-integrity-components.json'), reduced)
        results[family] = {'summary_path': str(paths[0]), 'summary_sha256': sha(paths[0]),
                           'qualified_cases': reduced['case_count'], 'cases': counts}
    save_new(artifact / 'integrity-validation-summary.json', {
        'status': 'passed', 'kind': 'realworld_integrity_control_validation',
        'plan_sha256': sha(plan_path), 'finished_at_utc': datetime.now(timezone.utc).isoformat(),
        'families': results, 'case_count': 22, 'capture_errors': 0,
        'new_boundary_cases_executed': 0, 'primary_freeze_complete': False,
        'legacy_owned_process_cleanup_qualification': False,
        'method_effectiveness_evidence': False})
    print('Twenty-two source-qualified integrity control branches passed.')


if __name__ == '__main__':
    main()
