#!/usr/bin/env python3
"""Certify completion of the original and separate corrected diagnostic collections."""
import argparse,json
from primary_preflight_v1 import ROOT,read,sha
from verify_primary_results_v1 import verify as primary
from verify_quartz_correction_results_v1 import verify as correction
from mixed_interface.common_execution_v1 import write
from mixed_interface.repetition import require
OUTPUT=ROOT/'manifests/experiment-completion-v1.json'

def build():
    original=primary();corrected=correction()
    paths=['manifests/primary-results-v1.json','manifests/quartz-correction-results-v1.json',
           'manifests/quartz-form-measurement-audit-v1.json','manifests/primary-execution-freeze-v1.json',
           'manifests/quartz-form-correction-freeze-v1.json']
    return {'kind':'completed_registered_diagnostic_experiments_v1',
            'original_collection':original,'separate_exposed_correction_collection':corrected,
            'evidence_sha256':{p:sha(ROOT/p) for p in paths},'remaining_registered_units':0,
            'independent_defects_confirmed':None,
            'scope':'All frozen original diagnostic units and selected follow-ups, plus the separately qualified exposed Quartz measurement-correction cohort and its selected follow-ups. Original and corrected observations are not independent samples.',
            'not_established':['human defect adjudication','timed selector efficacy','population generalization','journal submission readiness']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');args=p.parse_args();value=build()
    if args.verify:require(read(OUTPUT)==value,'Experiment completion differs from reconstructed evidence')
    else:
        require(not OUTPUT.exists(),'Completion already registered');write(OUTPUT,value)
    print(json.dumps({'remaining_registered_units':value['remaining_registered_units'],
        'original_units':sum(value['original_collection'][k] for k in ('initial_units','second_units','third_units')),
        'correction_units':sum(value['separate_exposed_correction_collection'][k] for k in ('initial_units','second_units','third_units'))}))
