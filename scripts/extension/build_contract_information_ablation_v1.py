#!/usr/bin/env python3
"""Post-hoc annotation ablation; full manual contract is a comparator, not independent truth."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from mixed_interface.write_contract import check

MODES = ['requested_only', 'frame_without_exceptions', 'frame_with_exceptions',
         'complete_transition', 'complete_transition_and_agreement']


def score(record, mode):
    r = copy.deepcopy(record)
    contract = r['contract']
    if mode != 'complete_transition_and_agreement':
        contract['agreements'] = []
    if mode in ('requested_only', 'frame_without_exceptions'):
        contract['derived_fields'] = []
        contract['derived_assignments'] = {}
    elif mode == 'frame_with_exceptions':
        contract['derived_fields'] = sorted(set(contract.get('derived_fields', [])) |
                                            set(contract.get('derived_assignments', {})))
        contract['derived_assignments'] = {}
    result = check(r)
    return bool(result['frame']['failed_assignments']) if mode == 'requested_only' else result['contract_violation']


def build():
    source = ROOT / 'manifests/write-contract-replay-v1.json'
    bundle = json.loads(source.read_text())
    for name, digest in bundle['source_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
    records = bundle['records']
    reference = {s['id']: s['contract_violation'] for s in bundle['scores']}
    rows = []
    for r in records:
        alerts = {mode: score(r, mode) for mode in MODES}
        assert alerts['complete_transition_and_agreement'] == reference[r['id']]
        rows.append({'id': r['id'], 'project': r['project'], 'alerts': alerts})
    groups = {}
    for project in sorted({r['project'] for r in rows}):
        selected = [r for r in rows if r['project'] == project]
        groups[project] = {'records': len(selected), 'modes': {mode: {
            'alert_records': sum(r['alerts'][mode] for r in selected),
            'additional_relative_to_full_contract': [r['id'] for r in selected if r['alerts'][mode] and not reference[r['id']]],
            'missing_relative_to_full_contract': [r['id'] for r in selected if not r['alerts'][mode] and reference[r['id']]],
        } for mode in MODES}}
    return {'kind': 'contract_information_ablation_v1', 'timing': 'post_hoc_on_outcome_exposed_traces',
            'new_application_executions': 0, 'rows': rows, 'by_project': groups,
            'aggregate_alert_records': {m: sum(r['alerts'][m] for r in rows) for m in MODES},
            'agreement_increment_over_complete_transition': [r['id'] for r in rows if
                r['alerts']['complete_transition_and_agreement'] and not r['alerts']['complete_transition']],
            'source_sha256': {str(source.relative_to(ROOT)): hashlib.sha256(source.read_bytes()).hexdigest()},
            'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'limits': ['All modes receive manually mapped state assignments; none is a tested automatic inference method.',
                       'Full manual contracts are the comparison reference, not independent ground truth.',
                       'Relative disagreements are not precision/recall or population false-positive estimates.',
                       'Variant counts are clustered by project; no significance test or independent-defect count is warranted.']}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--verify', action='store_true'); args = p.parse_args()
    value = build(); dest = ROOT / 'manifests/contract-information-ablation-v1.json'
    if args.verify: assert json.loads(dest.read_text()) == value
    else:
        assert not dest.exists()
        dest.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({'aggregate_alert_records': value['aggregate_alert_records'],
                      'agreement_increment_over_complete_transition': value['agreement_increment_over_complete_transition']}))


if __name__ == '__main__': main()
