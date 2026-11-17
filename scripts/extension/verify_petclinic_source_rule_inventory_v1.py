"""Reconstruct source inventory from hash-matched local source files, not outcomes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.angular_rule_inventory import inventory

def main(directory):
    manifest=json.loads((ROOT/'manifests/petclinic-source-rule-inventory-v1.json').read_text())
    rebuilt=[]
    for item in manifest['sources']:
        raw=(directory/Path(item['path']).name).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==item['sha256']
        if item['path'].endswith('-form.ts'):
            rebuilt.append(inventory(raw.decode(),item['endpoint']))
    assert rebuilt==manifest['inventories']
    assert manifest['application_executions']==manifest['independent_evaluation_cases']==0
    print(json.dumps(dict(source_files=len(manifest['sources']),schemas=len(rebuilt),
        explicit_declarations=sum(len(x['candidates']) for x in rebuilt),
        unsupported_calls=sum(len(x['unsupported']) for x in rebuilt),
        semantic_lowering=False,automatic_api_mapping=False,independent_cases=0),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-directory',type=Path,required=True);main(p.parse_args().source_directory)
