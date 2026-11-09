"""Previously exposed RealWorld representation controls with baseline references."""
from pathlib import Path
from realworld_terminal_campaign import ROOT, read, write, sha, pair_result, reducer, BASELINES
from mixed_interface.campaign_v2 import build_plan
from mixed_interface.repetition import require, job as make_job, digest

VARIATIONS={
 'article-tag-order-duplicates-control':('article-valid','tag_order_and_duplicates'),
 'profile-bio-null':('profile-bio-valid','explicit_null_bio'),
 'profile-bio-omitted':('profile-bio-valid','omitted_bio'),
}
REGISTRY_DIGEST='3a8b6c86a14462371dd03006dc3ab18938ab7c020f8166f40714051c32483d66'


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
    expected_sources={'run_realworld_pair_job_v3.py','realworld_paired_case.mjs','run_realworld_pilot.py','response_capture.mjs','realworld_integrity.mjs','phase_clock.mjs','realworld_normalization.mjs','validate_realworld_paired_controls.py','summarize_realworld_oracle_components.py','normalization.py'}
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
