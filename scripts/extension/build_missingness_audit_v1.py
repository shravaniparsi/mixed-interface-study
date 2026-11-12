#!/usr/bin/env python3
"""Finite-cohort missing-outcome accounting, not confidence intervals."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def build():
    source = ROOT / 'manifests/independent-input-summary-v1.json'
    d = json.loads(source.read_text())
    selected = sum(w['selected_inputs'] for w in d['workflow_selection'])
    executed = sum(w['executed_initial_inputs'] for w in d['workflow_selection'])
    missing = selected - executed
    assert (selected, executed, missing) == (44, 28, 16)
    assert len(d['unexecuted_selected_input_ids']) == missing
    rejected = d['initial_sample_counts']['producer_rejected']
    accepted = executed - rejected
    assert sum(d['initial_sample_counts'].values()) == executed
    assert d['native_only_detections'] == 0 and accepted == 25
    scenarios = [{'hypothetical_missing_positive_cases': k, 'selected_cohort_yield_numerator': k, 'selected_cohort_yield_denominator': selected, 'selected_cohort_yield': k / selected} for k in range(missing + 1)]
    return {'kind': 'independent_input_missingness_audit_v1', 'analysis_timing': 'post hoc descriptive sensitivity audit; no new experiments', 'selected_inputs': selected, 'executed_inputs': executed, 'producer_rejections': rejected, 'accepted_initial_inputs': accepted, 'observed_incremental_native_detections': 0, 'missing_selected_inputs': missing, 'execution_coverage': executed / selected, 'observed_accepted_case_yield': {'numerator': 0, 'denominator': accepted}, 'finite_selected_cohort_possible_yield': {'lower': 0, 'upper': missing / selected, 'upper_numerator': missing, 'denominator': selected}, 'interpretation': 'Logical missing-outcome range for accepted-and-incrementally-detected yield per selected input. Excluded cases need a valid measurement procedure before this hypothetical outcome is defined. Not an estimated missing-data rate, confidence interval, prevalence estimate or permission to rerun exclusions.', 'workflow_coverage': {'selected': 6, 'qualified': 3, 'excluded': 3, 'schema_exclusion_without_enumerated_inputs': 1}, 'workflow_counts': d['workflow_selection'], 'scenarios': scenarios, 'source_sha256': {str(source.relative_to(ROOT)): hashlib.sha256(source.read_bytes()).hexdigest()}}

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--verify', action='store_true'); args = parser.parse_args()
    result = build(); p = ROOT / 'manifests/independent-input-missingness-audit-v1.json'
    if args.verify:
        assert json.loads(p.read_text()) == result
    else:
        p.write_text(json.dumps(result, indent=2) + '\n')
    print('Observed: 0/25 accepted initial cases; 16/44 selected inputs unexecuted. Logical selected-cohort yield range: 0 to 16/44. No population inference.')

if __name__ == '__main__':
    main()
