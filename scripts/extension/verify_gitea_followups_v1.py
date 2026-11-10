#!/usr/bin/env python3
"""Fixed followups: independent reconstruction plus original-result comparison."""
import argparse,json
from pathlib import Path
from verify_gitea_cases_v1 import build as rebuild,read,sha,need,ROOT

def build(root):
    reg=ROOT/'manifests/gitea-followup-execution-v1.json';v=rebuild(root,reg);first=read(ROOT/'manifests/gitea-initial-results-v1.json');comparisons=[]
    for uid,r in v['records'].items():
        u=r['unit']
        if u['cohort']!='boundary':continue
        need(u['case_id'] in first['followup_candidates'] and u['repetition'] in [2,3],'Registered repetition');original=first['records'][u['case_id']]
        comparisons.append(dict(unit=uid,case_id=u['case_id'],repetition=u['repetition'],linked_control=u['linked_valid_control'],control_qualified=r['linked_valid_qualified'],qualified=r['qualified'],category=r['category'],matches_initial_outcomes=r['qualified'] and r['outcomes']==original['outcomes'],matches_initial_overlap=r['qualified'] and all(r[k]==original[k] for k in ['api_signal','native_signal','native_only_signal'])))
    need({(c['case_id'],c['repetition']) for c in comparisons}=={(cid,n) for cid in first['followup_candidates'] for n in [2,3]},'Complete finite repeat schedule')
    v.update(kind='gitea_fixed_followup_results_v1',followup_verifier_sha256=sha(__file__),comparisons=comparisons,qualified_boundary_repeat_pairs=sum(c['qualified'] for c in comparisons),further_repeats_authorized=False);v.pop('followup_candidates');return v
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--output',type=Path);a=p.parse_args();v=build(a.root)
    if a.output:need(not a.output.exists(),'Output exists');a.output.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps({k:v[k] for k in ['run_identity','counts','missing_units','qualified_boundary_repeat_pairs','native_only_signals']},indent=2));print('Matched initial outcomes:',sum(c['matches_initial_outcomes'] for c in v['comparisons']))
