#!/usr/bin/env python3
"""Rebuild v4 and verify v10 before reconciling one exact reference binding."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.coverage_review_v5 import reconcile
from mixed_interface.evaluation import file_hashes
from prepare_corpus_review_v4 import build as previous_build
from verify_realworld_reference_runtime_v10 import verify,MANIFEST
from realworld_terminal_campaign import read
OUTPUT=ROOT/'manifests/retained-corpus-review-v5.json'
INPUTS=['manifests/retained-corpus-review-v4.json','manifests/realworld-reference-runtime-v10.json',
        'src/mixed_interface/coverage_review_v5.py','scripts/prepare_corpus_review_v5.py',
        'protocol/retained-corpus-review-v5.md','scripts/verify_realworld_reference_runtime_v10.py']


def collect():
    manifest=read(MANIFEST);root=ROOT/manifest['archive_root']/'realworld-legacy-v10';attempts=[]
    for d in sorted(root.glob('legacy-*')):
        job=read(d/'job.json');observed=read(d/'observations.json')
        summary_path=next((d/'run').glob('*/summary.json'));summary=read(summary_path)
        spec=next(c for c in read(summary_path.parent/'registered-candidates.json')['cases'] if c['candidate_id']==job['candidate_id'])
        paired=job['entry_kind']=='pair'
        attempts.append({'job':job,'spec':spec,'application_run':manifest['application_run'],
            'source_commit':manifest['source_commit'],'evidence':INPUTS[1],
            'channels':[b['continuation'] for b in summary['branches']],
            'literal_kind':observed['literal_terminal']['kind'] if paired else None,
            'terminal_kind':observed['terminal']['kind'] if paired else observed['branch']['kind'],
            'reference_comparison':observed.get('reference_comparison'),
            'new_primary_samples':manifest['new_primary_samples'],'primary_freeze_complete':manifest['primary_freeze_complete']})
    return attempts


def build():
    previous=previous_build()
    if previous!=read(ROOT/INPUTS[0]):raise ValueError('Previous review differs')
    verify()
    return {'review':reconcile(previous['review'],collect()),'input_sha256':file_hashes(ROOT,INPUTS)}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args();v=build()
    if args.verify:
        if read(OUTPUT)!=v:raise ValueError('Corpus review v5 differs')
    else:OUTPUT.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps({'counts':v['review']['counts'],'execution_requirements':v['review']['remaining_execution_requirement_counts']},indent=2))
