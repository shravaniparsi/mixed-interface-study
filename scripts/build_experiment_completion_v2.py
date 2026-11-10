#!/usr/bin/env python3
"""Complete only after original experiments and explicit provider recovery are retained."""
import argparse,json
from collections import Counter
from primary_preflight_v1 import ROOT,read,sha
from verify_primary_results_v1 import verify as primary
from verify_quartz_recovery_results_v1 import verify as recovery
from retain_quartz_provider_failure_v1 import build as retained,OUTPUT as RETENTION,ARCHIVE
from analyze_primary_units_v1 import component_overlap
from mixed_interface.terminal_outcomes import decision
from mixed_interface.common_execution_v1 import write
from mixed_interface.repetition import require
OUTPUT=ROOT/'manifests/experiment-completion-v2.json'

def combine_categories(first,additional,expected):
    require(not(set(first)&set(additional)),'Corrected case counted twice')
    require(set(first)|set(additional)==set(expected),'Corrected case coverage incomplete or foreign')
    return {**first,**additional}

def build():
    original=primary();recovered=recovery();provider=retained();require(provider==read(RETENTION),'Provider retention differs')
    plan=read(ROOT/'manifests/quartz-form-correction-preparation-v1.json')['plan']['initial_batches']
    first={}
    for path in ARCHIVE.glob('*/quartz-correction-unit-v1/plan.json'):
        unit=read(path)['unit'];record=provider['records'][unit['batch_id']]
        require(record['status']=='executed_and_reconstructed' and record['verification']['qualified_observations'],'First collection unit not qualified')
        ledger=record['verification']['ledger'];require(ledger['status']=='completed_observations','First collection unit incomplete')
        candidate=ledger['observations'][0]['terminal'];require(not decision(candidate)['repeat'],'Unfulfilled follow-up in first corrected collection')
        first[unit['target_pair_id']]=component_overlap(read(path.parent/unit['jobs'][0]['attempt_id']/'loaded.json'))['category']
    recovery_result=read(ROOT/'manifests/quartz-recovery-results-v1.json')
    additional={r['pair_id']:r['assigned_overlap']['category'] for r in recovery_result['rows']}
    coverage=combine_categories(first,additional,[u['target_pair_id'] for u in plan])
    require(len(first)==6 and len(additional)==16,'Executed/recovery split differs')
    paths=['manifests/primary-results-v1.json',str(RETENTION.relative_to(ROOT)),
        'manifests/quartz-recovery-results-v1.json','manifests/quartz-form-measurement-audit-v1.json',
        'manifests/quartz-form-correction-freeze-v1.json','manifests/quartz-recovery-freeze-v1.json']
    return {'kind':'completed_diagnostic_experiments_with_explicit_provider_recovery_v2',
        'original_collection':original,'incomplete_corrected_attempt':{'executed_units':6,'provider_rejected_units':16,'original_attempt_complete':False},
        'additional_recovery_collection':recovered,'corrected_case_coverage':coverage,'corrected_category_counts':dict(Counter(coverage.values())),
        'evidence_sha256':{p:sha(ROOT/p) for p in paths},'remaining_registered_units':0,'independent_defects_confirmed':None,
        'scope':'All original units and selected repetitions; six executed corrected units plus a separate 16-case recovery collection and its selected repetitions. The failed provider attempt is preserved. This is case coverage, not independent sample pooling.',
        'not_established':['human defect adjudication','timed selector efficacy','population generalization','journal submission readiness']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');args=p.parse_args();value=build()
    if args.verify:require(read(OUTPUT)==value,'Completion differs from retained evidence')
    else:require(not OUTPUT.exists(),'Completion already registered');write(OUTPUT,value)
    print(json.dumps({'remaining_registered_units':value['remaining_registered_units'],'corrected_cases':len(value['corrected_case_coverage'])}))
