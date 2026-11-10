#!/usr/bin/env python3
"""Independently reconstruct all registered finite cases; retain unresolved attempts."""
import argparse,hashlib,json,re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(value,message):
    if not value:raise ValueError(message)
def classify(status,after,before,expected):
    successful=200<=status<400
    if successful and after==expected:return 'clean_preserving_continuation'
    if not successful and after!=before:return 'failed_write_state_change'
    if successful:return 'preservation_or_edit_discrepancy'
    if status in (400,409,422) and after==before:return 'blocked_save'
    return 'execution_unknown'
def contract_violations(value,rules):
    failures=[]
    for key,rule in rules.items():
        v=value.get(key)
        if v is None and rule.get('nullable') and key in value:continue
        correct={'string':type(v)is str,'boolean':type(v)is bool,'number':type(v)in(int,float),'array':type(v)is list}.get(rule['type'],False)
        if not correct or (rule.get('integer') and type(v)is not int) or ('max_length' in rule and type(v)is str and len(v)>rule['max_length']) or ('options' in rule and v not in rule['options']) or ('pattern' in rule and type(v)is str and re.search(rule['pattern'],v)is None):failures.append(key)
    return failures
def check(root,registry):
    reg=read(registry);cases={c['id']:c for c in reg['cases']};units={u['id']:u for u in reg['units']};flows={w['id']:w for w in reg['workflows']}
    for p,h in {**reg['source_sha256'],**reg['qualification_sha256']}.items():require(sha(ROOT/p)==h,'Frozen dependency changed: '+p)
    records={};runs=set();commits=set()
    for report in sorted(Path(root).rglob('report.json')):
        pair=report.parent;r=read(report);u=r['unit'];require(u['id'] in units and u==units[u['id']] and u['id'] not in records,'Foreign or duplicate unit');require(r['registry_sha256']==sha(registry),'Registry hash mismatch');runs.add(r['run_identity']);commits.add(r['source_commit'])
        actual={str(p.relative_to(pair)):sha(p) for p in sorted(pair.rglob('*')) if p.is_file() and p.name!='report.json'};require(actual==r['files_sha256'],'Raw inventory differs')
        c=cases[u['case_id']];w=flows[c['workflow']];record={'case_id':c['id'],'cohort':u['cohort'],'report_sha256':sha(report),'eligible':False,'classification':'unresolved','channels':{},'shared_signal':False}
        if r['status']!='pair_observed' or not r['cleanup_confirmed']:
            record['error']=r.get('error','Incomplete branch or comparability');records[u['id']]=record;continue
        require(r['image']['id']==reg['image_id'] and r['application_version']==reg['version'] and r['actor_role']['is_staff'] is False and r['actor_role']['is_superuser'] is False,'Image/version/role differs')
        states=[]
        for channel in ('api','ui'):
            o=read(pair/channel/'observation.json');require(o['case_id']==c['id'] and o['workflow']==w['id'] and o['channel']==channel and o['browser_cleanup_confirmed'],'Observation identity/cleanup differs')
            actor=o['initial_business_state']['actor_id'];require(type(actor)is int,'Actor identity missing');payload={**c['payload'],'owner':actor};requests=o['requests'];producers=[q for q in requests if q['channel']=='api' and q['method']=='POST'];require(len(producers)==1 and producers[0]['body']==payload and producers[0]['path']==w['collection'],'Producer differs');producer=producers[0];require(all(q.get('api_version')==10 for q in requests if q['channel']=='api'),'API version differs');initial=[q for q in requests if q['method']=='GET' and q['path']==w['collection']][0];require(initial['status']==200 and initial['response']['count']==0,'Initial collection not empty')
            if o['prefix_status']=='rejected_without_visible_write':
                require(producer['status'] in (400,409,422),'Incorrect rejection label');lists=[q for q in requests if q['method']=='GET' and q['path']==w['collection']];require(len(lists)==2 and all(q['status']==200 and q['response']['count']==0 for q in lists),'Rejected-write visible-state check missing');record['channels'][channel]='producer_rejected';states.append(None);continue
            if o['prefix_status']=='unresolved':
                record['channels'][channel]='execution_unknown';states.append(None);continue
            require(o['prefix_status']=='accepted_persisted' and producer['status']==201,'Unresolved producer cannot be promoted');resource=producer['response']['id'];require(type(resource)is int and resource==o['resource_id'],'Resource identity differs');path=w['collection']+str(resource)+'/'
            reads=[q for q in requests if q['method']=='GET' and q['path']==path];require(reads and all(q['status']==200 for q in reads),'Persisted reads missing');business=lambda d:{k:d[k] for k in w['fields']};before=business(reads[0]['response']);require(before==o['prefix'],'Prefix differs');states.append(before);expected={**before,w['edit_field']:w['edit_value']}
            failures=contract_violations(producer['response'],reg['response_contracts'][w['id']]);require(sorted(failures)==sorted(o['response_contract_violations']),'Response contract reconstruction differs');response_agrees=business(producer['response'])==before;require(response_agrees==o['immediate_schema']['response_matches_readback'],'Response/readback reconstruction differs');record['shared_signal']=record['shared_signal'] or bool(failures) or not response_agrees
            if o['continuation'] in ('loaded_value_discrepancy','fresh_editor_value_discrepancy'):
                # These are observable discrepancies, not requirement-backed defect labels.
                require(channel=='ui','Native-only label in API branch');label='loaded' if o['continuation']=='loaded_value_discrepancy' else 'fresh_final';form=next(f for f in o['forms'] if f['label']==label);require(any(not f['agrees'] for f in form['fields']),'No measured discrepancy');record['channels'][channel]=o['continuation'];continue
            require(len(reads)==2 and o['final']==business(reads[1]['response']),'Final state missing');edits=[q for q in requests if q['method'] in ('PUT','POST') and q is not producer];require(len(edits)==1 and edits[0]['channel']==channel,'Continuation count/channel differs');edit=edits[0]
            if channel=='api':require(edit['path']==path and edit['method']=='PUT' and edit['body']==expected,'API edit differs')
            else:
                require(edit['path']==path and edit['method']=='PUT' and edit['body'][w['edit_field']]==w['edit_value'] and 'version=10' in edit['accept'],'Native edit/version differs');require([f['label'] for f in o['forms']]==['loaded','before_submit','fresh_final'],'Native views missing')
                for form,values in zip(o['forms'],[before,expected,o['final']]):
                    for binding in w['native_fields']:
                        key=binding['field'];displayed=values['matching_algorithm'] not in binding.get('hidden_for_algorithms',[]);expected_value=reg['algorithm_labels'].get(str(values[key])) if binding['kind']=='label' else values[key]
                        found=[x for x in form['fields'] if x['name']==key];require(len(found)==1 and found[0]['selector']==binding['selector'] and found[0]['displayed']==displayed,'Native binding differs');field=found[0]
                        require((field['count']==1 and field['value']==expected_value) if displayed else (field['count']==0 and field['value'] is None),'Native value/conditional visibility differs')
            observed=classify(edit['status'],o['final'],before,expected);require(observed==o['continuation'],'Outcome reconstruction differs');record['channels'][channel]=observed
        require(states[0]==states[1],'Paired producer states differ')
        values=list(record['channels'].values())
        if all(v=='producer_rejected' for v in values):record['classification']='producer_rejected'
        elif 'execution_unknown' in values:record['classification']='unresolved'
        elif all(v=='clean_preserving_continuation' for v in values):record.update(classification='both_clean',eligible=True)
        elif values[0]!=values[1]:record.update(classification='channel_difference',eligible=True)
        else:record.update(classification='shared_continuation_discrepancy',eligible=True)
        if record['eligible']:
            api_detected=record['shared_signal'] or record['channels']['api']!='clean_preserving_continuation';native_detected=record['shared_signal'] or record['channels']['ui']!='clean_preserving_continuation';record['baseline_overlap']='both' if api_detected and native_detected else 'api_only' if api_detected else 'native_only' if native_detected else 'neither'
        record['repeat_required']=record['classification'] not in ('producer_rejected','both_clean') or record['shared_signal'];records[u['id']]=record
    require(set(records)==set(units),'Missing registered cases');require(len(runs)==len(commits)==1,'Mixed source/run collection')
    return {'kind':'paperless_finite_results_v1','run_identity':next(iter(runs)),'source_commit':next(iter(commits)),'records':records,'counts':{cohort:dict(Counter(r['classification'] for r in records.values() if r['cohort']==cohort)) for cohort in ('boundary','valid_control')},'repeat_case_ids':sorted({r['case_id'] for r in records.values() if r.get('repeat_required',True)}),'baseline_overlap':{cohort:dict(Counter(r.get('baseline_overlap','not_eligible') for r in records.values() if r['cohort']==cohort)) for cohort in ('boundary','valid_control')},'natural_defects_confirmed':0,'interpretation':'Observational outcomes only; mechanism and requirement adjudication remain separate.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--registry',default=str(ROOT/'manifests/paperless-execution-v1.json'));p.add_argument('--output');a=p.parse_args();result=check(a.root,Path(a.registry))
    if a.output:
        target=Path(a.output);require(not target.exists(),'Output exists');target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['counts'],indent=2))
