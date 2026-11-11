#!/usr/bin/env python3
"""Reconstruct fixed repeats and require their linked ordinary controls for interpretation."""
import argparse,json
from pathlib import Path
from collections import Counter
from verify_independent_grocy_category_cases_v1 import check,read,require,ROOT
REGISTRY=ROOT/'manifests/independent-grocy-category-followup-execution-v1.json'
def build(root):
    v=check(root,REGISTRY);reg=read(REGISTRY);units={u['id']:u for u in reg['units']};initial=read(ROOT/'manifests/independent-grocy-category-initial-results-v1.json');initial_records={r['case_id']:r for r in initial['records'].values()};comparison=[]
    for uid,u in units.items():
        if u['cohort']!='schema_sample':continue
        record=v['records'][uid];control=v['records'][u['linked_control_unit']];qualified=control['classification']=='both_clean' and not control['shared_signal'] and not control.get('native_representation_signal',False);original=initial_records[u['case_id']]
        comparison.append({'unit':uid,'case_id':u['case_id'],'repetition':u['repetition'],'linked_control':u['linked_control_unit'],'control_qualified':qualified,'classification':record['classification'],'channels':record['channels'],'baseline_overlap':record.get('baseline_overlap'),'matches_initial_channels':qualified and record['channels']==original['channels'],'matches_initial_overlap':qualified and record.get('baseline_overlap')==original.get('baseline_overlap')})
    require(len(comparison)==2,'Repeat inventory differs');v.update(kind='grocy_fixed_followup_results_v1',comparisons=comparison,qualified_boundary_repeat_pairs=sum(x['control_qualified'] for x in comparison),overlap_counts=dict(Counter(x['baseline_overlap'] if x['control_qualified'] else 'control_unqualified' for x in comparison)),interpretation='Exactly the registered two repeats per selected initial case. Variants and repeats are correlated. No automatic additional repeats are authorized by this result.')
    v.pop('repeat_case_ids');return v
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--output');a=p.parse_args();v=build(a.root)
    if a.output:
        target=Path(a.output);require(not target.exists(),'Output exists');target.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps({'counts':v['counts'],'overlap':v['overlap_counts']},indent=2))
