#!/usr/bin/env python3
"""Reconstruct registered triples; report candidate signals, never confirm defects."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BRANCHES=('native_native','api_native','api_api')
HEAD='fd613571c9341f9a8a1a46253877b0d586121a28'
TITLE='Integrating LLMs for better prompts'

def semantic_pass(row):
    if not row or 'producer_state' not in row or 'final_state' not in row:return False
    before=row['producer_state'];patch=row['optional_field_patch']
    intent=(before.get('title')==TITLE and before.get('project_id')==183 and before.get('confidential')==(patch.get('confidential',False)) and before.get('assignee_ids')==[] and before.get('due_date') is None)
    if patch.get('description'):intent=intent and before.get('description')==patch['description']
    if patch.get('description')=='':intent=intent and before.get('description') in ('',None)
    return intent and row['final_state']==dict(before,assignee_ids=[2264],due_date='2033-04-01')

def qualified_branch(row):
    return bool(row and row.get('case_passed') and row.get('browser_cleanup_confirmed') and row.get('preflight',{}).get('exact_title_count')==0 and row.get('preflight',{}).get('may_be_truncated') is False and semantic_pass(row))

def classify_triple(rows,controls_passed):
    complete=all(rows.get(b) for b in BRANCHES)
    before=[rows[b].get('producer_state') for b in BRANCHES] if complete else []
    states_equal=bool(before and all(v is not None and v==before[0] for v in before))
    setup_equal=complete and len({rows[b].get('assignee_membership_setup') for b in BRANCHES})==1 and rows[BRANCHES[0]].get('assignee_membership_setup') in ('added_developer','already_authorized')
    passed={b:qualified_branch(rows.get(b)) for b in BRANCHES}
    candidate=False
    if not complete:category='incomplete_triple'
    elif not controls_passed:category='unqualified_batch_controls'
    elif not setup_equal:category='setup_mismatch_or_failure'
    elif not all(rows[b].get('preflight',{}).get('exact_title_count')==0 and rows[b].get('preflight',{}).get('may_be_truncated') is False and rows[b].get('actor')=={'id':2330,'username':'byteblaze'} for b in BRANCHES):category='reset_or_actor_verification_failure'
    elif any(v is None for v in before):category='producer_rejection_or_instrument_failure'
    elif not states_equal:category='producer_state_mismatch'
    elif all(passed.values()):category='all_paths_preserve'
    else:
        native=rows['api_native']
        persisted_failure='final_state' in native and not semantic_pass(native)
        http_failure=any(r.get('status',0)>=400 and r.get('path')==f"/byteblaze/empathy-prompts/-/issues/{native.get('issue_iid')}" for r in native.get('native_writes',[])) and native.get('stage')=='continuation'
        candidate=passed['native_native'] and passed['api_api'] and not passed['api_native'] and (persisted_failure or http_failure)
        category='candidate_incremental_signal_requires_review' if candidate else 'continuation_or_instrument_failure'
    return {'classification':category,'producer_states_equal':states_equal,'setup_equal':bool(setup_equal),'branch_pass':passed,'candidate_incremental_signal':bool(candidate),'confirmed_natural_defect':False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    archive=args.archive.resolve();run=json.loads((archive/'run.json').read_text());assert run['status']=='completed' and run['headSha']==HEAD
    reg=json.loads((ROOT/'manifests/benchmark-gitlab-issue-execution-v1.json').read_text())
    specifications={s['id']:s for s in reg['cases']};jobs={j['name']:j for j in run['jobs']}
    assert set(jobs)=={'execute (1)','execute (2)'}
    result={'kind':'benchmark_gitlab_issue_results_v1','run_id':43284543994,'head_sha':HEAD,'scheduled_specifications':6,'scheduled_triples':12,'scheduled_scientific_branches':36,'scheduled_control_branches':4,'repetitions':[],'triples':[],'production_phase_entries':0,'controls_observed':0,'job_seconds':0,'paid_model_calls':0,'confirmed_natural_defects':0,'other_frozen_specifications_pending':18}
    containers=[]
    for rep in (1,2):
        job=jobs[f'execute ({rep})'];seconds=(datetime.fromisoformat(job['completedAt'].replace('Z','+00:00'))-datetime.fromisoformat(job['startedAt'].replace('Z','+00:00'))).total_seconds();result['job_seconds']+=seconds
        folder=archive/f'gitlab-issue-inputs-r{rep}-43284543994'
        batch=json.loads((folder/'batch.json').read_text()) if (folder/'batch.json').exists() else None
        scheduled=next(s for s in reg['schedules'] if s['repetition']==rep)['executions'];rows={};entries={}
        if batch:
            assert batch['source_commit']==HEAD and batch['repetition']==rep
            for entry in batch['executions']:
                i=entry['index'];expected=scheduled[i]
                assert all(entry[k]==expected[k] for k in ('case_id','branch','role'))
                if entry.get('container_id'):containers.append(entry['container_id'])
                path=folder/entry['folder']/'issue-case.json';row=json.loads(path.read_text()) if path.exists() else None
                entries[(entry['case_id'],entry['branch'])]=entry
                if row:
                    assert row['case_id']==entry['case_id'] and row['branch']==entry['branch'] and row['case_role']==entry['role']
                    assert row['optional_field_patch']==specifications[row['case_id']]['optional_field_patch']
                    result['production_phase_entries']+=row['scientific_cases_executed']
                    if entry['role']=='control':result['controls_observed']+=1
                    rows[(entry['case_id'],entry['branch'])]=row
        def usable(key):
            entry=entries.get(key,{})
            return bool(entry.get('container_id')) and entry.get('container_removed') is True and entry.get('browser_cleanup_confirmed') is True and entry.get('process_exit_code')==0
        controls_passed=bool(batch and batch['status']=='completed' and all(qualified_branch(rows.get((name,'native_native'))) and usable((name,'native_native')) for name in ('control_start','control_end')))
        result['repetitions'].append({'repetition':rep,'job_conclusion':job['conclusion'],'job_seconds':seconds,'batch_status':batch['status'] if batch else 'missing_batch','controls_passed':controls_passed,'recorded_executions':len(entries)})
        for case in [c for c in reg['cases'] if c['role']=='scientific']:
            group={b:rows.get((case['id'],b)) for b in BRANCHES}
            verdict=classify_triple(group,controls_passed)
            # Recorded scientific failures remain visible; a successful classification
            # additionally requires a clean process and cleanup in every branch.
            if verdict['classification']=='all_paths_preserve' and not all(usable((case['id'],b)) for b in BRANCHES):verdict['classification']='process_or_cleanup_failure'
            verdict.update(repetition=rep,case_id=case['id'],observed_branches=[b for b in BRANCHES if group[b]])
            result['triples'].append(verdict)
    result['container_count']=len(containers);result['container_ids_unique']=len(set(containers))==len(containers)
    assert result['container_ids_unique'],'Fresh-container identity reused'
    result['classification_counts']=dict(Counter(t['classification'] for t in result['triples']))
    result['candidate_incremental_signals']=sum(t['candidate_incremental_signal'] for t in result['triples'])
    result['scheduled_execution_complete']=result['production_phase_entries']==36 and result['controls_observed']==4 and all(r['controls_passed'] and r['recorded_executions']==20 for r in result['repetitions'])
    result['scope']='Six correlated specifications in one GitLab workflow, fixed repeats; not population prevalence, distinct defect counts, or completion of the wider cohort.'
    result['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(archive.rglob('*')) if p.is_file()}
    target=ROOT/'manifests/benchmark-gitlab-issue-results-v1.json'
    if args.verify:assert json.loads(target.read_text())==result
    else:target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_sha256','triples')},indent=2))
if __name__=='__main__':main()
