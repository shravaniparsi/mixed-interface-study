#!/usr/bin/env python3
"""Build or verify a deterministic historical PetClinic terminal replay."""
import argparse,json
from pathlib import Path
from petclinic_terminal_outcomes import ROOT,replay_archive,load,sha
from mixed_interface.evaluation import file_hashes
OUTPUT='results/petclinic-terminal-replay-v2.json'
MANIFEST='manifests/petclinic-terminal-extraction-v2.json'
SOURCES=['scripts/prepare_petclinic_terminal.py','scripts/petclinic_terminal_outcomes.py',
 'tests/test_petclinic_terminal_outcomes.py','protocol/petclinic-terminal-extraction-v2.md',
 'scripts/summarize_petclinic_integrity_components.py','scripts/summarize_petclinic_oracle_components.py',
 'scripts/validate_petclinic_integrity.py','scripts/petclinic_boundary_slice.mjs',
 'scripts/petclinic_integrity.mjs','scripts/petclinic_response_capture.mjs','scripts/petclinic_cleanup.mjs',
 'src/mixed_interface/terminal_outcomes.py','src/mixed_interface/repetition.py',
 'manifests/petclinic-candidates-v1.json','manifests/petclinic-integrity-controls-v1.json',
 'manifests/petclinic-execution-integrity.json']


def generate():
    prior=load(ROOT/'manifests/petclinic-execution-integrity.json')
    result=replay_archive(ROOT/'results/petclinic-integrity-ci-20261107')
    manifest={'kind':'petclinic_terminal_extraction_preparation','status':'historical_replay_verified',
              'historical_application_run':prior['application_run'],'historical_source_commit':prior['validation_source_commit'],
              'pairs':6,'branches':12,'terminal_kinds':[p['terminal']['kind'] for p in result['pairs']],
              'application_executions_added':0,'per_job_dispatch_qualified':False,'primary_freeze_complete':False,
              'output':OUTPUT,'input_sha256':file_hashes(ROOT,sorted(set(SOURCES)|set(prior['compact_artifact_sha256'])))}
    return result,manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    result,manifest=generate()
    for name,value in ((OUTPUT,result),(MANIFEST,manifest)):
        if args.verify:
            if load(ROOT/name)!=value:raise ValueError('PetClinic replay or source fingerprint differs: '+name)
        else:(ROOT/name).write_text(json.dumps(value,indent=2)+'\n')
    print('Verified six historical PetClinic terminal pairs; no new application execution or dispatch qualification.')
