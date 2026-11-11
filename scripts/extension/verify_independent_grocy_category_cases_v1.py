#!/usr/bin/env python3
"""Reconstruct the complete finite Grocy archive from raw retained observations."""
import argparse,hashlib,json,re
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(v,m):
    if not v:raise ValueError(m)
def classify(status,after,before,expected,metadata):
    if not metadata:return 'immutable_field_change'
    if status is not None and 200<=status<400:return 'clean_preserving_continuation' if after==expected else 'preservation_or_edit_discrepancy'
    if after!=before:return 'failed_write_state_change'
    return 'blocked_save' if status in (400,409,422) else 'execution_unknown'
def violations(values,rules):
    failures=[]
    for key,rule in rules.items():
        v=values[key]
        if v is None and rule.get('nullable'):continue
        correct=type(v)is str if rule['type']=='string' else type(v)is int if rule['type']=='integer' else type(v)in(int,float)
        if not correct or (type(v)is str and len(v)<rule.get('minLength',0)) or ('minimum' in rule and type(v)in(int,float) and v<rule['minimum']):failures.append(key)
    return failures
def check(root,registry):
    reg=read(registry);units={u['id']:u for u in reg['units']};cases={c['id']:c for c in reg['cases']};flows={w['id']:w for w in reg['workflows']};records={};runs=set();commits=set()
    for p,h in {**reg['source_sha256'],**reg['qualification_sha256']}.items():require(sha(ROOT/p)==h,'Frozen source changed: '+p)
    seed=lambda rows:sorted([{k:v for k,v in row.items() if k!='row_created_timestamp'} for row in rows],key=lambda x:x['id'])
    for report in sorted(Path(root).rglob('report.json')):
        pair=report.parent;r=read(report);u=r['unit'];require(u['id'] in units and u==units[u['id']] and u['id'] not in records,'Unit identity differs');require(r['registry_sha256']==sha(registry),'Registry differs');require(r['files_sha256']=={str(p.relative_to(pair)):sha(p) for p in pair.rglob('*') if p.is_file() and p.name!='report.json'},'Raw files differ');runs.add(r['run_identity']);commits.add(r['source_commit']);c=cases[u['case_id']];w=flows[c['workflow']]
        record={'case_id':c['id'],'cohort':u['cohort'],'report_sha256':sha(report),'classification':'unresolved','channels':{},'shared_signal':False,'repeat_required':True}
        records[u['id']]=record
        if r['status']!='pair_observed' or not r['cleanup_confirmed']:record['error']=r.get('error','Incomplete observation');continue
        require(r['image']['id']==reg['image_id'] and r['actor_permissions']==reg['actor_permissions'],'Image/role differs');observations=[]
        def canonical(k,v):return int(v) if k in w['integer_fields'] and type(v)is str and re.fullmatch(r'-?[0-9]+',v) else v
        def business(v):return {k:canonical(k,v[k]) for k in w['fields']}
        for channel in ['api','ui']:
            o=read(pair/channel/'observation.json');observations.append(o);require(o['case_id']==c['id'] and o['workflow']==w['id'] and o['channel']==channel and o['browser_cleanup_confirmed'],'Observation differs');qs=o['requests'];infos=[q for q in qs if q['path']=='/api/system/info'];require(len(infos)==1 and infos[0]['status']==200 and infos[0]['response']['grocy_version']['Version']==reg['version'],'Version differs');initial=next(q for q in qs if q['method']=='GET' and q['path']==w['collection']);require(initial['status']==200 and len(initial['response'])==w['initial_count'],'Initial collection differs');seeds={w['collection']:seed(initial['response'])};fixtures={}
            for f in w['fixtures']:
                existing=next(q for q in qs if q['method']=='GET' and q['path']==f['collection']);made=[q for q in qs if q['method']=='POST' and q['path']==f['collection']];require(existing['status']==200 and len(made)==1 and made[0]['status']==200 and made[0]['body']==f['payload'],'Fixture differs');seeds[f['collection']]=seed(existing['response']);require(not any(x['name']==f['payload']['name'] for x in existing['response']),'Fixture collision');fixtures[f['id']]=int(made[0]['response']['created_object_id'])
            require(seeds==o['initial_business_state']['seed_collections'] and fixtures==o['fixture_ids'],'Seed or fixture identity differs');actor=o['initial_business_state']['actor_id'];payload={k:actor if v=='$actor' else fixtures[v[9:]] if type(v)is str and v.startswith('$fixture:') else v for k,v in c['payload'].items()};made=[q for q in qs if q['method']=='POST' and q['path']==w['collection']];require(len(made)==1 and made[0]['body']==payload==o['resolved_payload'],'Producer differs');made=made[0]
            if made['status']!=200:
                lists=[q for q in qs if q['method']=='GET' and q['path']==w['collection']];require(len(lists)==2 and lists[1]['status']==200,'Failed-write collection check missing');same=seed(lists[1]['response'])==seeds[w['collection']];status='rejected_without_visible_write' if same and made['status'] in (400,409,422) else 'server_error_or_unexpected_status_without_visible_write' if same else 'failed_producer_visible_state_change';require(status==o['prefix_status'] and same==o['failed_producer_collection_unchanged'],'Failed producer classification differs');record['channels'][channel]='producer_rejected' if status=='rejected_without_visible_write' else 'execution_unknown';continue
            require(o['prefix_status']=='accepted_persisted','Prefix status differs');resource=int(made['response']['created_object_id']);require(resource==o['resource_id'],'Resource differs');path=w['collection']+'/'+str(resource);reads=[q for q in qs if q['method']=='GET' and q['path']==path];require(len(reads)==2 and all(q['status']==200 for q in reads),'State reads missing');before,after=[business(q['response']) for q in reads];require(before==o['prefix'] and after==o['final'],'State reconstruction differs');require(all(set(q['response'])==set(w['fields']+w['immutable_fields']) for q in reads),'Schema inventory differs');require(reads[0]['response']['id']==resource,'Persisted identity differs');expected={**before,w['edit_field']:w['edit_value']};metadata=all(reads[0]['response'][k]==reads[1]['response'][k] for k in w['immutable_fields']);failures=violations(before,reg['persisted_contracts'][w['id']]);require(failures==o['persisted_contract_violations'],'Contract signal differs');record['shared_signal']|=bool(failures)
            refs=[]
            for ref in w['references']:
                v=before[ref['field']]
                if v is None:check={'field':ref['field'],'value':v,'valid':ref['nullable'],'reason':'nullable_absent' if ref['nullable'] else 'required_reference_absent'}
                elif type(v)is not int:check={'field':ref['field'],'value':v,'valid':False,'reason':'non_integer_reference'}
                else:
                    refpath=ref['collection'] if ref['mode']=='list' else ref['collection']+'/'+str(v);found=[q for q in qs if q['method']=='GET' and q['path']==refpath];require(found,'Reference lookup missing');q=found[0];valid=(any(int(x['id'])==v for x in q['response']) if ref['mode']=='list' else int(q['response']['id'])==v) if q['status']==200 else False if q['status']==404 else None;check={'field':ref['field'],'value':v,'status':q['status'],'valid':valid,'reason':'lookup_unresolved' if valid is None else 'exists' if valid else 'missing_reference'}
                refs.append(check)
            require(refs==o['reference_checks'],'Reference signal reconstruction differs');record['shared_signal']|=any(x['valid'] is not True for x in refs)
            edits=[q for q in qs if q['method']=='PUT' and q['path']==path];require(len(edits)<=1,'Multiple continuations');status=edits[0]['status'] if edits else None
            if channel=='api':require(len(edits)==1 and edits[0]['channel']=='api' and edits[0]['body']==expected,'API full-record edit differs')
            else:
                require([f['label'] for f in o['forms']]==['loaded','before_submit','fresh_final'],'Native snapshots missing');discrepancies=[]
                for form,values in zip(o['forms'],[before,expected,after]):
                    for binding in w['native_fields']:
                        key=binding['field'];found=[x for x in form['fields'] if x['name']==key];require(len(found)==1 and found[0]['count']==1 and found[0]['selector']==binding['selector'],'Native binding differs');f=found[0];expected_value=values[key]==1 if binding['kind']=='checkbox' else '' if values[key] is None else str(values[key]);agree=f['value']==expected_value;require(f['expected']==expected_value and f['agrees']==agree,'Native interpretation differs')
                        if form['label']!='before_submit' and not agree:discrepancies.append({'stage':form['label'],'field':key,'value':f['value'],'expected':expected_value})
                require(discrepancies==o['native_representation_discrepancies'],'Representation differences missing');record['native_representation_signal']=bool(discrepancies)
                if edits:require(edits[0]['channel']=='ui' and edits[0]['body'][w['edit_field']]==w['edit_value'],'Native edit differs')
            outcome=classify(status,after,before,expected,metadata)
            if channel=='ui' and not edits and o['native_submission']['form_valid'] is False and o['native_submission']['attempts']==[] and after==before and metadata:
                require(o['native_submission']['observation_window_ms']==1500 and o['forms'][1]['form_valid'] is False and any(f['details']['valid'] is False for f in o['forms'][1]['fields']),'Blocking validity evidence missing');outcome='blocked_native_validation'
            require(outcome==o['continuation'],'Continuation classification differs');record['channels'][channel]=outcome
        for key in ['initial_business_state','fixture_ids','prefix_status','prefix']:require(observations[0].get(key)==observations[1].get(key),'Pair differs: '+key)
        values=list(record['channels'].values())
        record['classification']='producer_rejected' if all(v=='producer_rejected' for v in values) else 'unresolved' if 'execution_unknown' in values else 'both_clean' if all(v=='clean_preserving_continuation' for v in values) else 'channel_difference' if values[0]!=values[1] else 'shared_continuation_discrepancy'
        record['repeat_required']=record['classification'] not in ['producer_rejected','both_clean'] or record['shared_signal'] or record.get('native_representation_signal',False)
        if record['classification'] not in ['producer_rejected','unresolved']:
            api=record['shared_signal'] or values[0]!='clean_preserving_continuation';native=record['shared_signal'] or values[1]!='clean_preserving_continuation' or record.get('native_representation_signal',False);record['baseline_overlap']='both' if api and native else 'api_only' if api else 'native_only' if native else 'neither'
    require(set(records)==set(units) and len(runs)==len(commits)==1,'Incomplete or mixed collection')
    return {'kind':'grocy_finite_results_v1','run_identity':next(iter(runs)),'source_commit':next(iter(commits)),'records':records,'counts':{c:dict(Counter(r['classification'] for r in records.values() if r['cohort']==c)) for c in ['schema_sample','valid_control']},'repeat_case_ids':sorted({r['case_id'] for r in records.values() if r['repeat_required']}),'natural_defects_confirmed':0}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--registry',default=str(ROOT/'manifests/independent-grocy-category-execution-v1.json'));p.add_argument('--output');a=p.parse_args();result=check(a.root,Path(a.registry))
    if a.output:
        target=Path(a.output);require(not target.exists(),'Output exists');target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['counts'],indent=2))
