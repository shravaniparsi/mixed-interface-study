#!/usr/bin/env python3
"""Verify retained ordinary evidence; never infer success from CI colour alone."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('evidence', type=Path)
    args = parser.parse_args()
    root = args.evidence
    load = lambda name: json.loads((root / name).read_text())
    qualification = load('qualification.json')
    assert qualification['status'] == 'ordinary_qualification_passed'
    assert qualification['scientific_cases'] == 0
    assert qualification['phases'] == ['producer', 'warm', 'seed', 'native', 'api']
    assert load('build-exit.json')['exit_code'] == load('runtime-exit.json')['exit_code'] == 0
    before_checkout, after_checkout = load('checkout.json'), load('checkout-after-build.json')
    assert before_checkout == after_checkout
    assert before_checkout['revision'] == '3833c3ae5714f164dd6870f4d28865e78d60a4cc'
    assert before_checkout['clean_checkout'] is True
    assert len(before_checkout['verified_previously_acquired_blobs']) == 67
    lock = (root / 'original-frontend-package-lock.json').read_bytes()
    assert hashlib.sha256(lock).hexdigest() == before_checkout['build_inputs']['mathesar_ui/package-lock.json']['sha256']
    image = load('application-image-inspect.json')[0]
    assert image['Id'] == (root / 'application-image-id.txt').read_text().strip()
    assert image['Architecture'] == 'amd64' and image['Os'] == 'linux'
    phases = {}
    for name in ['producer', 'warm', 'seed', 'native', 'api']:
        phase = load(name + '-browser.json')
        assert phase['phase'] == name and phase['status'] == 'ordinary_phase_passed'
        assert phase['external_requests'] == phase['page_errors'] == []
        assert phase['browser_version'] == '151.0.7922.34'
        assert phase['executable_sha256'] == '0b20b130e7edd9dd51873be867761295fe0cfad490c2b9a64f95bd3cfc08fa71'
        settings = json.loads((root / (name + '-settings.log')).read_text().strip())
        assert settings == {'test': False, 'per_user_databases': False,
                            'analytics_enabled': False, 'installation_ids': 0}
        assert load(name + '-browser-process-exit.json')['exit_code'] == 0
        phases[name] = phase
    ordinary = {'username': 'studycontrol', 'full_name': 'Study Control',
                'email': 'studycontrol@example.com', 'display_language': 'en', 'is_superuser': False}
    target = phases['seed']['producer']['target']
    assert isinstance(target['id'], int) and not isinstance(target['id'], bool) and target['id'] > 0
    assert target == {**ordinary, 'id': target['id']}
    for name in ['producer', 'warm', 'seed']:
        assert phases[name]['bootstrap']['telemetry_flags_submitted'] is False
        actor = phases[name]['bootstrap']['actor']
        assert actor['username'] == 'studyadmin' and actor['is_superuser'] is True
        assert actor['id'] != target['id']
        assert phases[name]['producer']['target'] == target
    native_producer = phases['producer']['producer']
    assert native_producer['complete_request_match'] is True
    captured = native_producer['emitted_request']
    assert captured['method'] == 'users.add' and captured['id'] == 0 and captured['jsonrpc'] == '2.0'
    assert set(captured['params']) == {'user_def'}
    definition = dict(captured['params']['user_def'])
    password = definition.pop('password')
    assert len(password['private_value_sha256']) == 64 and password['utf8_bytes'] > 16
    assert definition == ordinary
    expected_request = {'jsonrpc': '2.0', 'id': 0, 'method': 'users.patch_other',
                        'params': {**ordinary, 'full_name': 'Study Edited', 'user_id': target['id']}}
    for name in ['warm', 'native', 'api']:
        continuation = phases[name]['continuation']
        assert continuation['before'] == target
        assert continuation['after'] == {**target, 'full_name': 'Study Edited'}
        assert continuation['request'] == expected_request and continuation['status'] == 200
        if name != 'api':
            assert continuation['emitted_request'] == expected_request
            assert continuation['complete_request_match'] is True
            assert continuation['actionability'] == {'visible': True, 'enabled': True, 'clicked': True}
    assert native_producer['actionability'] == {'visible': True, 'enabled': True, 'clicked': True}
    assert phases['native']['continuation']['actor'] == phases['api']['continuation']['actor']
    assert phases['native']['restored_storage_sha256'] == phases['api']['restored_storage_sha256']
    seed = load('seed-state.json')
    assert seed['status'] == 'checkpoint_captured'
    assert seed['state']['tables'] and seed['state']['sequences']
    for name in ['native', 'api']:
        state = load(name + '-before-state.json')
        assert state['status'] == 'restore_matches'
        assert state['dump_sha256'] == seed['dump_sha256']
        assert state['state'] == seed['state']
    native_after, api_after = load('native-after-state.json'), load('api-after-state.json')
    assert native_after['status'] == api_after['status'] == 'state_inspected'
    assert native_after['state'] == api_after['state']
    print(json.dumps({'status': 'retained_ordinary_evidence_verified', 'scientific_cases': 0,
                      'fresh_full_state_equivalence_claimed': False}))


if __name__ == '__main__':
    main()
