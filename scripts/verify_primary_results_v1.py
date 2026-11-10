#!/usr/bin/env python3
"""Require every registered phase before accepting the final descriptive analysis."""
import json
from primary_preflight_v1 import ROOT, read, units
from analyze_primary_units_v1 import analyze
from mixed_interface.repetition import require


def verify():
    initial = ROOT / 'manifests/primary-initial-runtime-v1.json'
    second = ROOT / 'manifests/primary-repeat2-runtime-v1.json'
    third = ROOT / 'manifests/primary-repeat3-runtime-v1.json'
    second_units = units('repeat2')
    third_units = []
    if second_units:
        require(second.is_file(), 'Selected second repetitions are not retained')
        third_units = units('repeat3')
        if third_units:
            require(third.is_file(), 'Selected third repetitions are not retained')
        else:
            require(not third.exists(), 'Unexpected empty third phase archive')
    else:
        require(not second.exists() and not third.exists(), 'Unexpected follow-up archive without selected units')
    result = analyze(initial, second if second_units else None, third if third_units else None)
    require(result == read(ROOT / 'manifests/primary-results-v1.json'), 'Final analysis differs from independently reconstructed evidence')
    return {'complete_registered_collection': True, 'initial_units': len(units('initial')),
            'second_units': len(second_units), 'third_units': len(third_units),
            'counts': result['counts'], 'claim_scope': result['claim_scope']}


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
