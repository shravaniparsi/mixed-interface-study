#!/usr/bin/env python3
"""Independent source, command, normalization and timing checks for hosted controls."""
import argparse,hashlib,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.normalization import exact,article_create,article_body_update,profile_update
from summarize_realworld_oracle_components import capture_integrity_issues,execution_integrity_issues

def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(value,message):
    if not value:raise ValueError(message)
def timeline(spans,total):
    require(bool(spans),'Missing timing spans');previous=0
    for s in spans:
        require(all(type(s[k]) in (int,float) and math.isfinite(s[k]) for k in ('start_s','end_s')),'Invalid timestamp')
        require(s['start_s']==previous and s['end_s']>=s['start_s'],'Gapped or overlapping exclusive spans');previous=s['end_s']
    require(math.isfinite(total) and abs(previous-total)<1e-9,'Timing total differs')

def validate(directory):
    summary=read(directory/'summary.json');registry=read(ROOT/'manifests/realworld-paired-controls-v1.json')
    require(summary['status']=='completed' and summary['frontend_exit_confirmed'],'Incomplete campaign/cleanup')
    require(sha(directory/'registered-candidates.json')==sha(ROOT/'manifests/realworld-paired-controls-v1.json')==summary['registry_sha256'],'Registry mismatch')
    for name,h in summary['source_sha256'].items():
        current=ROOT/('src/mixed_interface' if name=='normalization.py' else 'scripts')/name
        require(sha(directory/name)==h==sha(current),'Source mismatch '+name)
    schedule=[{'candidate_id':c['candidate_id'],'order':['api','ui'] if i%2==0 else ['ui','api']} for i,c in enumerate(registry['cases'])]
    require(summary['schedule']==schedule,'Schedule differs')
    expected=[(s['candidate_id'],channel) for s in schedule for channel in s['order']]
    require([(b['candidate_id'],b['continuation']) for b in summary['branches']]==expected,'Missing/reordered branches')
    require(len(summary['pairs'])==7 and all(p['valid'] and all(p['comparability'].values()) for p in summary['pairs']),'Invalid pair')
    fixture=read(directory/'fixture-references.json');rows=[];by_pair={}
    for branch in summary['branches']:
        raw=read(directory/branch['evidence']);spec=next(c for c in registry['cases'] if c['candidate_id']==branch['candidate_id'])
        require(branch['status']=='passed' and branch['backend_exit_confirmed'] and branch['reset_sha256']==summary['fixture_sha256'],'Branch/reset/cleanup failed')
        issues=capture_integrity_issues(raw,required=True)+execution_integrity_issues(raw,required=True)
        require(not issues,'Capture/integrity issues: '+str(issues))
        require(raw['checks'] and all(c['passed'] is True for c in raw['checks']),'Failed/missing business checks')
        require(raw['normalization_policy']=='normalization-policy-v1','Wrong normalization policy')
        actual=raw['prefix_state'];payload=spec['prefix_payload'];workflow=spec['workflow']
        if workflow=='article-create-edit':wanted=article_create(payload);actual={k:actual[k] for k in wanted}
        elif workflow=='article-update-comment':
            before=fixture[spec['target_fixture']];wanted=article_body_update({k:before[k] for k in ('title','description','body','tagList')},payload);actual={k:actual[k] for k in wanted}
        elif workflow=='profile-update-edit':wanted=profile_update(raw['integrity']['before']['data']['user'],payload)
        else:wanted={'body':payload['body'],'author':'pilotresearch'};actual={k:actual[k] for k in wanted}
        require(exact(wanted,actual),'Prefix normalization differs')
        timeline(branch['timing'],branch['total_s']);timeline(raw['timing']['spans'],raw['timing']['total_s'])
        require(set(raw['timing']['totals_s']) >= {'producer','assigned_continuation','shared_verification','authentication_session'},'Missing core phase')
        require(abs(sum(raw['timing']['totals_s'].values())-raw['timing']['total_s'])<1e-8,'Adapter phase totals differ')
        process=next(s for s in branch['timing'] if s['phase']=='adapter_process')
        residual=process['end_s']-process['start_s']-raw['timing']['total_s']
        require(residual>=0 and abs(residual-branch['adapter_uninstrumented_process_s'])<1e-9,'Parent/child timing mismatch')
        by_pair.setdefault(branch['candidate_id'],{})[branch['continuation']]=raw
        rows.append({'case_id':branch['case_id'],'observation_sha256':sha(directory/branch['evidence']),'total_s':branch['total_s'],'adapter_phases_s':raw['timing']['totals_s'],'uninstrumented_process_s':residual,'checks':len(raw['checks']),'guards':len(raw['integrity']['guards'])})
    for members in by_pair.values():
        a,u=members['api'],members['ui']
        require(a['prefix_state']==u['prefix_state'] and a['actor']==u['actor'] and a['integrity']['before']==u['integrity']['before'],'Pair state/actor differs')
        for stage in ('prefix','continuation'):
            commands=[[g['observed'] for g in r['integrity']['guards'] if g['stage']==stage and g['name']=='submitted_command'] for r in (a,u)]
            require(len(commands[0])==len(commands[1])==1 and commands[0]==commands[1],'Pair command differs')
    return {'status':'verified','source_commit':summary['source_commit'],'branches':len(rows),'pairs':len(by_pair),'cases':rows,'summary_sha256':sha(directory/'summary.json'),'primary_freeze_complete':False,'selector_calibration':False}
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path);args=parser.parse_args()
    paths=list(args.root.glob('*/summary.json'));require(len(paths)==1,'Expected one complete attempt')
    result=validate(paths[0].parent);(args.root/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'branches':result['branches'],'pairs':result['pairs']}))
