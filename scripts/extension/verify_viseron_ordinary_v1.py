#!/usr/bin/env python3
"""Reconstruct ordinary qualification from retained public evidence."""
import argparse
import hashlib
import json
from pathlib import Path
from qualify_viseron_ordinary_v1 import canonical_files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('evidence', type=Path)
    args = parser.parse_args()
    root = args.evidence
    load = lambda name: json.loads((root / name).read_text())
    q = load('qualification.json')
    assert q['status'] == 'ordinary_qualification_passed'
    assert q['phases'] == ['producer', 'warm', 'seed', 'native', 'api']
    assert q['scientific_cases'] == 0
    assert load('runtime-exit.json')['exit_code'] == 0
    package = load('packaged-source.json')
    assert package['status'] == 'packaged_source_checks_passed_pending_native_controls'
    assert package['declared_revision'] == '3d77e324d8316033f30acb83058736aa7e468d81'
    assert package['frontend_source_byte_equivalence_claimed'] is False
    assert package['packaged_sources'] and package['frontend_assets']
    for row in package['packaged_sources']:
        assert row['actual_sha256'] == row['expected_sha256']
    for index, image_id in enumerate([
        'sha256:e7b2904341af931c754f815f865c799b0a0ee0a86f5aeff091de57d063e417e7',
        'sha256:fee853fafa59550d162cef52bca02d907694b44ebf6ef9fb075bcc0c65d8dedb']):
        image = load(f'image-{index}-inspect.json')[0]
        assert image['Id'] == image_id and image['Architecture'] == 'amd64' and image['Os'] == 'linux'
    schema = load('ordinary-schema.json')
    assert schema['status'] == 'evaluated' and schema['accepted'] is True
    assert schema['validated_body_equals_input'] is True and schema['mutation_called'] is False
    assert schema['request_sha256'] == hashlib.sha256((root / 'ordinary-schema-input.json').read_bytes()).hexdigest()
    assert schema['validator_version'] == '0.16.0'
    phases = {}
    for phase in q['phases']:
        p = load(phase + '-browser.json')
        assert p['phase'] == phase and p['status'] == 'ordinary_phase_passed'
        assert p['page_errors'] == [] and p['token_refreshes'] == 0
        assert p['browser_version'] == '151.0.7922.34'
        assert p['executable_sha256'] == '0b20b130e7edd9dd51873be867761295fe0cfad490c2b9a64f95bd3cfc08fa71'
        assert load(phase + '-browser-exit.json')['exit_code'] == 0
        network = load(phase + '-containment.json')
        assert network['status'] == 'isolated_loopback_namespace'
        assert network['database_network_mode'] == 'none' and network['published_ports'] is False
        browser = load(phase + '-browser-containment.json')
        assert browser['network_mode'] in ['container:study-viseron-postgres', 'container:' + browser['database_id']]
        assert browser['same_isolated_namespace'] is True
        assert load(phase + '-empty-storage.json') == {'/tmp/downloads': 0, '/config/public_images': 0}
        phases[phase] = p
    native, api = [phases[p]['continuation'] for p in ['native', 'api']]
    assert native == api
    assert phases['native']['restored_storage_sha256'] == phases['api']['restored_storage_sha256']
    for phase in ['warm', 'native']:
        assert phases[phase]['actionability'] == {'visible': True, 'enabled': True}
    for phase in ['native', 'api']:
        assert load(phase + '-before-database.json')['status'] == 'restore_matches'
        assert load(phase + '-before-filesystem.json')['status'] == 'filesystem_restore_matches'
    assert load('native-before-database.json')['state'] == load('api-before-database.json')['state']
    assert load('native-after-database.json')['state'] == load('api-after-database.json')['state']
    assert load('native-before-filesystem.json')['state_sha256'] == load('api-before-filesystem.json')['state_sha256']
    assert canonical_files(load('native-after-filesystem-inventory.json')) == canonical_files(load('api-after-filesystem-inventory.json'))
    for label in ['producer', 'warm', 'seed', 'native-before', 'native-after', 'api-before', 'api-after']:
        state = load(label + '-database.json')['state']
        for name in ['recordings', 'motion']:
            rows = [t for t in state['tables'] if t['schema_name'] == 'public' and t['relation_name'] == name]
            assert len(rows) == 1 and rows[0]['rows'] == 0
    ordinary = {'name': 'Study Control', 'username': 'studycontrol', 'role': 'read',
                'enabled': True, 'assigned_cameras': None, 'preferences': None}
    for phase in ['producer', 'warm', 'seed']:
        user = phases[phase]['producer']['target']
        assert {k: v for k, v in user.items() if k != 'id'} == ordinary
        assert phases[phase]['producer']['actor']['id'] != user['id']
        assert phases[phase]['producer']['actor']['role'] == 'admin'
    assert native['before'] == phases['seed']['producer']['target']
    assert native['after'] == {**native['before'], 'name': 'Study Edited'}
    assert native['request']['body'] == {'name': 'Study Edited', 'username': 'studycontrol', 'role': 'read', 'assigned_cameras': None}
    assert native['request']['method'] == 'PUT'
    assert native['request']['path'] == '/api/v1/auth/user/' + native['before']['id']
    warm = phases['warm']['continuation']
    for key in ['actor', 'before', 'after']:
        assert {k: v for k, v in warm[key].items() if k != 'id'} == {k: v for k, v in native[key].items() if k != 'id'}
    assert warm['request']['body'] == native['request']['body']
    print('Ordinary qualification verified; zero scientific inputs; no independent-creation full-state equivalence claim.')


if __name__ == '__main__':
    main()
