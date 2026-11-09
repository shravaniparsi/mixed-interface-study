"""Independent trace reconstruction for the identity adapter; no dispatch authority."""
import hashlib
from copy import deepcopy
from pathlib import Path
from urllib.parse import quote
from summarize_realworld_oracle_components import capture_integrity_issues, strict_json_equal

ROOT=Path(__file__).resolve().parents[1]
BIO='Bio after meaningful continuation.'
FIELDS=('username','email','bio','image')
jskey=lambda s:s.encode('utf-16-be','surrogatepass')
encode=lambda s:quote(s,safe="~()*!.'-")


def require(ok,message):
    if not ok:raise ValueError(message)


def user(value):
    require(type(value) is dict and all(k in value for k in FIELDS),'Incomplete current user')
    require(all(type(value[k]) is str and value[k] for k in ('username','email')),'Invalid principal')
    require(all(value[k] is None or type(value[k]) is str for k in ('bio','image')),'Invalid optional field')
    return {k:value[k] for k in FIELDS}


def expected_user(before,patch):
    result=user(before)
    require(type(patch) is dict and not set(patch)-set(FIELDS),'Unsupported patch')
    for key,value in patch.items():
        if key=='email':require(value==before['email'],'Email change outside contract')
        elif key=='username':
            require(type(value) is str and bool(value),'Unsupported accepted username')
            result[key]=value
        else:
            require(value is None or type(value) is str,'Invalid optional field')
            result[key]=None if value is None or value=='' else value
    return result


def project(reads,principal,slugs):
    require(type(slugs) is list and slugs and all(type(s) is str and s for s in slugs) and len(slugs)==len(set(slugs)),'Invalid fixture references')
    def at(path):
        matches=[r for r in reads if r['path']==path]
        require(len(matches)==1 and type(matches[0]['status']) is int and matches[0]['status']==200,'Unreadable or duplicate snapshot probe')
        return matches[0]['data']
    current=user(at('/api/user')['user'])
    require(all(current[k]==principal[k] for k in ('username','email')),'Principal differs')
    collection=at('/api/articles?author='+encode(principal['username']))
    articles=collection['articles']
    require(type(articles) is list and type(collection['articlesCount']) is int and collection['articlesCount']==len(articles),'Partial article list')
    require(sorted(a['slug'] for a in articles)==sorted(slugs),'Fixture articles differ')
    tags=at('/api/tags')['tags']
    require(type(tags) is list and all(type(t) is str for t in tags),'Invalid tags')
    output=[]
    for article in articles:
        require(article['author']['username']==principal['username'],'Wrong article author')
        require(all(type(article[k]) is str for k in ('title','description','body')) and type(article['tagList']) is list and all(type(t) is str for t in article['tagList']),'Invalid article fields')
        comments=at('/api/articles/'+encode(article['slug'])+'/comments')['comments']
        require(type(comments) is list and all(type(c['id']) is int and 0<c['id']<=9007199254740991 and type(c['body']) is str and type(c['author']['username']) is str for c in comments),'Invalid comments')
        require(len(comments)==len({c['id'] for c in comments}),'Duplicate comment ids')
        output.append({'article':{**article,'tagList':sorted(set(article['tagList']),key=jskey)},'comments':sorted(comments,key=lambda c:c['id'])})
    require(len(reads)==3+len(slugs),'Extra snapshot probes')
    return {'user':current,'articles':sorted(output,key=lambda a:jskey(a['article']['slug'])),'tags':sorted(set(tags),key=jskey)}


