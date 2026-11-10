#!/usr/bin/env python3
"""Reuse independent raw-trace reconstruction, report exploratory conditions separately."""
import argparse,json
from pathlib import Path
from collections import Counter
from verify_grocy_cases_v1 import check,require,read,ROOT
REGISTRY=ROOT/'manifests/grocy-energy-execution-v1.json'
def build(root):
    result=check(root,REGISTRY);reg=read(REGISTRY);cases={c['id']:c for c in reg['cases']};conditions={}
    for c in reg['cases']:
        rows=[v for v in result['records'].values() if v['case_id']==c['id']];require(len(rows)==3,'Condition repetition count differs');conditions[c['condition']]={'pairs':len(rows),'classifications':dict(Counter(v['classification'] for v in rows)),'baseline_overlap':dict(Counter(v.get('baseline_overlap','unresolved') for v in rows))}
    evidence=[]
    for report in sorted(Path(root).rglob('report.json')):
        pair=read(report);unit=pair['unit'];branches={}
        for channel in ['api','ui']:
            p=report.parent/channel/'observation.json'
            if not p.exists():branches[channel]={'status':'missing'};continue
            o=read(p);branches[channel]={'status':o['status'],'starting_state':o.get('prefix'),'final_state':o.get('final'),'energy_loaded':next((f['value'] for form in o['forms'] if form['label']=='loaded' for f in form['fields'] if f['name']=='calories'),None),'additional_changes':o.get('additional_field_changes'),'initial_business_state':o.get('initial_business_state')}
        evidence.append({'unit':unit['id'],'condition':cases[unit['case_id']]['condition'],'repetition':unit['repetition'],'branches':branches})
    comparisons=[]
    for repetition in [1,2,3]:
        rows=[e for e in evidence if e['repetition']==repetition];states=[b for e in rows for b in e['branches'].values()];complete=len(rows)==3 and all(b.get('starting_state') is not None for b in states)
        comparisons.append({'repetition':repetition,'starting_states_available':complete,'all_nonenergy_fields_equal':complete and all({k:v for k,v in b['starting_state'].items() if k!='calories'}=={k:v for k,v in states[0]['starting_state'].items() if k!='calories'} for b in states),'matched_initial_fixtures':complete and all(b['initial_business_state']==states[0]['initial_business_state'] for b in states)})
    result['counterfactual_comparability']=comparisons
    result['counts']={cohort:dict(Counter(v['classification'] for v in result['records'].values() if v['cohort']==cohort)) for cohort in ['valid_control','exploratory_replication']}
    result.update(kind='grocy_exploratory_energy_results_v1',conditions=conditions,condition_evidence=evidence,interpretation='Post-exposure replication and input counterfactual; repetitions are not independent mechanisms and this is not a new-defect adjudication. Fixed three pairs per condition; no outcome-triggered repeat loop for this exploratory cohort.')
    result.pop('repeat_case_ids');return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--output');a=p.parse_args();v=build(a.root)
    if a.output:
        target=Path(a.output);require(not target.exists(),'Output exists');target.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps(v['conditions'],indent=2))
