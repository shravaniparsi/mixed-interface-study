#!/usr/bin/env python3
"""Apply new source-qualified expectations to existing controls, without relabelling them."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.normalization import exact,article_create,article_body_update,profile_update,tag_comparison

def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def one(items,label):
    if len(items)!=1:raise ValueError('Missing or ambiguous '+label)
    return items[0]

def build():
    inputs=load(ROOT/'manifests/unified-control-inputs-v1.json')
    policy=load(ROOT/'manifests/normalization-policy-v1.json')
    for path,h in policy['source_sha256'].items():
        if sha(ROOT/path)!=h:raise ValueError('Changed normalization source '+path)
    rows=[]
    for key,ref in inputs['realworld_raw'].items():
        path=ref['observation']
        if sha(ROOT/path)!=inputs['input_sha256'][path]:raise ValueError('Changed raw control '+path)
        raw=load(ROOT/path);trace=raw['trace']
        responses=[t for t in trace if t['type'] in ('response','ui_response') and t.get('phase') in ('prefix','producer')
                   and t.get('method') in ('POST','PUT') and t.get('path')!='/api/users/login']
        response=one(responses,'prefix response');status=response['status']
        row={'record_id':key,'input_sha256':sha(ROOT/path),'prefix_status':status}
        if status>=400:
            row['status']='rejected_no_accepted_state_expectation';rows.append(row);continue
        endpoint=response['path']
        requests=[t for t in trace if t['type'] in ('request','ui_request') and t.get('phase') in ('prefix','producer')
                  and t.get('method')==response['method'] and t.get('path')==endpoint and t['sequence']<response['sequence']]
        request=one(requests,'prefix request');payload=request['payload']
        if '/comments' in endpoint:
            row['status']='outside_normalization_scope';rows.append(row);continue
        if endpoint=='/api/user':
            baseline=[t['data']['user'] for t in trace if t['type']=='response' and t.get('phase')=='setup' and t.get('path')=='/api/user' and t.get('status')==200]
            if not baseline or any(not exact(baseline[0],x) for x in baseline):raise ValueError('Missing or inconsistent profile baseline')
            before=baseline[0];fields=('username','email','bio','image')
            wanted=profile_update({k:before[k] for k in fields},payload['user'])
            actual={k:response['data']['user'][k] for k in fields}
        else:
            fields=('title','description','body','tagList')
            if endpoint=='/api/articles' and response['method']=='POST':wanted=article_create(payload['article'])
            elif response['method']=='PUT' and endpoint.startswith('/api/articles/'):
                if set(payload['article'])!={'body'}:raise ValueError('Audit supports only the registered body-only partial update')
                baselines=[a for t in trace if t['type']=='response' and t.get('phase')=='setup' and t.get('path')=='/api/articles?author=pilotresearch' and t.get('status')==200 for a in t['data']['articles'] if '/api/articles/'+a['slug']==endpoint]
                before=one(baselines,'listed article baseline')
                wanted=article_create({**{k:before[k] for k in ('title','description','tagList')},'body':payload['article']['body']})
                row['baseline_scope']='Listed preserved fields; old body unobserved and explicitly replaced by the declared body.'
            else:raise ValueError('Unsupported accepted prefix '+endpoint)
            actual={k:response['data']['article'][k] for k in fields}
            row['tags']=tag_comparison(wanted['tagList'],actual['tagList'])
        row.update(status='source_expectation_matches' if exact(wanted,actual) else 'source_expectation_differs',expected=wanted,observed=actual,
                   request_sequence=request['sequence'],response_sequence=response['sequence'])
        rows.append(row)
    return {'scope':'retrospective control expectations; no runner replacement or defect adjudication',
            'primary_freeze_complete':False,'records':rows,'counts':{s:sum(r['status']==s for r in rows) for s in
             ('source_expectation_matches','source_expectation_differs','rejected_no_accepted_state_expectation','outside_normalization_scope')},
            'source_sha256':{p:sha(ROOT/p) for p in ('scripts/audit_normalization_controls.py','src/mixed_interface/normalization.py','manifests/normalization-policy-v1.json','manifests/unified-control-inputs-v1.json')}}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    result=build();path=ROOT/'results/normalization-controls-20261107/analysis.json'
    if args.verify:
        if load(path)!=result:raise ValueError('Normalization audit differs from archived report')
    else:
        path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['counts'],indent=2))
if __name__=='__main__':main()
