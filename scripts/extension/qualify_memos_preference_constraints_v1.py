#!/usr/bin/env python3
"""Offline violating-input checks against actual qualified native option inventories.
This qualifies membership measurement only, not invalid producer/UI continuation.
"""
import argparse,hashlib,json
from pathlib import Path
from memos_preference_constraints_v1 import extract,check_preferences,ROOT

def build(root):
    result=[]
    for p in sorted(Path(root).rglob('ui/observation.json')):
        o=json.loads(p.read_text())
        if o['status']!='ordinary_control_passed':raise ValueError('Unqualified source')
        for form in o['forms']:
            options=extract(form['preference_fields']);valid={'locale':'en','theme':'paper','memoVisibility':'PROTECTED','saveMediaMetadata':False}
            assert check_preferences(valid,options)=={'api_contract_signals':[],'shared_constraint_consistency_signals':[]}
            probes=[]
            for field in ['locale','theme','memoVisibility']:
                invalid={**valid,field:'study-unsupported'};signals=check_preferences(invalid,options)
                assert signals['shared_constraint_consistency_signals']==[field+':native_option']
                assert signals['api_contract_signals']==(['memoVisibility:server_enum'] if field=='memoVisibility' else [])
                probes.append({'field':field,'input':'study-unsupported','signals':signals})
            result.append({'observation_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'view':form['label'],'domain_sizes':{k:len(v) for k,v in options.items()},'negative_inputs':probes})
    if len(result)!=4:raise ValueError('Expected four qualified views')
    paths=['scripts/extension/memos_preference_constraints_v1.py','scripts/extension/qualify_memos_preference_constraints_v1.py','manifests/memos-preference-domains-v1.json']
    return {'kind':'memos_offline_option_membership_qualification_v1','source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},'views':result,'natural_defect_count':0,'scope':'Offline negative membership inputs on real qualified DOM option inventories. No impossible option is inserted into the application; invalid producer/continuation behavior remains unobserved.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--output',required=True);a=p.parse_args();v=build(a.root);target=Path(a.output)
    if target.exists():raise ValueError('Output exists')
    target.write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({'qualified_views':len(v['views']),'negative_membership_checks':sum(len(r['negative_inputs']) for r in v['views'])}))
