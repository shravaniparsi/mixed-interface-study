#!/usr/bin/env python3
"""Reconstruct repository continuation outcomes from complete recorded state."""
import argparse,hashlib,json
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(v,m):
    if not v:raise ValueError(m)
def business(v):
    x=json.loads(json.dumps(v));x.pop('created_at',None);x.pop('updated_at',None)
    if x.get('owner'):
        x['owner'].pop('created',None);x['owner'].pop('last_login',None)
    return x
def preserved(v):return {k:x for k,x in v.items() if k!='updated_at'}
def classify(status,after,before,expected):
    if status is not None and 200<=status<400:
        return 'clean_preserving_continuation' if preserved(after)==preserved(expected) else 'requested_edit_not_persisted' if preserved(after)==preserved(before) else 'preservation_or_edit_discrepancy'
    if preserved(after)!=preserved(before):return 'failed_write_state_change'
    return 'blocked_save' if status in [400,409,422] else 'execution_unknown'
def violations(v,trust,reg):
    out=[]
    if type(v['name'])is not str or len(v['name'])==0:out.append('name')
    for k,limit in [('description',2048),('website',1024)]:
        if type(v[k])is not str or len(v[k])>limit:out.append(k)
    if type(v['template'])is not bool:out.append('template')
    if trust not in reg['trust_models']:out.append('trust_model')
    return out
