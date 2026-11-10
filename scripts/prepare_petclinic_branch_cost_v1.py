#!/usr/bin/env python3
"""Hash offline PetClinic timing preparation; no runtime dispatch or qualification."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.evaluation import file_hashes
SOURCES=['scripts/petclinic_branch_cost_v1.mjs','scripts/run_petclinic_pair_job_v4.mjs',
         'scripts/run_petclinic_pair_job_v3.mjs','scripts/petclinic_job_binding_v3.mjs',
         'scripts/petclinic_cleanup.mjs','scripts/petclinic_integrity.mjs','scripts/petclinic_response_capture.mjs',
         'scripts/prepare_petclinic_branch_cost_v1.py','tests/petclinic-branch-cost.test.mjs',
         'protocol/petclinic-branch-cost-v1.md','protocol/primary-cost-scope-v2.md']
OUTPUT=ROOT/'manifests/petclinic-branch-cost-v1.json'

def build():
    return {'kind':'petclinic_monotonic_branch_cost_preparation_v1','source_sha256':file_hashes(ROOT,SOURCES),
        'clock':'node performance.now()/1000','scope':'reset/startup through raw readback validation and owned branch cleanup',
        'excluded':['shared browser startup','final cost-sidecar serialization','controller-summary serialization'],
        'complete_cost_requires':['observed monotonic end','raw evidence binding','backend exit confirmed','branch context closure confirmed'],
        'runtime_dispatch_qualified':False,'independent_loader_integrated':False,'primary_freeze_complete':False,
        'new_application_executions':0,'new_primary_samples':0}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args();value=build()
    if args.verify:
        if json.loads(OUTPUT.read_text())!=value:raise ValueError('PetClinic cost preparation differs')
    else:OUTPUT.write_text(json.dumps(value,indent=2)+'\n')
    print('Verified PetClinic timing preparation; runtime qualification remains pending')
