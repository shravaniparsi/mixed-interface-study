#!/usr/bin/env python3
"""Validate one interruption checkpoint and two independent complete controls."""
import argparse
import hashlib
import json
from pathlib import Path
from validate_realworld_paired_controls import validate, require

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return json.loads(path.read_bytes())


def attempt(stage):
    paths = list((stage/'realworld-paired-controls').glob('*/summary.json'))
    require(len(paths) == 1, 'Expected one preserved attempt per stage')
    return paths[0].parent


def business_state(value):
    # Explicit repeat exclusions: generated references and server wall-clock times.
    # Their within-branch integrity remains required by the ordinary validator.
    if isinstance(value, dict):
        return {k: business_state(v) for k, v in value.items() if k not in {'slug', 'createdAt', 'updatedAt'}}
    if isinstance(value, list):
        return [business_state(v) for v in value]
    return value


def fingerprint(raw):
    return {'candidate': raw['candidate_id'], 'workflow': raw['workflow'],
            'route': [raw['prefix_interface'], raw['continuation_interface']],
            'actor': raw['actor'], 'prefix': business_state(raw['prefix_state']),
            'final': business_state(raw['final_state']),
            'checks': raw['checks'],
            'guards': [(g['stage'], g['name'], g['passed']) for g in raw['integrity']['guards']],
            'outcomes': {k: raw['observations'].get(k) for k in ('prefix_status', 'prefix_outcome', 'continuation_outcome', 'consumer_read_status', 'continuation_write_status')}}


def compare_repeats(first, second):
    require(first.resolve() != second.resolve(), 'Repeat must be a separate attempt')
    left, right = attempt(first), attempt(second)
    validations = [validate(left), validate(right)]
    summaries = [read(p/'summary.json') for p in (left, right)]
    require(summaries[0]['schedule'] == summaries[1]['schedule'], 'Repeat schedule differs')
    require(summaries[0]['source_commit'] == summaries[1]['source_commit'], 'Repeat source differs')
    rows = []
    for a, b in zip(summaries[0]['branches'], summaries[1]['branches']):
        require(a['case_id'] == b['case_id'], 'Repeat branch identity differs')
        require(fingerprint(read(left/a['evidence'])) == fingerprint(read(right/b['evidence'])), 'Repeat business observation differs: '+a['case_id'])
        rows.append(a['case_id'])
    require(len(rows) == 14 and all(v['branches'] == 14 for v in validations), 'Incomplete repeat')
    return {'status': 'matched', 'matched_branches': len(rows), 'case_ids': rows,
            'excluded_fields': ['slug', 'createdAt', 'updatedAt'],
            'scope': 'Two engineering attempts; not independent samples or timing calibration'}


def verify(artifact):
    report = read(artifact/'realworld-interruption-report.json')
    plan = read(artifact/'realworld-interruption-plan.json')
    require(report['status'] == 'qualified_at_declared_checkpoint' and not report['rescue_actions'], 'Qualification failed or required rescue')
    require(report['source_commit'] == plan['source_commit'] and report['source_sha256'] == plan['source_sha256'], 'Plan/source differs')
    for name, digest in plan['source_sha256'].items():
        require(hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest, 'Source differs: '+name)
    event = report['interruption']
    require(event['signal'] == 'SIGTERM' and event['wrapper_returncode'] == 143 and 0 <= event['wrapper_exit_s'] <= 18, 'Invalid interruption result')
    observed = report['checkpoint']['observed_descendants']
    require(any('chrome' in p['command'].lower() for p in observed), 'No observed browser')
    require(any('realworld_paired_case.mjs' in p['command'] and '--continuation ui' in p['command'] for p in observed), 'No observed native adapter')
    interrupted = attempt(artifact/'realworld-interrupted')
    require(any(read(p).get('execution_status') == 'completed' and read(p)['observations'].get('continuation_outcome') == 'passed' for p in interrupted.glob('*-api-r1.json')), 'No completed API checkpoint evidence')
    for stage in ('interrupted', 'fresh', 'repeat'):
        cleanup = report[stage+'_cleanup']
        require(cleanup['observed_processes'] and not cleanup['live_survivors'] and cleanup['ports_open'] == {'18765': False, '18766': False}, 'Cleanup incomplete: '+stage)
        require(set(cleanup['wrapper_cleanup']) == {'runner'}, 'Missing owned runner evidence')
        require(all(r['exit_confirmed'] and not r['errors'] for r in cleanup['wrapper_cleanup'].values()), 'Owned cleanup failed')
        require(cleanup['wrapper_cleanup'] == read(artifact/('realworld-'+stage)/'realworld-owned-process-cleanup.json'), 'Cleanup sidecar differs')
        if stage != 'interrupted':
            require(validate(attempt(artifact/('realworld-'+stage))) == report[stage+'_control_validation'] == read(artifact/('realworld-'+stage)/'realworld-paired-controls/validation.json'), 'Control validation differs')
    comparison = compare_repeats(artifact/'realworld-fresh', artifact/'realworld-repeat')
    require(comparison == report['repeat_comparison'], 'Repeat comparison differs')
    return {'status': 'verified', 'source_commit': report['source_commit'], 'wrapper_exit_s': event['wrapper_exit_s'], 'complete_branches': 28, 'matched_repeat_branches': 14, 'rescue_actions': 0, 'primary_freeze_complete': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('artifact', type=Path); args = parser.parse_args()
    result = verify(args.artifact)
    (args.artifact/'realworld-interruption-verification.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
