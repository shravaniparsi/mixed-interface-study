#!/usr/bin/env python3
"""Rebuild readiness from independently verified generated archives and frozen v3."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.coverage_review_v4 import reconcile
from mixed_interface.evaluation import file_hashes
from prepare_corpus_review_v3 import build as previous_build
from realworld_terminal_campaign import read
from verify_realworld_generated_runtime_archive import verify as verify_controls
from verify_realworld_generated_mutations_archive import verify as verify_mutations
OUTPUT=ROOT/'manifests/retained-corpus-review-v4.json'
INPUTS=['manifests/retained-corpus-review-v3.json','manifests/realworld-generated-runtime-integration.json',
        'manifests/realworld-generated-mutations-integration.json','src/mixed_interface/coverage_review_v4.py',
        'scripts/prepare_corpus_review_v4.py','protocol/retained-corpus-review-v4.md',
        'scripts/verify_realworld_generated_runtime_archive.py','scripts/verify_realworld_generated_mutations_archive.py']


def collect():
    attempts=[]
    for name,version in [(INPUTS[1],'v2'),(INPUTS[2],'v3')]:
        manifest=read(ROOT/name);root=ROOT/manifest['archive_root']/('realworld-generated-'+version)
        for result in manifest['verification']['results']:
            directory=root/result['job_id'];job=read(directory/'job.json');observed=read(directory/'observations.json')
            branches={c:observed['branches'][c]['components'] for c in ('api','ui')}
            attempts.append({'job':job,'specs':{c:read(directory/c/'case.json') for c in branches},
                'application_run':manifest['application_run'],'evidence':name,
                'campaign_status':read(root/'report.json')['status'],
                'terminal_kind':observed['terminal']['kind'],
                'branch_observations':{c:{k:b[k] for k in ('accepted_prefix','assigned_continuation_reached','execution_evidence_complete')} for c,b in branches.items()},
                'branch_total_s':result['branch_total_s'],
                'new_primary_samples':manifest['new_primary_samples'],'primary_freeze_complete':manifest['primary_freeze_complete']})
    return attempts


def build():
    previous=previous_build()
    if previous!=read(ROOT/INPUTS[0]):raise ValueError('Previous review differs')
    verify_controls();verify_mutations()
    return {'review':reconcile(previous['review'],collect()),'input_sha256':file_hashes(ROOT,INPUTS)}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    value=build()
    if args.verify:
        if read(OUTPUT)!=value:raise ValueError('Corpus review v4 differs')
    else:OUTPUT.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({'counts':value['review']['counts'],'execution_requirements':value['review']['remaining_execution_requirement_counts']},indent=2))
