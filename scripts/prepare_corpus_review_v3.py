#!/usr/bin/env python3
"""Reconcile independently verified archives without changing the v1/v2 maps."""
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.coverage_review_v3 import reconcile
from mixed_interface.evaluation import file_hashes
from prepare_corpus_review_v2 import build as previous_build
from realworld_terminal_campaign import read
from verify_realworld_legacy_halted_archive import verify as verify_v8
from verify_realworld_fresh_legacy_archive import verify as verify_v9
from verify_realworld_article_database_archive import verify as verify_article
from verify_realworld_identity_database_archive import main as verify_identity
from replay_realworld_references_v1 import replay
OUTPUT=ROOT/'manifests/retained-corpus-review-v3.json'
INPUTS=['manifests/retained-corpus-review-v2.json','manifests/realworld-legacy-halted-integration.json',
        'manifests/realworld-fresh-legacy-integration.json','manifests/realworld-article-database-integration.json',
        'manifests/realworld-identity-database-integration.json','manifests/realworld-reference-replay-v1.json',
        'manifests/realworld-boundary-registry-v1.json','manifests/realworld-identity-controls-v1.json',
        'src/mixed_interface/coverage_review_v3.py','scripts/prepare_corpus_review_v3.py',
        'protocol/retained-corpus-review-v3.md']


def collect():
    attempts=[]
    comparisons=read(ROOT/INPUTS[5])['jobs']
    for name,version in [(INPUTS[1],'v8'),(INPUTS[2],'v9')]:
        manifest=read(ROOT/name);root=ROOT/manifest['archive_root']/('realworld-legacy-'+version)
        directories=sorted(p for p in root.glob('legacy-*') if (p/'observations.json').is_file())
        for directory in directories:
            job=read(directory/'job.json');summary=next((directory/'run').glob('*/summary.json'))
            spec=next(c for c in read(summary.parent/'registered-candidates.json')['cases'] if c['candidate_id']==job['candidate_id'])
            observed=read(directory/'observations.json')
            value={'spec':spec,'job_id':job['job_id'],'application_run':manifest['application_run'],
                   'evidence':name,'entry_kind':job['entry_kind'],'channels':[b['continuation'] for b in job['branches']],
                   'terminal_kind':observed['branch']['kind'] if job['entry_kind']=='singleton' else observed['terminal']['kind'],
                   'primary_freeze_complete':manifest['primary_freeze_complete'],'new_primary_samples':manifest['new_primary_samples']}
            if version=='v9' and job['entry_kind']=='pair':value['retrospective_comparison']=comparisons[job['job_id']]
            attempts.append(value)
    diagnostics=[]
    for name,registry in [(INPUTS[3],INPUTS[6]),(INPUTS[4],INPUTS[7])]:
        manifest=read(ROOT/name);specs={c['candidate_id']:c for c in read(ROOT/registry)['cases']}
        for case in manifest['verification']['cases']:
            diagnostics.append({'spec':specs[case['candidate_id']], 'measurement':case,'evidence':name,
                                'scope':'isolated API-prefix observation; no paired continuation or timing transfer',
                                'new_primary_samples':manifest['new_primary_samples'],'primary_freeze_complete':manifest['primary_freeze_complete']})
    return attempts,diagnostics


def build():
    previous=previous_build()
    if previous!=read(ROOT/INPUTS[0]):raise ValueError('Previous review differs')
    verify_v8();verify_v9();verify_article();verify_identity()
    if replay()!=read(ROOT/INPUTS[5]):raise ValueError('Reference replay differs')
    attempts,diagnostics=collect()
    return {'review':reconcile(previous['review'],attempts,diagnostics),'input_sha256':file_hashes(ROOT,INPUTS)}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    value=build()
    if args.verify:
        if read(OUTPUT)!=value:raise ValueError('Corpus review v3 differs')
    else:OUTPUT.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({'counts':value['review']['counts'],'execution_requirements':value['review']['remaining_execution_requirement_counts']},indent=2))