def check(root,registry):
    reg=read(registry);units={u['id']:u for u in reg['units']};cases={c['id']:c for c in reg['cases']};spec=reg['workflows'][0];records={};runs=set();commits=set()
    for p,h in {**reg['source_sha256'],**reg['qualification_sha256']}.items():need(sha(ROOT/p)==h,'Frozen source '+p)
    for p in sorted(Path(root).rglob('report.json')):
        r=read(p);u=r['unit'];uid=u['id'];need(uid in units and u==units[uid] and uid not in records,'Unit');need(r['registry_sha256']==sha(registry),'Registry');need(r['files_sha256']=={str(q.relative_to(p.parent)):sha(q) for q in p.parent.rglob('*') if q.is_file() and q.name!='report.json'},'Raw inventory');runs.add(r['run_identity']);commits.add(r['source_commit']);c=cases[u['case_id']]
        row={'case_id':c['id'],'cohort':u['cohort'],'report_sha256':sha(p),'classification':'unresolved','channels':{},'shared_signal':False,'repeat_required':True};records[uid]=row
        if r['status']!='pair_observed' or not r.get('cleanup_confirmed'):row['error']=r.get('error','Incomplete observation');continue
        need(r['image']['id']==reg['image_id'],'Image');observations=[]
        for channel in ['api','ui']:
            o=read(p.parent/channel/'observation.json');observations.append(o);need(o['status']=='observed' and o['browser_cleanup_confirmed'] and o['case_id']==c['id'] and o['channel']==channel and o['workflow']==spec['id'],'Observation');qs=o['requests'];versions=[q for q in qs if q['path']=='/api/v1/version'];actors=[q for q in qs if q['path']=='/api/v1/user'];need(len(versions)==1 and versions[0]['status']==200 and versions[0]['response']['version']==reg['version'],'Version');need(len(actors)==1 and actors[0]['status']==200 and {k:actors[0]['response'][k] for k in ['id','login','is_admin']}==o['actor'] and o['actor']['login']=='study-actor' and o['actor']['is_admin'] is False,'Actor')
            lists=[q for q in qs if q['method']=='GET' and q['path']=='/api/v1/user/repos'];need(lists and lists[0]['status']==200 and lists[0]['response']==[] and o['initial_business_state']=={'actor':o['actor'],'resources':[]},'Reset state');made=[q for q in qs if q['method']=='POST' and q['path']=='/api/v1/user/repos'];need(len(made)==1 and made[0]['body']==c['payload'],'Frozen producer');made=made[0];need(made['status']==o['producer_status'],'Producer status')
            if made['status']!=201:
                need(len(lists)==2 and lists[1]['status']==200,'Rejected-write readback');same=lists[1]['response']==[];need(o['collection_unchanged']==same,'Collection comparison');expected='rejected_without_visible_write' if same and made['status'] in [400,409,422] else 'unresolved';need(o['prefix_status']==expected,'Producer classification');row['channels'][channel]='producer_rejected' if expected=='rejected_without_visible_write' else 'execution_unknown';continue
            created=made['response'];need(type(created['id'])is int and created['owner']['id']==o['actor']['id'] and created['full_name']=='study-actor/'+created['name'],'Resource identity');path='/api/v1/repos/'+created['full_name'];reads=[q for q in qs if q['method']=='GET' and q['path']==path];need(len(reads)==2 and all(q['status']==200 for q in reads),'Complete readback');before,after=[q['response'] for q in reads];need(before==o['prefix'] and after==o['final'] and business(before)==o['prefix_business'] and business(after)==o['final_business'],'Raw/paired projection');expected={**before,'description':spec['edit_value']};body={k:expected[k] for k in spec['fields']}
            shared=o['shared_state_observations'];need([x['phase'] for x in shared]==['before','after'] and all(x['path']=='/'+created['full_name']+'/settings' and [v['value'] for v in x['options'] if v['checked']]==[x['trust_model']] for x in shared),'Shared trust measurements');failures=violations(before,shared[0]['trust_model'],reg);need(failures==o['shared_violations'],'Shared baseline');row['shared_signal']|=bool(failures)
            if channel=='api':
                writes=[q for q in qs if q['method']=='PATCH'];need(len(writes)==1 and writes[0]['path']==path and writes[0]['body']==body,'Full native-write projection');status=writes[0]['status']
            else:
                writes=o['native_requests'];need(len(writes)<=1,'Native write count');status=writes[0]['status'] if writes else None
                if writes:
                    q=writes[0];entries=dict(q['form_entries']);need(q['path']=='/'+created['full_name']+'/settings' and q['method']=='POST' and entries['action']=='update' and entries['description']==spec['edit_value'],'Native edit')
                need([f['label'] for f in o['forms']]==['loaded','before_submit','fresh_final'],'Native snapshots');signal=False
                for form,values in zip(o['forms'],[before,expected,after]):
                    for f in spec['native_fields']:
                        found=[x for x in form['fields'] if x['name']==f['field']];need(len(found)==1 and found[0]['selector']==f['selector'],'Native binding')
                        if form['label']!='before_submit' and found[0]['value']!=values[f['field']]:signal=True
                        if form['label']=='before_submit' and f['field']=='description':need(found[0]['value']==spec['edit_value'],'Requested edit set')
                need(signal==o['native_representation_signal'],'Representation signal');row['native_representation_signal']=signal
            outcome=classify(status,after,before,expected)
            if channel=='ui' and not writes and o['native_submission']['form_valid'] is False and o['native_submission']['attempts']==[] and after==before:
                need(o['native_submission']['observation_window_ms']==1500 and any(not f['attributes']['valid'] for f in o['forms'][1]['fields']),'Native validation evidence');outcome='blocked_native_validation'
            if shared[0]['trust_model']!=shared[1]['trust_model']:outcome='shared_metadata_changed'
            need(outcome==o['continuation'],'Continuation classification');row['channels'][channel]=outcome
        for key in ['initial_business_state','prefix_status','prefix_business']:need(observations[0].get(key)==observations[1].get(key),'Pair comparability')
        values=list(row['channels'].values());row['classification']='producer_rejected' if all(v=='producer_rejected' for v in values) else 'unresolved' if 'execution_unknown' in values else 'both_clean' if all(v=='clean_preserving_continuation' for v in values) else 'channel_difference' if values[0]!=values[1] else 'shared_continuation_discrepancy'
        if row['classification'] not in ['producer_rejected','unresolved']:
            api=row['shared_signal'] or values[0]!='clean_preserving_continuation';native=row['shared_signal'] or values[1]!='clean_preserving_continuation' or row.get('native_representation_signal',False);row['baseline_overlap']='both' if api and native else 'api_only' if api else 'native_only' if native else 'neither'
        row['repeat_required']=row['classification'] not in ['producer_rejected','both_clean'] or row['shared_signal'] or row.get('native_representation_signal',False)
    need(set(records)==set(units) and len(runs)==len(commits)==1,'Complete single-run inventory')
    return dict(kind='independent_gitea_repo_finite_results_v1',run_identity=next(iter(runs)),source_commit=next(iter(commits)),records=records,counts={cohort:dict(Counter(r['classification'] for r in records.values() if r['cohort']==cohort)) for cohort in ['schema_sample','valid_control']},repeat_case_ids=sorted({r['case_id'] for r in records.values() if r['repeat_required']}),natural_defects_confirmed=0)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--registry',default=str(ROOT/'manifests/independent-gitea-repo-execution-v1.json'));p.add_argument('--output');a=p.parse_args();v=check(a.root,a.registry)
    if a.output:
        target=Path(a.output);need(not target.exists(),'Already registered');target.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps(v['counts'],indent=2))
