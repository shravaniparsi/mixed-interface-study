#!/usr/bin/env python3
"""Source-pinned offline mutation qualification preparation."""
import argparse,json
from realworld_generated_bindings_v1 import ROOT
from realworld_generated_mutations_v3 import plan
from mixed_interface.evaluation import file_hashes
OUTPUT=ROOT/'manifests/realworld-generated-mutations-v3.json'
SOURCES=['scripts/realworld_generated_mutations_v3.py','scripts/realworld_generated_terminal_v3.py',
         'scripts/realworld_generated_runtime_v3.py','scripts/prepare_realworld_generated_mutations_v3.py',
         'tests/generated_mutation_fixture_v3.py','tests/test_realworld_generated_mutations_v3.py',
         'protocol/realworld-generated-mutations-v3.md','manifests/realworld-generated-bindings-v1.json',
         'manifests/realworld-article-generated-pool-v1.json']

def build():
    return {'plan':plan(),'source_sha256':file_hashes(ROOT,SOURCES),'qualification':'synthetic_preparation_only',
            'runtime_dispatch_qualified':False,'new_application_executions':0,'new_primary_samples':0}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args();value=build()
    if args.verify:
        if json.loads(OUTPUT.read_bytes())!=value:raise ValueError('Mutation preparation differs')
    else:OUTPUT.write_text(json.dumps(value,indent=2)+'\n')
    print('Verified preparation: seven mutation pairs plus one reference; no runtime dispatch qualification')
