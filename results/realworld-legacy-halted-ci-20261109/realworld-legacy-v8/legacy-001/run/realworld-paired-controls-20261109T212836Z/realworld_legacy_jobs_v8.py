"""Exact exposed legacy jobs; native singleton results never enter paired statistics.

This module binds jobs and loads evidence. It is not a primary campaign or a
qualification certificate. The mixed-cardinality campaign supervisor is pending.
"""
from copy import deepcopy
from pathlib import Path
from realworld_terminal_campaign import ROOT, read, sha, reducer
from mixed_interface.repetition import digest, require
from realworld_legacy_terminal_v8 import classify_branch
from realworld_rejection_outcomes import pair_result

SOURCE = 'manifests/realworld-boundary-registry-v1.json'
SOURCE_SHA = 'dee2fee441d71283eddd68e1c5b23396d95d7a8c184d0e24468a1c5f7e1deab2'
IDS = ('article-valid', 'article-update-unique-partial', 'article-title-150',
       'article-title-151', 'article-title-whitespace',
       'article-update-duplicate-partial', 'article-update-duplicate-full',
       'comment-native-control', 'profile-native-control')
REFERENCES = {'article-create-edit': 'article-valid',
              'article-update-comment': 'article-update-unique-partial'}
SOURCES = {'run_realworld_legacy_job_v8.py', 'realworld_legacy_jobs_v8.py',
           'realworld_legacy_reducer_v8.py', 'realworld_legacy_terminal_v8.py',
           'realworld_paired_case.mjs', 'run_realworld_pilot.py',
           'response_capture.mjs', 'realworld_integrity.mjs', 'phase_clock.mjs',
           'realworld_normalization.mjs', 'validate_realworld_paired_controls.py',
           'summarize_realworld_oracle_components.py', 'normalization.py'}


def selection():
    require(sha(ROOT / SOURCE) == SOURCE_SHA, 'Legacy registry source changed')
    original = read(ROOT / SOURCE)
    by_id = {c['candidate_id']: c for c in original['cases']}
    return {'schema_version': 1, 'kind': 'exposed_legacy_job_selection_v8',
            'source': SOURCE, 'source_sha256': SOURCE_SHA,
            'primary_freeze_complete': False,
            'cases': [deepcopy(by_id[cid]) for cid in IDS]}


def plan_for(registry):
    require(registry == selection(), 'Selection differs from retained source cases')
    jobs = []
    for i, spec in enumerate(registry['cases']):
        cid = spec['candidate_id']; singleton = spec['continuations'] == ['ui']
        order = ['ui'] if singleton else ['api', 'ui'] if i % 2 == 0 else ['ui', 'api']
        jobs.append({'job_id': f'legacy-{i:03d}', 'candidate_id': cid,
                     'entry_kind': 'singleton' if singleton else 'pair',
                     'source_case_sha256': digest(spec), 'repetition': 1,
                     'reference_control': None if singleton else REFERENCES[spec['workflow']],
                     'branches': [{'case_id': f'{cid}-{c}-r1', 'continuation': c,
                                   'fresh_reset_required': True} for c in order]})
    return {'kind': 'exposed_legacy_initial_jobs_v8', 'jobs': jobs,
            'counts': {'retained_pairs': 5, 'paired_references': 2,
                       'native_singletons': 2, 'branch_slots': 16},
            'primary_freeze_complete': False, 'campaign_dispatch_qualified': False,
            'automatic_repeats': False}


def validate_job(job, registry):
    require(job in plan_for(registry)['jobs'], 'Foreign or altered legacy job')
    return next(c for c in registry['cases'] if c['candidate_id'] == job['candidate_id'])


def extract(job, branches, spec, fixture, fixture_sha, cleanup, evidence):
    require(spec == validate_job(job, selection()), 'Extracted case differs from job')
    require(set(branches) == {b['continuation'] for b in job['branches']},
            'Missing or fabricated branch')
    if job['entry_kind'] == 'pair':
        return {'entry_kind': 'pair', **pair_result(job, branches, spec, fixture,
                                                   fixture_sha, cleanup, evidence)}
    require(spec['prefix_interface'] == 'ui' and spec['continuations'] == ['ui'],
            'Singleton route differs')
    raw, run = branches['ui']
    value = classify_branch(raw, run, spec, fixture=fixture, cleanup_confirmed=cleanup)
    # No fake absent API branch, no paired envelope, no discrepancy boolean.
    return {'entry_kind': 'singleton', 'job_id': job['job_id'], 'branch': value,
            'channel_discrepancy': None, 'paired_comparison_eligible': False,
            'evidence_sha256': evidence, 'primary_freeze_complete': False}


def read_job(directory, job, registry, execution):
    directory = Path(directory); spec = validate_job(job, registry)
    require(execution.get('exit_confirmed') is True and not execution.get('errors')
            and execution.get('returncode') == 0, 'Runner exit not clean')
    paths = list((directory / 'run').glob('*/summary.json'))
    require(len(paths) == 1, 'Expected one summary')
    path = paths[0]; root = path.parent; summary = read(path)
    require(summary['job'] == job and summary['job_sha256'] == sha(directory / 'job.json'),
            'Executed job differs')
    require(read(root / 'registered-candidates.json') == registry and
            summary['registry_sha256'] == sha(root / 'registered-candidates.json'), 'Registry differs')
    require(summary['status'] == 'completed' and summary['frontend_exit_confirmed'] is True,
            'Incomplete job')
    require(summary['schedule'] == [{'candidate_id': spec['candidate_id'],
            'order': [b['continuation'] for b in job['branches']]}], 'Declared order differs')
    require([b['case_id'] for b in summary['branches']] ==
            [b['case_id'] for b in job['branches']], 'Branch inventory differs')
    require(set(summary['source_sha256']) == SOURCES, 'Source inventory differs')
    for name, h in summary['source_sha256'].items():
        live = ROOT / ('src/mixed_interface/normalization.py' if name == 'normalization.py' else 'scripts/' + name)
        require(sha(root / name) == h == sha(live), 'Executed source differs: ' + name)
    source = read(ROOT / SOURCE)
    require(summary['backend_commit'] == source['backend_commit'] and
            summary['frontend_commit'] == source['frontend_commit'], 'Application revision differs')
    fixture = read(root / 'fixture-references.json'); branches = {}
    evidence = {'summary': sha(path), 'job': sha(directory / 'job.json'),
                'execution': sha(directory / 'execution.json')}
    for declared, branch in zip(job['branches'], summary['branches']):
        require(branch['continuation'] == declared['continuation'] and
                branch['candidate_id'] == spec['candidate_id'] and
                branch['evidence'] == declared['case_id'] + '.json', 'Branch binding differs')
        require(branch['reset_sha256'] == summary['fixture_sha256'], 'Reset differs')
        raw = read(root / branch['evidence']); reducer.validate_timing(raw, branch)
        branches[branch['continuation']] = (raw, branch)
        evidence[branch['evidence']] = sha(root / branch['evidence'])
    return extract(job, branches, spec, fixture, summary['fixture_sha256'], True, evidence)
