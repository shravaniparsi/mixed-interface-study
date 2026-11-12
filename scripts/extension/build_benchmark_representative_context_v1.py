#!/usr/bin/env python3
"""Extract only task identities, initial URLs and intents for frozen representatives."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    source=ROOT/'results/benchmark-frame-screen-v1/assets/dataset/webarena-verified.json'
    tasks=json.loads(source.read_text());selection=json.loads((ROOT/'manifests/benchmark-continuation-selection-v1.json').read_text())
    rows=[]
    for family in selection['candidate_families']:
        task=next(t for t in tasks if t['task_id']==family['representative_task_id'])
        rows.append({'family':family['family'],'task_id':task['task_id'],'start_urls':task['start_urls'],'intent':task['intent']})
    result={'kind':'benchmark_representative_context_v1','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'read_fields':['task_id','start_urls','intent'],'evaluator_fields_inspected':False,'representatives':rows}
    target=ROOT/'manifests/benchmark-representative-context-v1.json'
    if args.verify:
        assert json.loads(target.read_text())==result
    else:
        target.write_text(json.dumps(result,indent=2)+'\n')
    print('Verified six representative contexts without projecting evaluator fields.')
if __name__=='__main__':main()
