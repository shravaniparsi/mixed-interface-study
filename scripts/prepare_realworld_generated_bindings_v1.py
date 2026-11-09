#!/usr/bin/env python3
"""Record offline generated job bindings and verify equality with the retained map."""
import argparse,json
from realworld_generated_bindings_v1 import ROOT,plan
from mixed_interface.evaluation import file_hashes
OUTPUT=ROOT/'manifests/realworld-generated-bindings-v1.json'
SOURCES=['manifests/realworld-article-generated-pool-v1.json','manifests/retained-corpus-review-v3.json',
         'scripts/realworld_generated_bindings_v1.py','scripts/prepare_realworld_generated_bindings_v1.py',
         'scripts/summarize_realworld_oracle_components.py','scripts/realworld_generated_case.mjs',
         'protocol/realworld-generated-bindings-v1.md']


def build():
    value=plan()
    rows=json.loads((ROOT/SOURCES[1]).read_bytes())['review']['rows']
    expected=[r for r in rows if r['path_family']=='realworld_generated']
    if [j['pair'] for j in value['jobs']]!=[r['inventory_entry'] for r in expected]:raise ValueError('Retained pairs differ')
    for job,row in zip(value['jobs'],expected):
        if job['reference_pair_id']!=row['reference_control_pair_id']:raise ValueError('Reference differs')
        if {b['case_id']:b['source_case_sha256'] for b in job['branches']}!={b['source_case_id']:b['source_case_sha256'] for b in row['branches']}:raise ValueError('Branch binding differs')
    return {'plan':value,'source_sha256':file_hashes(ROOT,SOURCES)}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args();value=build()
    if args.verify:
        if json.loads(OUTPUT.read_bytes())!=value:raise ValueError('Generated bindings changed')
    else:OUTPUT.write_text(json.dumps(value,indent=2)+'\n')
    print('Nine offline pairs / eighteen branches bound; runtime dispatch remains unqualified')
