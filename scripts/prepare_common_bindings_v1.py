#!/usr/bin/env python3
"""Source-qualified first common binding set; exact generated and timed PetClinic cases."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.common_bindings_v1 import registry,preflight,bind_job
from mixed_interface.terminal_outcomes import POLICY_SHA256
from mixed_interface.evaluation import file_hashes
from prepare_corpus_review_v5 import build as review_build
from realworld_generated_bindings_v1 import case_for
from petclinic_timed_jobs_v4 import validate_job as pc_case
from petclinic_timed_jobs_v4 import read,sha
from verify_realworld_generated_runtime_archive import verify as verify_controls
from verify_realworld_generated_mutations_archive import verify as verify_mutations
from verify_petclinic_timing_archive_v1 import verify as verify_petclinic
OUTPUT=ROOT/'manifests/common-bindings-v1.json'
ARCHIVES=[('generated_control_v2','manifests/realworld-generated-runtime-integration.json','realworld-generated-v2'),
          ('generated_mutation_v3','manifests/realworld-generated-mutations-integration.json','realworld-generated-v3'),
          ('petclinic_timing_v1','manifests/petclinic-timing-runtime-v1.json','petclinic-timing-v1')]
INPUTS=['src/mixed_interface/common_bindings_v1.py','scripts/prepare_common_bindings_v1.py',
        'tests/test_common_bindings_v1.py','protocol/common-bindings-v1.md','manifests/retained-corpus-review-v5.json']+[x[1] for x in ARCHIVES]


def collect():
    profiles={};records=[]
    for profile,name,folder in ARCHIVES:
        m=read(ROOT/name);root=ROOT/m['archive_root']/folder;cert=read(root/'plan.json')
        is_pc=profile=='petclinic_timing_v1'
        profiles[profile]={'source_commit':m['source_commit'],'evidence_manifest':name,'source_sha256':cert['sources'],
            'terminal_policy_sha256':POLICY_SHA256,'cost_scope':'petclinic_branch_reset_through_raw_validation_and_owned_cleanup_v1' if is_pc else 'generated_branch_before_worker_through_parent_raw_validation_and_cleanup',
            'costs_are_observed_attempts_not_budget_estimates':True}
        for result in m['verification']['results']:
            if profile=='generated_control_v2' and result['job_id']!='generated-000':continue
            if is_pc:
                d=root/result['slot_id'];slot=read(d/'slot.json');job=slot['job'];spec=pc_case(job,slot['batch'])
                pid='petclinic_development::'+job['pair_id'];cases={c:spec for c in ('api','ui')}
                order=[b['continuation'] for b in job['branches']];ids={b['continuation']:b['case_id'] for b in job['branches']};context={'batch':slot['batch']};attempt=result['slot_id']
            else:
                d=root/result['job_id'];job=read(d/'job.json');pid=job['pair']['pair_id'];cases={c:case_for(job,c) for c in ('api','ui')}
                order=[b['channel'] for b in job['branches']];ids={b['channel']:b['case_id'] for b in job['branches']};context={};attempt=result['job_id']
            records.append({'pair_id':pid,'profile':profile,'runtime_job':job,'runtime_context':context,'cases':cases,
                'branch_order':order,'effective_case_ids':ids,'observed_cost_s':result['branch_total_s'],
                'observed_attempt':attempt,'observed_terminal_kind':result['terminal_kind']})
    return records,profiles


def build():
    reviewed=review_build()
    if reviewed!=read(ROOT/'manifests/retained-corpus-review-v5.json'):raise ValueError('Readiness review differs')
    verify_controls();verify_mutations();verify_petclinic()
    records,profiles=collect();value=registry(reviewed['review'],records,profiles)
    live={p:sha(ROOT/p) for profile in profiles.values() for p in profile['source_sha256']}
    checked=preflight(value,[b['pair_id'] for b in value['bindings']],live)
    initial=[bind_job(value,checked,j) for j in checked['campaign']['schedule']['initial_jobs']]
    return {'registry':value,'preflight':checked,'initial_bindings':initial,'input_sha256':file_hashes(ROOT,INPUTS),
            'new_application_executions':0,'new_primary_samples':0,'primary_freeze_complete':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args();v=build()
    if args.verify:
        if read(OUTPUT)!=v:raise ValueError('Common bindings differ')
    else:OUTPUT.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps(v['registry']['counts'],indent=2))
