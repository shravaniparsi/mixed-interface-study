#!/usr/bin/env python3
"""Reanalyse retained summaries only; no DB/application execution or relabelling."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from mixed_interface.write_observations import measure as old
from mixed_interface.write_observations_v2 import measure as new
from mixed_interface.write_frame import equal


def main():
    inputs = ['manifests/realworld-paired-database-integration.json',
              'manifests/realworld-identity-database-integration.json',
              'manifests/realworld-identity-controls-v1.json']
    paired, identity, controls = [json.loads((ROOT / p).read_bytes()) for p in inputs]
    specs = {c['candidate_id']: c for c in controls['cases']}
    assert len(specs) == len(controls['cases']), 'Duplicate control identity'
    assert len(paired['verification']['results']) == 4
    assert len(identity['verification']['cases']) == 3
    rows = []
    for case in paired['verification']['results']:
        assert set(case['measurements']) == {'api', 'ui'}
        for channel, sidecar in case['measurements'].items():
            m = sidecar['measurement']; p = m['persistence']
            args = (m['http']['status'], p['before'], p['immediate'], p['restart'],
                    specs[case['candidate_id']]['prefix_payload'], m['readbacks'])
            before, after = old(*args), new(*args)
            assert equal(before['persistence'], p), 'Legacy reconstruction differs'
            changed = [k for k in p if not equal(before['persistence'][k], after['persistence'][k])]
            rows.append({'source': inputs[0], 'candidate_id': case['candidate_id'],
                         'channel': channel, 'legacy_summary_reproduced': True,
                         'changed_measurement_fields': changed})
    for c in identity['verification']['cases']:
        def obs(key):
            return {'state': 'observed', 'projection': {'username': c[key]}}
        args = (c['prefix_status'], obs('before_username'), obs('immediate_username'),
                obs('after_restart_username'), specs[c['candidate_id']]['prefix_payload'],
                {phase + ':' + endpoint: {'state': 'response', 'status': status}
                 for phase, endpoints in c['readback_statuses'].items()
                 for endpoint, status in endpoints.items()})
        before, after = old(*args), new(*args)
        p = before['persistence']
        assert p['intended_values_observed'] == c['requested_username_observed']
        assert p['immediate_projection_survives_restart'] == c['post_response_state_survives_restart']
        assert (p['selected_change'] != 'unchanged') == c['username_changed']
        rows.append({'source': inputs[1], 'candidate_id': c['candidate_id'],
                     'channel': 'api_only', 'legacy_summary_reproduced': True,
                     'changed_measurement_fields': [k for k in p if not equal(p[k], after['persistence'][k])]})
    paths = inputs + ['src/mixed_interface/write_observations.py',
                     'src/mixed_interface/write_observations_v2.py',
                     'src/mixed_interface/write_frame.py',
                     'scripts/extension/audit_typed_persistence_impact_v1.py']
    result = {'scope': 'retained summary reanalysis; not raw archive revalidation',
              'records_checked': len(rows),
              'records_with_changed_measurements': sum(bool(r['changed_measurement_fields']) for r in rows),
              'rows': rows,
              'raw_directory_availability': {x['evidence_directory']: (ROOT / x['evidence_directory']).is_dir()
                                             for x in [paired, identity]},
              'input_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
              'historical_results_modified': False, 'scientific_cases_added': 0,
              'global_no_impact_claim_supported': False}
    out = ROOT / 'results/typed-persistence-impact-v1'
    out.mkdir(exist_ok=True)
    target = out / 'summary.json'
    data = json.dumps(result, indent=2) + '\n'
    if '--verify' in sys.argv:
        assert target.read_text() == data, 'Saved audit differs'
    else:
        assert not target.exists(), 'Do not overwrite retained audit'
        target.write_text(data)
    print(json.dumps({k: result[k] for k in ['records_checked', 'records_with_changed_measurements',
                                           'global_no_impact_claim_supported']}))


if __name__ == '__main__':
    main()
