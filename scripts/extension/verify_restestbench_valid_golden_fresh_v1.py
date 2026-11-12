#!/usr/bin/env python3
"""Use the original evidence checks for the registered fresh-dispatch handle."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'scripts/extension/verify_restestbench_valid_golden_v1.py'
spec=importlib.util.spec_from_file_location('original_verifier',BASE)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.RUN=43133202268

def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--verify',action='store_true');args=p.parse_args()
    value=module.build(args.archive)
    value['kind']='restestbench_valid_golden_fresh_v1'
    value['original_verifier_sha256']=hashlib.sha256(BASE.read_bytes()).hexdigest()
    protocol=ROOT/'protocol/restestbench-fresh-dispatch-diagnostic-v1.md'
    value['fresh_dispatch_protocol_sha256']=hashlib.sha256(protocol.read_bytes()).hexdigest()
    if args.verify:assert json.loads(args.output.read_text())==value
    else:
        assert not args.output.exists();args.output.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({k:v for k,v in value.items() if k!='evidence_sha256'},indent=2))

if __name__=='__main__':main()