def reconstruct(raw,spec,fixture):
    """Source/fixture/reset qualification and process cleanup remain loader duties."""
    require(raw['candidate_id']==spec['candidate_id'] and raw['expectation']==spec['expectation'],'Changed registration')
    require(raw['workflow']==spec['workflow']=='profile-update-edit' and raw['prefix_interface']==spec['prefix_interface']=='api','Wrong workflow or producer')
    branch=raw['continuation_interface'];require(branch in ('api','ui') and branch in spec['continuations'],'Wrong consumer')
    require(raw['execution_status']=='completed' and not raw.get('error'),'Incomplete adapter')
    require(not capture_integrity_issues(raw,required=True),'Incomplete response capture')
    require(raw['normalization_policy']=='realworld-identity-preparation-v1','Wrong identity contract')
    identity=raw['identity'];require(identity['version']==1 and identity['helper_sha256']==hashlib.sha256((ROOT/'scripts/realworld_identity_v1.mjs').read_bytes()).hexdigest(),'Identity helper differs')
    trace=raw['trace'];require([e['sequence'] for e in trace]==list(range(1,len(trace)+1)),'Noncontiguous trace')
    require(not any(e['type'] in ('capture_error','page_error') for e in trace),'Trace error')
    # Direct API calls are sequential. UI pairs are separately bound by capture ids.
    pending=None
    for event in trace:
        if event.get('source') not in ('api','state_probe') or event['type'] not in ('request','response'):continue
        key=tuple(event[k] for k in ('source','phase','method','path'))
        if event['type']=='request':require(pending is None,'Overlapping direct requests');pending=key
        else:require(pending==key,'Unmatched direct response');pending=None
    require(pending is None,'Unfinished direct request')
    def events(kind,source,phase,method,path):
        return [e for e in trace if e['type']==kind and e.get('source')==source and (e.get('request_phase',e['phase']) if source=='ui' else e['phase'])==phase and e.get('method')==method and e.get('path')==path]
    def one(kind,source,phase,method,path):
        matches=events(kind,source,phase,method,path);require(len(matches)==1,'Missing or duplicate '+phase+' '+method+' '+path);return matches[0]
    def exchange(source,phase,method,path,payload):
        request=one('request',source,phase,method,path);response=one('response',source,phase,method,path)
        require(strict_json_equal(request.get('payload'),payload),'Submitted command differs')
        require(request['sequence']<response['sequence'],'Response precedes request')
        require(type(response['status']) is int,'Invalid response status')
        return {**response,'_request_sequence':request['sequence']}
    login=exchange('api','setup','POST','/api/users/login',{'user':{'email':'pilot@example.com','password':'[REDACTED]'}})
    require(login['status']==200 and user(login['data']['user'])['username']=='pilotresearch' and login['data']['user']['email']=='pilot@example.com','Initial principal differs')
    baseline_response=one('response','api','setup','GET','/api/user')
    require(baseline_response['status']==200,'Baseline unreadable');baseline=user(baseline_response['data']['user'])
    require(baseline['username']=='pilotresearch' and baseline['email']=='pilot@example.com','Baseline principal differs')
    require(raw['actor']=={'email':'pilot@example.com','stable_fixture_username':'pilotresearch'},'Actor differs')
    refs=[fixture[k]['slug'] for k in ('base','duplicate_first','duplicate')]
    def snapshot(name,phase,principal):
        value=identity[name];require(value['readable'] is True,'Unreadable '+name+' snapshot')
        seen=[]
        for read in value['reads']:
            event=trace[read['response_sequence']-1]
            require(event['type']=='response' and event['source']=='state_probe' and event['phase']==phase and event['method']=='GET','Snapshot phase/source differs')
            require(all(strict_json_equal(read[k],event[k]) for k in ('path','status','data')),'Snapshot lacks trace binding')
            seen.append(event['sequence'])
        require(seen==[e['sequence'] for e in trace if e.get('source')=='state_probe' and e['type']=='response' and e['phase']==phase],'Snapshot probe inventory differs')
        derived=project(value['reads'],principal,refs)
        require(strict_json_equal(derived,value['data']),'Snapshot projection differs')
        return derived
    before=snapshot('before','setup',baseline)
    require(strict_json_equal(before['user'],baseline),'Baseline projection differs')
    require(strict_json_equal([x['article'] for x in before['articles']],sorted(fixture.values(),key=lambda a:jskey(a['slug']))),'Restored fixture articles differ')
    prefix=exchange('api','prefix','PUT','/api/user',{'user':spec['prefix_payload']})
    require(raw['observations']['prefix_status']==prefix['status'] and strict_json_equal(raw['observations']['prefix_response'],prefix['data']),'Prefix summary differs')
    require(login['sequence']<baseline_response['sequence']<identity['before']['reads'][0]['response_sequence'] and identity['before']['reads'][-1]['response_sequence']<prefix['_request_sequence'],'Setup/prefix order differs')
    accepted=prefix['status']==200
    allowed_writes={('api','setup','POST','/api/users/login'),('api','prefix','PUT','/api/user')}
    if accepted:
        allowed_writes.add((branch,'continuation','PUT','/api/user'))
        if branch=='ui':allowed_writes.add(('ui','continuation_auth','POST','/api/users/login'))
    for e in trace:
        if e['type']=='request' and e.get('method') in ('POST','PUT','DELETE','PATCH'):
            require((e.get('source'),e.get('request_phase',e['phase']),e['method'],e['path']) in allowed_writes,'Unregistered write')
    require(all(g['passed'] is True and strict_json_equal(g['expected'],g['observed']) for g in raw['integrity']['guards']),'Failed operation guard')
    def guard(name,stage,source,expected):
        records=[g for g in raw['integrity']['guards'] if (g['name'],g['stage'],g['source'])==(name,stage,source)]
        require(len(records)==1 and strict_json_equal(records[0]['expected'],expected),'Missing or altered bound guard')
    guard('pre_state_readable','setup','shared_api',True)
    guard('submitted_command','prefix','api',{'method':'PUT','path':'/api/user','payload':{'user':spec['prefix_payload']}})
    unknown=spec['expectation']['outcome']=='unknown' or spec['expectation']['category']=='unresolved'
    if not accepted:
        require(not any(e['phase'] in ('continuation','continuation_auth','prefix_readback','shared_readback') for e in trace),'Continuation after rejected prefix')
        require(not raw['observations']['api_continuation_started'] and not raw['observations']['ui_continuation_started'] and raw['observations']['continuation_outcome']=='not_executed_prefix_unsuccessful','Rejection stop differs')
        after=snapshot('after','failed_prefix_followup',baseline)
        require(prefix['sequence']<identity['after']['reads'][0]['response_sequence'],'Rejection readback precedes prefix')
        checks={'rejection_state_unchanged':strict_json_equal(before,after)}
        kind='application_response_failure' if prefix['status'] not in (400,422) else 'unresolved_policy' if unknown else 'matched_rejection' if spec['expectation']['outcome']=='reject' and all(checks.values()) else 'completed_mismatch'
        return {'kind':kind,'accepted':False,'checks':checks,'prefix_status':prefix['status'],'policy_unresolved':unknown}
    expected=expected_user(baseline,spec['prefix_payload'])
    current=snapshot('prefix','prefix_readback',expected)
    require(strict_json_equal(current['user'],expected) and strict_json_equal(raw['prefix_state'],expected),'Prefix user differs')
    guard('expected_prefix_user','prefix_readback','shared_api',expected)
    payload={k:expected[k] for k in ('username','email')};payload['bio']=BIO
    if expected['image'] is not None:payload['image']=expected['image']
    if branch=='ui':
        fresh=exchange('ui','continuation_auth','POST','/api/users/login',{'user':{'email':'pilot@example.com','password':'[REDACTED]'}})
        require(fresh['status']==200 and strict_json_equal(user(fresh['data']['user']),expected),'Fresh principal differs')
        guard('fresh_identity_bound','continuation_auth','ui',expected)
        guard('settings_form_bound','continuation','ui',{'username':expected['username'],'email':expected['email'],'bio':expected['bio'] or '', 'image':expected['image'] or '', 'new_credential_blank':True})
    continuation=exchange(branch,'continuation','PUT','/api/user',{'user':payload})
    require(prefix['sequence']<identity['prefix']['reads'][0]['response_sequence'] and identity['prefix']['reads'][-1]['response_sequence']<continuation['_request_sequence'],'Prefix/continuation order differs')
    if branch=='ui':require(identity['prefix']['reads'][-1]['response_sequence']<fresh['_request_sequence'] and fresh['sequence']<continuation['_request_sequence'],'Fresh login order differs')
    guard('submitted_command','continuation',branch,{'method':'PUT','path':'/api/user','payload':{'user':payload}})
    require(raw['observations'][branch+'_continuation_started'] is True and raw['observations'][('ui' if branch=='api' else 'api')+'_continuation_started'] is False,'Wrong assigned continuation')
    require(raw['observations']['continuation_write_status']==continuation['status'],'Write status differs')
    after=snapshot('after','shared_readback',expected)
    profile=one('response','api','shared_readback','GET','/api/profiles/'+encode(expected['username']))
    require(continuation['sequence']<identity['after']['reads'][0]['response_sequence'] and identity['after']['reads'][-1]['response_sequence']<profile['sequence'],'Final readback order differs')
    related=deepcopy(current['articles'])
    for row in related:
        for entity in [row['article']]+row['comments']:
            if entity['author']['username']==expected['username'] and 'bio' in entity['author']:entity['author']['bio']=BIO
    prefix_related=deepcopy(before['articles'])
    for row in prefix_related:
        for entity in [row['article']]+row['comments']:
            if entity['author']['username']==baseline['username']:
                for key in ('username','bio','image'):
                    if key in entity['author']:entity['author'][key]=expected[key]
    checks={'prefix_profile_matches_input':True,'prefix_related_state_preserved':strict_json_equal(prefix_related,current['articles']) and strict_json_equal(before['tags'],current['tags']),'profile_reference_resolvable':profile['status']==200 and profile['data'].get('profile',{}).get('username')==expected['username'] and profile['data'].get('profile',{}).get('bio')==BIO,
            'profile_edit_persisted':continuation['status']==200 and strict_json_equal(after['user'],{**expected,'bio':BIO}),
            'related_state_preserved':strict_json_equal(related,after['articles']) and strict_json_equal(current['tags'],after['tags'])}
    require(len(raw['checks'])==len(checks) and strict_json_equal({c['name']:c['passed'] for c in raw['checks']},checks),'Claimed checks differ from trace')
    require(strict_json_equal(raw['final_state'],after['user']),'Final state differs')
    require(raw['observations']['continuation_outcome']==('passed' if all(checks.values()) else 'state_mismatch'),'Continuation summary differs')
    kind='application_response_failure' if continuation['status']!=200 else 'unresolved_policy' if unknown else 'clean_observation' if all(checks.values()) and spec['expectation']['outcome']=='accept' else 'completed_mismatch'
    return {'kind':kind,'accepted':True,'checks':checks,'prefix_status':200,'policy_unresolved':unknown}


def extract(raw,spec,fixture):
    try:return reconstruct(raw,spec,fixture)
    except (ValueError,KeyError,TypeError,AttributeError,IndexError) as error:
        return {'kind':'missing_evidence','issues':[str(error)],'accepted':None}
