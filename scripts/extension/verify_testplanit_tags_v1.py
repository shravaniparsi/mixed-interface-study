#!/usr/bin/env python3
"""Reconstruct TestPlanIt observations; keep setup failures and partial data distinct."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import jsonschema

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from mixed_interface.write_frame import evaluate


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(archive):
    registration_path = ROOT / 'manifests/testplanit-tags-calibration-v1.json'
    registration = read(registration_path)
    for name, expected in registration['artifact_sha256'].items():
        assert sha(ROOT / name) == expected, name
    scores = []
    for path in sorted(archive.rglob('*-observation.json')):
        observation = read(path)
        version, case = observation['version'], observation['kind']
        assert version in registration['versions'] and case in registration['cases']
        before = read(path.with_name(case + '-before.json'))
        after = read(path.with_name(case + '-after.json'))
        assert len(before['row']) == len(after['row']) == 1
        b, a = before['row'][0], after['row'][0]
        assert b['id'] == a['id'] == observation['args']['caseId']
        assert b['currentVersion'] == 1 and len(before['tags']) == 1
        assert not before['versions']
        b_tags = sorted(t['tagId'] for t in before['tags'])
        a_tags = sorted(t['tagId'] for t in after['tags'])
        schema = [t['inputSchema'] for t in read(path.parent / 'tools.json')['tools']
                  if t['name'] == 'testplanit_cases_update']
        assert len(schema) == 1
        errors = sorted(e.message for e in jsonschema.Draft202012Validator(schema[0]).iter_errors(observation['args']))
        assignments = ({'name': observation['args']['name']} if case == 'omit'
                       else {'tag_ids': sorted(observation['args']['tags'])})
        expected_tags = b_tags if case == 'omit' else sorted(observation['args']['tags'])
        baseline = evaluate(dict(b, tag_ids=b_tags), dict(a, tag_ids=a_tags), assignments, ['currentVersion'])
        result = observation['result']
        success = not result.get('isError', False) and 'transportError' not in result
        readback = observation['readback']
        readback_available = isinstance(readback, dict) and 'error' not in readback and 'caseTags' in readback
        readback_tags = sorted(t['tagId'] for t in readback['caseTags']) if readback_available else None
        # Snapshot tag names are joined to the independent tag-ID expectation
        # through the fixed synthetic fixture names, not through tool output.
        if case == 'replace':
            expected_names = ['study-contract-B']
        elif case == 'clear':
            expected_names = []
        else:
            expected_names = ['study-contract-A']
        versions = after['versions']
        version_agreement = (len(versions) == 1 and versions[0]['version'] == 2
                             and sorted(versions[0]['tags']) == expected_names)
        scores.append({
            'version': version, 'case': case, 'schema_valid': not errors, 'schema_errors': errors,
            'operation_success': success, 'requested_postcondition': not baseline['failed_assignments'],
            'tag_contract_passes': a_tags == expected_tags,
            'frame_violations': baseline['frame_violations'],
            'version_increment_passes': a['currentVersion'] == 2,
            'snapshot_agreement_passes': version_agreement,
            'fresh_api_readback_available': readback_available,
            'fresh_api_tag_agreement': readback_available and readback_tags == a_tags,
            'http_statuses': [r.get('status') for r in observation['trace']],
            'source': str(path.relative_to(ROOT)),
        })
    assert len({(s['version'], s['case']) for s in scores}) == len(scores)
    complete = len(scores) == registration['planned_executions']
    controls = [s for s in scores if s['case'] in ('omit', 'clear')]
    controls_pass = len(controls) == 4 and all(
        s['schema_valid'] and s['operation_success'] and s['tag_contract_passes']
        and not s['frame_violations'] and s['snapshot_agreement_passes']
        and s['fresh_api_tag_agreement'] and s['version_increment_passes'] for s in controls)
    return {
        'kind': 'testplanit_tags_reconstruction_v1', 'observations': len(scores),
        'planned_executions': registration['planned_executions'],
        'complete_observation_set': complete, 'omit_and_clear_controls_pass': controls_pass,
        'status': 'observed_requires_interpretation' if complete else 'incomplete_or_setup_failure',
        'new_defects_claimed': 0, 'independent_mechanisms_counted': 0,
        'scores': scores,
        'registration_sha256': sha(registration_path),
        'implementation_sha256': sha(Path(__file__).resolve()),
        'raw_sha256': {str(p.relative_to(ROOT)): sha(p) for p in sorted(archive.rglob('*')) if p.is_file()},
        'limits': ['Historical issue-selected data; no unseen efficacy or prevalence.',
                   'A requested-postcondition baseline can detect requested tag loss.',
                   'Scientific qualification and causal attribution require reviewing controls, HTTP traces and run metadata.',
                   'No observations means no scientific executions, not zero defects in eight tested cases.'],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    value = build(args.archive.resolve())
    if args.verify:
        assert read(args.verify) == value
    elif args.output:
        args.output.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: v for k, v in value.items() if k not in ('scores', 'raw_sha256', 'limits')}))


if __name__ == '__main__':
    main()
