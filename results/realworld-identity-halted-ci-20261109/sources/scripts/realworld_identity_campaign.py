"""Exposed username identity variants with exact selection and reference binding."""
from pathlib import Path
from realworld_terminal_campaign import ROOT, read, write, sha, reducer, BASELINES
from mixed_interface.campaign_v2 import build_plan
from realworld_identity_bridge_v1 import pair_result
from mixed_interface.repetition import require, job as make_job, digest

VARIATIONS={'profile-username-null': ('profile-bio-valid', 'profile-username-null'), 'profile-username-empty': ('profile-bio-valid', 'profile-username-empty'), 'profile-username-length60': ('profile-bio-valid', 'profile-username-length60'), 'profile-username-length61': ('profile-bio-valid', 'profile-username-length61')}
REGISTRY_DIGEST='4590e68447b3865534a54993c266cc70c1668d22aef910bac95a8eb1d90c4117'


def plan_for(registry):
    require(digest(registry)==REGISTRY_DIGEST,'Engineering registry differs from the exact qualified selection')
    pairs=[]
    for c in registry['cases']:
        cid=c['candidate_id'];baseline=cid in BASELINES
        require(baseline or cid in VARIATIONS,'Unregistered variation')
        pairs.append({'pair_id':cid,'workflow_id':c['workflow'],'producer_interface':'api',
            'case_ids':{x:cid+'-'+x+'-r1' for x in ('api','ui')},
            'intervention':'route_only' if baseline else 'payload_mutation',
            'mutation':None if baseline else VARIATIONS[cid][1]})
    plan=build_plan(pairs)
    for p in plan['schedule']['pairs']:
        require(p['reference_control']==(p['pair_id'] if p['pair_id'] in BASELINES else VARIATIONS[p['pair_id']][0]),'Reference control differs')
    return plan


def validate_job(job,registry):
    plan=plan_for(registry);pairs=plan['schedule']['pairs'];by_id={p['pair_id']:p for p in pairs}
    allowed=list(plan['schedule']['initial_jobs'])
    for i,p in enumerate(pairs):
        for repetition in (2,3):
            allowed.append(make_job(p,f'followup-{i:03d}-r{repetition}','candidate_repeat',p['pair_id'],repetition))
            allowed.append(make_job(by_id[p['reference_control']],f'control-{i:03d}-r{repetition}','reference_control',p['pair_id'],repetition))
    require(job in allowed,'Job differs from expanded engineering schedule')
    return next(c for c in registry['cases'] if c['candidate_id']==job['pair_id'])


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
    expected_sources={'run_realworld_pair_job_v6.py','realworld_identity_case_v1.mjs','run_realworld_pilot.py','response_capture.mjs','realworld_integrity.mjs','phase_clock.mjs','realworld_normalization.mjs','validate_realworld_paired_controls.py','summarize_realworld_oracle_components.py','normalization.py','realworld_identity_v1.mjs','realworld_identity_extract_v1.py'}
    require(set(summary['source_sha256'])==expected_sources,'Runner source inventory differs')
    for name,h in summary['source_sha256'].items():
        live=ROOT/('src/mixed_interface/normalization.py' if name=='normalization.py' else 'scripts/'+name)
        require(sha(root/name)==h==sha(live),'Executed source differs: '+name)
    require(summary['backend_commit']=='87dd078c883a046f5ff20269df2fb004d8b5f83f' and summary['frontend_commit']=='b14ba5011cf9cc97babfcd7ca99dcfbb058862e7','Application revision differs')
    fixture=read(root/'fixture-references.json');branches={};evidence={'summary':sha(path),'job':sha(directory/'job.json'),'execution':sha(directory/'execution.json')}
    for b in summary['branches']:
        require(b['evidence']==b['case_id']+'.json','Unexpected evidence path')
        raw=read(root/b['evidence']);reducer.validate_timing(raw,b)
        require(b['candidate_id']==spec['candidate_id'] and raw['candidate_id']==spec['candidate_id'] and raw['continuation_interface']==b['continuation'],'Raw branch identity differs')
        branches[b['continuation']]=(raw,b);evidence[b['evidence']]=sha(root/b['evidence'])
    return pair_result(job,branches,spec,fixture,summary['fixture_sha256'],True,evidence)
