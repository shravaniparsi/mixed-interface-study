#!/usr/bin/env python3
"""Rebuild the complete bounded independent-input study, with exclusions visible."""
import argparse,hashlib,importlib,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUNS=[('grocy.task_category','initial','43071019063','verify_independent_grocy_category_cases_v1','manifests/independent-grocy-category-execution-v1.json','manifests/independent-grocy-category-initial-results-v1.json','results/independent-grocy-category-cases-v1-ci-43071019063'),('grocy.task_category','followup','43072084690','verify_independent_grocy_category_followups_v1',None,'manifests/independent-grocy-category-followup-results-v1.json','results/independent-grocy-category-followups-v1-ci-43072084690'),('paperless.storage_path','initial','43072645323','verify_independent_paperless_storage_cases_v2','manifests/independent-paperless-storage-execution-v2.json','manifests/independent-paperless-storage-initial-results-v2.json','results/independent-paperless-storage-cases-v2-ci-43072645323'),('gitea.repository_settings','initial','43075912184','verify_independent_gitea_repo_cases_v1','manifests/independent-gitea-repo-execution-v1.json','manifests/independent-gitea-repo-initial-results-v1.json','results/independent-gitea-repo-cases-v1-ci-43075912184')]
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def build():
    inventory=read(ROOT/'manifests/independent-api-input-inventory-v1.json');rows=[];initial=[];followups=[];sources={};repeat_requests=[];completed_repeats=[]
    for workflow,phase,run,module,registry,proof,folder in RUNS:
        m=importlib.import_module(module);v=m.check(ROOT/folder,ROOT/registry) if registry else m.build(ROOT/folder);assert v==read(ROOT/proof),'Saved proof differs: '+proof;sources[proof]=sha(ROOT/proof)
        records=list(v['records'].values());(initial if phase=='initial' else followups).extend(records)
        rows.append(dict(workflow=workflow,phase=phase,run_id=run,pairs=len(records),counts=v['counts'],native_only_detections=sum(r.get('baseline_overlap')=='native_only' for r in records),proof=proof))
        if phase=='initial':repeat_requests+=v['repeat_case_ids']
        else:
            for x in v['comparisons']:assert x['control_qualified'] and x['matches_initial_channels'] and x['matches_initial_overlap'];completed_repeats.append((x['case_id'],x['repetition']))
    assert Counter(c for c,r in completed_repeats)==Counter({c:2 for c in repeat_requests})
    assert all({r for c,r in completed_repeats if c==case}=={2,3} for case in repeat_requests)
    sample=[r for r in initial if r['cohort']=='schema_sample'];controls=[r for r in initial if r['cohort']=='valid_control'];assert len(sample)==28 and len(controls)==12 and len(followups)==4
    assert all(r['classification']=='both_clean' and not r['shared_signal'] for r in controls)
    for module,proof in [('build_independent_category_mechanism_v1','manifests/independent-grocy-category-mechanism-v1.json'),('build_independent_custom_exclusion_v1','manifests/independent-paperless-custom-exclusion-v1.json'),('build_independent_storage_fixture_v2','manifests/independent-paperless-storage-inputs-v2.json'),('build_independent_input_cost_v1','manifests/independent-input-cost-v1.json')]:
        assert importlib.import_module(module).build()==read(ROOT/proof);sources[proof]=sha(ROOT/proof)
    filtered=read(ROOT/'manifests/independent-vikunja-filter-exclusion-v1.json')
    for p,h in filtered['source_sha256'].items():assert sha(ROOT/p)==h
    sources['manifests/independent-vikunja-filter-exclusion-v1.json']=sha(ROOT/'manifests/independent-vikunja-filter-exclusion-v1.json')
    selected={x['id'] for x in inventory['selected']};executed={x['case_id'] for x in sample};unexecuted=sorted(selected-executed);assert len(unexecuted)==16 and len(executed)==28
    funnel=[dict(workflow=w['id'],status=('complete_corrected_fixture_cohort' if w['id']=='paperless.storage_path' else 'complete') if w['id'] in {r['workflow'] for r in rows} else 'excluded_schema_scope' if w['id']=='grocy.shopping_list' else 'excluded_frozen_ordinary_control',selected_inputs=sum(c['workflow']==w['id'] for c in inventory['selected']),executed_initial_inputs=sum(c['id'] in executed for c in inventory['selected'] if c['workflow']==w['id'])) for w in inventory['workflows']]
    return dict(kind='independent_input_complete_summary_v1',workflow_selection=funnel,selected_inputs=len(selected),executed_initial_inputs=len(sample),unexecuted_selected_input_ids=unexecuted,initial_sample_counts=dict(Counter(r['classification'] for r in sample)),initial_sample_overlap=dict(Counter(r.get('baseline_overlap','not_eligible') for r in sample)),initial_valid_control_pairs=len(controls),followup_case_pairs=sum(r['cohort']=='schema_sample' for r in followups),followup_valid_control_pairs=sum(r['cohort']=='valid_control' for r in followups),total_scientific_pairs=len(initial)+len(followups),all_required_repeats_complete=True,native_only_detections=sum(r.get('baseline_overlap')=='native_only' for r in sample),natural_defects_confirmed=0,runs=rows,source_sha256=sources,scope='Purposive scalar API-schema inputs in previously exposed applications. Three of six candidate workflows reached scientific execution. Storage uses a disclosed post-qualification identity correction; original owner-ID1 subgroup is unexecuted. Custom-field metadata rewriting and saved-filter creation rejection are qualification exclusions, not scientific detections. No pooling with the earlier production extension, no prevalence estimate and no agent-performance claim.',publication_assessment='The bounded comparison is complete and reproducible. It provides no incremental native-only detection in this sample and does not establish a novel detector advantage or sufficient Q1-journal contribution by itself.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();target=ROOT/'manifests/independent-input-summary-v1.json';v=build()
    if a.verify:assert read(target)==v
    else:assert not target.exists();target.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps({k:v[k] for k in ['selected_inputs','executed_initial_inputs','initial_sample_counts','total_scientific_pairs','native_only_detections','all_required_repeats_complete']},indent=2))
