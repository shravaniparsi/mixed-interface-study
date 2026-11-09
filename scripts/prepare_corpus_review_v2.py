#!/usr/bin/env python3
"""Verify retained evidence and derive the current corpus-readiness review."""
import argparse,json,sys
from pathlib import Path
from contextlib import redirect_stdout
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.coverage_review_v2 import reconcile
from mixed_interface.evaluation import file_hashes
from prepare_corpus_coverage import generate
from verify_realworld_paired_database_archive import verify as verify_paired
from verify_realworld_identity_halted_archive import main as verify_halted
OUTPUT='manifests/retained-corpus-review-v2.json'
INPUTS=['manifests/retained-corpus-coverage-v1.json','manifests/realworld-identity-controls-v1.json',
        'manifests/realworld-paired-database-integration.json','manifests/realworld-identity-halted-integration.json',
        'src/mixed_interface/coverage_review_v2.py','scripts/prepare_corpus_review_v2.py',
        'protocol/retained-corpus-review-v2.md']


def build():
    read=lambda p:json.loads((ROOT/p).read_bytes())
    baseline=read(INPUTS[0]);expected=generate()
    if baseline!=expected:raise ValueError('Base coverage differs from its source-derived map')
    with redirect_stdout(sys.stderr):
        verified=verify_paired();verify_halted()
    paired=read(INPUTS[2])
    if verified!=paired['verification']:raise ValueError('Paired evidence differs')
    review=reconcile(baseline['coverage'],read(INPUTS[1]),paired,read(INPUTS[3]))
    return {'review':review,'input_sha256':file_hashes(ROOT,INPUTS)}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    value=build();path=ROOT/OUTPUT
    if args.verify:
        if json.loads(path.read_bytes())!=value:raise ValueError('Reviewed coverage or provenance changed')
    else:path.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({'verified':args.verify,'counts':value['review']['counts'],
                      'execution_requirements':value['review']['remaining_execution_requirement_counts'],
                      'outcome_limits':value['review']['retained_outcome_limit_counts']},indent=2))


if __name__=='__main__':main()
