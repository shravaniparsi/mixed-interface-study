#!/usr/bin/env python3
"""Account for the full frozen input inventory without promoting qualification to science."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['manifests/benchmark-continuation-selection-v1.json','manifests/benchmark-gitlab-input-inventory-v1.json','manifests/benchmark-gitlab-issue-results-v1.json','manifests/benchmark-gitlab-members-controls-v3.json','manifests/benchmark-gitlab-members-correction-v3.json','manifests/benchmark-gitlab-mr-form-results-v1.json','evidence/benchmark-wikipedia-source-v1.json','evidence/benchmark-wikipedia-host-probe-v1.json','notes/benchmark_wikipedia_dependency_20261116.md','manifests/benchmark-gitlab-mr-source-results-v1.json','notes/benchmark_gitlab_mr_source_results_20261116.md']
def build():
 values={s:json.loads((ROOT/s).read_text()) for s in SOURCES if s.endswith('.json')}
 inv=values[SOURCES[1]];issue=values[SOURCES[2]];members=values[SOURCES[3]];mr=values[SOURCES[5]]
 assert inv['specification_count']==24 and issue['scheduled_execution_complete'] and issue['scheduled_specifications']==6
 assert not members['ordinary_triple_qualified'] and not mr['ordinary_write_triple_qualified']
 assert values[SOURCES[9]]['packaged_source_identity_established']
 statuses={'gitlab.issue_assignment':('scheduled_execution_complete',SOURCES[2]),'gitlab.project_members':('qualification_closed_six_specifications_unexecuted',SOURCES[3]),'gitlab.merge_request_reviewer':('qualification_closed_packaged_ce_single_reviewer_constraint',SOURCES[9]),'gitlab.repository_readme':('unqualified_original_wikipedia_content_not_recovered',SOURCES[8])}
 families=[]
 for f in inv['families']:
  name=f['family'];ids=[s['id'] for s in f['specifications']];completed=name=='gitlab.issue_assignment'
  families.append({'family':name,'frozen_specifications':ids,'scheduled_execution_complete':completed,'executed_specifications':len(ids) if completed else 0,'unexecuted_specifications':0 if completed else len(ids),'status':statuses[name][0],'evidence':statuses[name][1]})
 return {'kind':'benchmark_continuation_progress_snapshot_v3','snapshot_scope':'After closed membership qualification and packaged MR capability assessment. Not a live job-status feed.','frozen_specifications':24,'executed_specifications':sum(f['executed_specifications'] for f in families),'unexecuted_specifications':sum(f['unexecuted_specifications'] for f in families),'unexecuted_after_closed_qualification':12,'unexecuted_with_qualification_unresolved':6,'families':families,'retained_unqualified_families':inv['retained_unqualified_families'],'completed_scientific_evidence':{'workflow_count':1,'application_count':1,'scientific_branch_entries':issue['production_phase_entries'],'control_branches':issue['controls_observed'],'triples':issue['scheduled_triples'],'classifications':issue['classification_counts'],'candidate_incremental_signals':issue['candidate_incremental_signals'],'confirmed_natural_defects':issue['confirmed_natural_defects'],'job_seconds':issue['job_seconds']},'confidentiality_observation':'API/native confidentiality loss was observed, but native production failed and producer states were not matched. It remains unresolved, not a confirmed incremental defect.','interpretation':'Correlated specifications and fixed repeats are not independent defects or prevalence samples. Ordinary qualification jobs do not increase the scientific case count. Wider cohort and Q1 contribution remain unproven.','source_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES}}
def main():
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();v=build();dest=ROOT/'manifests/benchmark-progress-v3.json'
 if a.verify:assert json.loads(dest.read_text())==v
 else:dest.write_text(json.dumps(v,indent=2)+'\n')
 print('24 frozen specifications: 6 executed, 18 unexecuted; zero confirmed incremental defects in completed issue cohort.')
if __name__=='__main__':main()
