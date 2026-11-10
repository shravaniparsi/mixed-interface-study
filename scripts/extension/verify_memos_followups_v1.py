#!/usr/bin/env python3
"""Reconstruct bounded repeats from raw observations and linked ordinary controls."""
import argparse,json
from collections import Counter
from pathlib import Path
import verify_memos_cases_v1 as initial_verifier
ROOT=initial_verifier.ROOT
REGISTRY=ROOT/'manifests/memos-followup-execution-v1.json'
def build(root):
    prior=initial_verifier.REGISTRY
    try:
        initial_verifier.REGISTRY=REGISTRY
        result=initial_verifier.build(root)
    finally:initial_verifier.REGISTRY=prior
    reg=initial_verifier.read(REGISTRY);initial=initial_verifier.read(ROOT/'manifests/memos-initial-results-v1.json')
    originals={v['case_id']:v for v in initial['records'].values()};comparisons=[]
    for u in reg['units']:
        if u['cohort']!='boundary':continue
        r=result['records'][u['id']];c=result['records'][u['linked_control_unit']];original=originals[u['case_id']]
        qualified=c['classification']=='both_clean' and c['baseline_overlap']=='neither' and not c['repeat_required']
        comparisons.append(dict(unit=u['id'],case_id=u['case_id'],repetition=u['repetition'],linked_control=u['linked_control_unit'],control_qualified=qualified,classification=r['classification'],baseline_overlap=r['baseline_overlap'],matches_initial_channels=qualified and r['channels']==original['channels'],matches_initial_overlap=qualified and r['baseline_overlap']==original['baseline_overlap']))
    initial_verifier.need(len(comparisons)==24,'Fixed repeat inventory')
    result.update(kind='memos_fixed_followup_results_v1',comparisons=comparisons,qualified_boundary_repeat_pairs=sum(c['control_qualified'] for c in comparisons),overlap_counts=dict(Counter(c['baseline_overlap'] if c['control_qualified'] else 'control_unqualified' for c in comparisons)),interpretation='Two registered repeats per selected initial case. Variants and repeats are correlated. No automatic additional repeats.')
    result.pop('repeat_case_ids');return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--output');a=p.parse_args();v=build(a.root)
    if a.output:
        target=Path(a.output);initial_verifier.need(not target.exists(),'Output exists');target.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps({'counts':v['counts'],'overlap':v['overlap_counts']},indent=2))
