#!/usr/bin/env python3
"""Recompute descriptive branch/candidate counts; no inferential statistics."""
import csv
from collections import Counter
import hashlib
import json
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]
RW='realworld-boundaries-20261107T054749Z'
RW_REPEAT='realworld-boundaries-20261107T055116Z'
PC='petclinic-boundary-v1'
PC_REPEAT='petclinic-boundary-replay-v1'

def read(path):return json.loads((PROJECT/path).read_text())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    rw=read('results/'+RW+'/summary.json');pc=read('results/'+PC+'/summary.json')
    assert rw['status']=='completed' and len(rw['branches'])==50
    assert len(pc['branches'])==36 and len(pc['pairs'])==18
    for name,expected in rw['source_sha256'].items():assert digest(PROJECT/'results'/RW/name)==expected
    assert digest(PROJECT/'results'/RW/'registered-candidates.json')==rw['registry_sha256']
    assert digest(PROJECT/'results'/PC/'registered-candidates.json')==pc['registry_sha256']
    assert digest(PROJECT/'results'/PC/'executed_boundary_slice.mjs')==pc['runner_sha256']
    grouped={};branch_rows=[]
    for b in rw['branches']:
        r=read('results/'+RW+'/'+b['evidence']);assert r['execution_status']=='completed' and r['oracle_revision']==2
        assert b['reset_sha256']==rw['fixture_sha256'] and b['exit_code']==0
        grouped.setdefault(b['candidate_id'],{})[b['continuation']]=r
        branch_rows.append({'subject':'realworld','candidate_id':b['candidate_id'],'workflow':r['workflow'],'oracle':b['continuation'],
            'prefix_status':b['prefix_status'],'continuation_started':r['observations'][b['continuation']+'_continuation_started'],
            'outcome':b['continuation_outcome'],'evidence':'results/'+RW+'/'+b['evidence']})
    for b in pc['branches']:
        r=read('results/'+PC+'/'+b['result'])
        branch_rows.append({'subject':'petclinic','candidate_id':b['candidate_id'],'workflow':r['template'],
            'oracle':'api' if b['oracle']=='api_semantic' else 'ui','prefix_status':b['prefix_status'],
            'continuation_started':b['status']!='prefix_rejected','outcome':b['status'],'evidence':'results/'+PC+'/'+b['result']})
    assert all(p['initial_state_equal'] and p['post_prefix_state_equal'] for p in pc['pairs'])
    candidate_rows=[]
    for cid,branches in grouped.items():
        record=next(iter(branches.values()));api=branches.get('api');ui=branches.get('ui')
        candidate_rows.append({'subject':'realworld','candidate_id':cid,'workflow':record['workflow'],
            'api_outcome':api['observations']['continuation_outcome'] if api else None,
            'ui_outcome':ui['observations']['continuation_outcome'] if ui else None,
            'api_continuation_started':api['observations']['api_continuation_started'] if api else False,
            'ui_continuation_started':ui['observations']['ui_continuation_started'] if ui else False,
            'classification':'investigator_reproduced_reference_defect' if cid=='article-update-duplicate-partial'
                else 'unadjudicated_empty_reference' if cid=='article-title-whitespace'
                else 'implementation_limit_probe' if cid in ['article-title-151','profile-username-length61']
                else 'control_or_registered_boundary'})
    for pair in pc['pairs']:
        cid=pair['candidate_id']
        candidate_rows.append({'subject':'petclinic','candidate_id':cid,'workflow':pair['template'],
            'api_outcome':pair['api_status'],'ui_outcome':pair['ui_status'],
            'api_continuation_started':pair['api_status']!='prefix_rejected','ui_continuation_started':pair['ui_status']!='prefix_rejected',
            'classification':'reproduced_previously_reported_compatibility_defect' if cid=='owner_first_name_hyphen'
                else 'unresolved_domain_policy_difference' if cid in ['owner_city_whitespace','visit_description_whitespace']
                else 'control_or_registered_boundary'})
    rr=read('results/'+RW_REPEAT+'/summary.json');pr=read('results/'+PC_REPEAT+'/summary.json')
    assert rr['status']=='completed' and len(rr['branches'])==16 and len(pr['branches'])==6
    for b in rr['branches']:
        assert b['execution_status']=='completed'
        expected='returned_reference_not_resolvable' if b['candidate_id']=='article-update-duplicate-partial' else 'passed'
        assert b['continuation_outcome']==expected
    output=PROJECT/'results/development-batch-v2';output.mkdir(exist_ok=True)
    for name,rows in [('branches.csv',branch_rows),('candidates.csv',candidate_rows)]:
        with (output/name).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary={
        'stage':'exploratory_development_not_confirmatory_evaluation','local_date':'2026-11-06','timezone':'America/Los_Angeles',
        'applications':2,'workflow_templates':len({(r['subject'],r['workflow']) for r in candidate_rows}),
        'registered_case_variants':len(candidate_rows),'main_replay_branches':len(branch_rows),
        'actual_continuations_started':dict(Counter(r['oracle'] for r in branch_rows if r['continuation_started'])),
        'prefix_status_counts':dict(Counter(str(r['prefix_status']) for r in branch_rows)),
        'known_ui_compatibility_failures_reproduced':1,'other_investigator_reproduced_reference_failures':1,
        'previously_unknown_faults_established':0,'ambiguous_domain_policy_cases':2,
        'diagnostic_replay_branches':{'realworld':16,'petclinic':6},
        'main_sources':['results/'+RW+'/summary.json','results/'+PC+'/summary.json'],
        'diagnostic_sources':['results/'+RW_REPEAT+'/summary.json','results/'+PC_REPEAT+'/summary.json'],
        'excluded_from_main_counts':{'prior_realworld_narrow_oracle_branches':50,'petclinic_date_format_setup_branches':6,'earlier_positive_control_pilot_branches':10},
        'selector_comparison_run':False,'agent_experiment_run':False,'additional_cash_usd':0,
        'interpretation':'One known API-contract-valid state blocks a native UI edit while the equivalent custom API edit passes. A separate returned-reference failure is exposed by both continuations. Cases were source-guided; no prevalence, statistical superiority, or off-the-shelf tool comparison is inferred.'}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
