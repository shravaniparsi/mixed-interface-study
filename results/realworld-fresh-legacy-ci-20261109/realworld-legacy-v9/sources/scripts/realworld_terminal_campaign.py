"""Baseline-only RealWorld job binding and terminal pair extraction."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.campaign_v2 import build_plan
from mixed_interface.repetition import require, job as make_job
from mixed_interface.terminal_outcomes import terminal
from realworld_terminal_outcomes import classify_branch, reducer

BASELINES=('article-valid','comment-body-valid','profile-bio-valid','article-update-unique-partial')
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')


def plan_for(registry):
    require(registry.get('kind')=='prospective_runner_engineering_controls','Unsupported registry')
    pairs=[]
    for cid in BASELINES:
        matches=[c for c in registry['cases'] if c['candidate_id']==cid]
        require(len(matches)==1,'Missing or duplicate baseline')
        c=matches[0]
        require(c['prefix_interface']=='api' and set(c['continuations'])=={'api','ui'} and c['expectation']['outcome']=='accept','Changed baseline route or expectation')
        pairs.append({'pair_id':cid,'workflow_id':c['workflow'],'producer_interface':'api',
                      'case_ids':{x:cid+'-'+x+'-r1' for x in ('api','ui')},'intervention':'route_only','mutation':None})
    return build_plan(pairs)


def validate_job(job,registry):
    plan=plan_for(registry)
    allowed=list(plan['schedule']['initial_jobs'])
    for i,p in enumerate(plan['schedule']['pairs']):
        for repetition in (2,3):
            allowed.append(make_job(p,f'followup-{i:03d}-r{repetition}','candidate_repeat',p['pair_id'],repetition))
            allowed.append(make_job(p,f'control-{i:03d}-r{repetition}','reference_control',p['pair_id'],repetition))
    require(job in allowed,'Job differs from baseline schedule')
    return next(c for c in registry['cases'] if c['candidate_id']==job['pair_id'])


def pair_result(job, branches, spec, fixture, fixture_sha, cleanup, evidence):
    classified={c:classify_branch(raw,run,spec,fixture=fixture,cleanup_confirmed=cleanup)
                for c,(raw,run) in branches.items()}
    kinds=[v['kind'] for v in classified.values()]
    gates={}
    complete={'clean_observation','completed_mismatch','matched_rejection','unresolved_policy'}
    if set(branches)=={'api','ui'} and all(k in complete for k in kinds):
        a,ar=branches['api'];u,ur=branches['ui']
        def command(raw,stage):
            values=[g['observed'] for g in raw['integrity']['guards'] if g['name']=='submitted_command' and g['stage']==stage]
            return values[0] if len(values)==1 else None
        accepted=all(classified[c]['components']['accepted_prefix'] for c in branches)
        gates={'same_actor':a['actor']==u['actor'],
               'same_pre_state':a['integrity']['before']==u['integrity']['before'],
               'same_prefix_command':command(a,'prefix') is not None and command(a,'prefix')==command(u,'prefix'),
               'same_prefix_status':a['observations']['prefix_status']==u['observations']['prefix_status'],
               'same_reset':bool(fixture_sha) and ar.get('reset_sha256')==ur.get('reset_sha256')==fixture_sha,
               'distinct_branches':ar['case_id']!=ur['case_id'] and ar['evidence']!=ur['evidence'],
               'same_prefix_state':not accepted or a.get('prefix_state')==u.get('prefix_state'),
               'same_consumer_command':not accepted or (command(a,'continuation') is not None and command(a,'continuation')==command(u,'continuation'))}
    prefix_values=[v.get('components',{}).get('accepted_prefix') for v in classified.values()]
    prefix='unobserved' if not prefix_values or None in prefix_values else 'accepted' if all(prefix_values) else 'rejected' if not any(prefix_values) else 'mixed'
    kind=next((k for k in ('cleanup_unconfirmed','interrupted','case_timeout','environment_failure','missing_evidence') if k in kinds),None)
    if not cleanup:kind='cleanup_unconfirmed'
    if kind is None and set(branches)!={'api','ui'}:kind='missing_evidence'
    if kind is None and (not gates or not all(gates.values()) or prefix=='mixed'):kind='incomparable_observation'
    if kind is None:kind='completed_mismatch' if 'completed_mismatch' in kinds else 'unresolved_policy' if 'unresolved_policy' in kinds else 'clean_observation' if prefix=='accepted' else 'matched_rejection'
    comparable=bool(gates) and all(gates.values()) and kind in complete
    signals={c: v['components']['components']['assigned_api_continuation' if c=='api' else 'assigned_native_continuation']['mismatch_observed'] for c,v in classified.items() if 'components' in v}
    # Stable signatures retain registered predicate outcomes, not generated timestamps/IDs.
    signature={'kinds':{c:v['kind'] for c,v in classified.items()},'gates':gates,
               'checks':{c:{name:[[x['id'],x['passed'],x['scope']] for x in p['checks']] for name,p in v['components']['components'].items()} for c,v in classified.items() if 'components' in v}}
    outcome={'job_id':job['job_id'],'execution':'complete' if comparable else 'incomplete','prefix':prefix,
             'channel_discrepancy':signals.get('api')!=signals.get('ui') if comparable else None,
             'check_failure':'completed_mismatch' in kinds if comparable else None,
             'cleanup_confirmed':cleanup and 'cleanup_unconfirmed' not in kinds,'observation_signature':signature}
    return {'terminal':terminal(outcome,kind,evidence),'comparability':gates,'branches':classified}


def read_job(directory,job,registry,execution):
    directory=Path(directory);spec=validate_job(job,registry)
    require(execution.get('exit_confirmed') is True and not execution.get('errors') and execution.get('returncode')==0,'Runner exit not clean')
    summaries=list((directory/'run').glob('*/summary.json'))
    require(len(summaries)==1,'Expected one job summary')
    path=summaries[0];root=path.parent;summary=read(path)
    require(summary['job']==job and summary['job_sha256']==sha(directory/'job.json'),'Executed job differs')
    require(read(root/'registered-candidates.json')==registry and summary['registry_sha256']==sha(root/'registered-candidates.json'),'Registry differs')
    require(summary['status']=='completed' and summary['frontend_exit_confirmed'] is True,'Incomplete job')
    expected=[b['case_id'] for b in job['branches']]
    require([b['case_id'] for b in summary['branches']]==expected,'Branch order differs')
    require(summary['schedule']==[{'candidate_id':spec['candidate_id'],'order':[b['continuation'] for b in job['branches']]}],'Declared order differs')
    expected_sources={'run_realworld_pair_job_v2.py','realworld_paired_case.mjs','run_realworld_pilot.py','response_capture.mjs','realworld_integrity.mjs','phase_clock.mjs','realworld_normalization.mjs','validate_realworld_paired_controls.py','summarize_realworld_oracle_components.py','normalization.py'}
    require(set(summary['source_sha256'])==expected_sources,'Runner source inventory differs')
    for name,h in summary['source_sha256'].items():
        live=ROOT/('src/mixed_interface/normalization.py' if name=='normalization.py' else 'scripts/'+name)
        require(sha(root/name)==h==sha(live),'Executed source differs: '+name)
    fixture=read(root/'fixture-references.json');branches={};evidence={'summary':sha(path),'job':sha(directory/'job.json'),'execution':sha(directory/'execution.json')}
    for b in summary['branches']:
        require(b['evidence']==b['case_id']+'.json','Unexpected evidence path')
        raw=read(root/b['evidence']);reducer.validate_timing(raw,b)
        branches[b['continuation']]=(raw,b);evidence[b['evidence']]=sha(root/b['evidence'])
    return pair_result(job,branches,spec,fixture,summary['fixture_sha256'],True,evidence)
