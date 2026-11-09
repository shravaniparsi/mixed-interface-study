import sys,json,hashlib,unittest,subprocess
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from realworld_identity_extract_v1 import extract,project,expected_user,BIO
from summarize_realworld_oracle_components import CAPTURE_HELPER


def synthetic(branch='api',username='u'*61,status=200,unknown=True):
    baseline={'username':'pilotresearch','email':'pilot@example.com','bio':'old','image':None}
    fixture={k:{'slug':k,'title':k,'description':'d','body':'b','tagList':[], 'author':{'username':'pilotresearch','bio':'old','image':None,'following':False}} for k in ('base','duplicate_first','duplicate')}
    spec={'candidate_id':'profile-username-length61','workflow':'profile-update-edit','prefix_interface':'api','prefix_payload':{'username':username},'continuations':['api','ui'],'expectation':{'outcome':'unknown' if unknown else 'reject' if status!=200 else 'accept','category':'unresolved' if unknown else 'implementation_control'}}
    raw={'candidate_id':spec['candidate_id'],'workflow':spec['workflow'],'prefix_interface':'api','continuation_interface':branch,'expectation':spec['expectation'],'actor':{'email':baseline['email'],'stable_fixture_username':'pilotresearch'},'execution_status':'completed','normalization_policy':'realworld-identity-preparation-v1', 'capture_integrity':{'version':1,'helper_sha256':CAPTURE_HELPER,'complete':True,'contexts':[]},'identity':{'version':1,'helper_sha256':hashlib.sha256((ROOT/'scripts/realworld_identity_v1.mjs').read_bytes()).hexdigest()},'integrity':{'guards':[]},'observations':{'api_continuation_started':False,'ui_continuation_started':False},'checks':[],'trace':[]}
    trace=raw['trace'];uid=0
    def emit(event):event['sequence']=len(trace)+1;trace.append(event);return event
    def exchange(source,phase,method,path,payload,data,status=200):
        nonlocal uid
        extra={}
        if source=='ui':
            uid+=1;extra={'capture_request_id':str(uid),'context_id':'page-1','request_phase':phase}
        emit({'type':'request','source':source,'phase':phase,'method':method,'path':path,'payload':deepcopy(payload),**extra})
        return emit({'type':'response','source':source,'phase':phase,'method':method,'path':path,'status':status,'data':deepcopy(data),**extra})
    def guard(name,stage,source,value):raw['integrity']['guards'].append({'name':name,'stage':stage,'source':source,'expected':deepcopy(value),'observed':deepcopy(value),'passed':True})
    def snap(name,phase,principal):
        articles=deepcopy(list(fixture.values()))
        for a in articles:a['author']['username']=principal['username'];a['author']['bio']=principal['bio']
        from urllib.parse import quote
        probes=[('/api/user',{'user':principal}),('/api/articles?author='+quote(principal['username'],safe="~()*!.'-"),{'articlesCount':3,'articles':articles}),('/api/tags',{'tags':[]})]+[('/api/articles/'+a['slug']+'/comments',{'comments':[]}) for a in sorted(articles,key=lambda x:x['slug'])]
        reads=[]
        for path,data in probes:
            event=exchange('state_probe',phase,'GET',path,None,data)
            reads.append({'path':path,'status':200,'data':deepcopy(data),'response_sequence':event['sequence']})
        raw['identity'][name]={'readable':True,'reads':reads,'data':project(reads,principal,[a['slug'] for a in articles])}
    exchange('api','setup','POST','/api/users/login',{'user':{'email':baseline['email'],'password':'[REDACTED]'}},{'user':baseline})
    exchange('api','setup','GET','/api/user',None,{'user':baseline});snap('before','setup',baseline)
    guard('pre_state_readable','setup','shared_api',True)
    current=expected_user(baseline,spec['prefix_payload']) if status==200 else baseline
    prefix=exchange('api','prefix','PUT','/api/user',{'user':spec['prefix_payload']},{'user':current} if status==200 else {'errors':{}},status)
    guard('submitted_command','prefix','api',{'method':'PUT','path':'/api/user','payload':{'user':spec['prefix_payload']}})
    raw['observations'].update(prefix_status=status,prefix_response=prefix['data'])
    if status!=200:
        snap('after','failed_prefix_followup',baseline);raw['observations']['continuation_outcome']='not_executed_prefix_unsuccessful'
        return raw,spec,fixture
    snap('prefix','prefix_readback',current);raw['prefix_state']=current;guard('expected_prefix_user','prefix_readback','shared_api',current)
    if branch=='ui':
        exchange('ui','continuation_auth','POST','/api/users/login',{'user':{'email':baseline['email'],'password':'[REDACTED]'}},{'user':current})
        guard('fresh_identity_bound','continuation_auth','ui',current)
        guard('settings_form_bound','continuation','ui',{'username':current['username'],'email':current['email'],'bio':current['bio'],'image':'','new_credential_blank':True})
    payload={'user':{'username':current['username'],'email':current['email'],'bio':BIO}}
    final={**current,'bio':BIO};exchange(branch,'continuation','PUT','/api/user',payload,{'user':final})
    guard('submitted_command','continuation',branch,{'method':'PUT','path':'/api/user','payload':payload})
    raw['observations'].update({branch+'_continuation_started':True,'continuation_write_status':200,'continuation_outcome':'passed'})
    snap('after','shared_readback',final)
    exchange('api','shared_readback','GET','/api/profiles/'+current['username'],None,{'profile':{'username':current['username'],'bio':BIO}})
    raw['final_state']=final;raw['checks']=[{'name':k,'passed':True} for k in ('prefix_profile_matches_input','prefix_related_state_preserved','profile_reference_resolvable','profile_edit_persisted','related_state_preserved')]
    if branch=='ui':
        context={'context_id':'page-1','complete':True,'timed_out':False,'outstanding':[],'failures':0,'admitted':uid,'completed':uid,'reason':'final_shutdown'}
        raw['capture_integrity']['contexts']=[context];emit({'type':'capture_drain','phase':'shared_readback',**context})
    return raw,spec,fixture


class IdentityExtractionTests(unittest.TestCase):
    def test_api_and_ui_unknown_acceptance_remain_unresolved(self):
        for branch in ('api','ui'):
            value=extract(*synthetic(branch));self.assertEqual(value['kind'],'unresolved_policy',value);self.assertTrue(all(value['checks'].values()))
    def test_known_acceptance_control_can_be_clean(self):
        for branch in ('api','ui'):self.assertEqual(extract(*synthetic(branch,unknown=False))['kind'],'clean_observation')
    def test_null_and_empty_rejections_are_complete_without_continuation(self):
        for value in (None,''):
            result=extract(*synthetic(username=value,status=422,unknown=False));self.assertEqual(result['kind'],'matched_rejection',result)
    def test_500_does_not_become_validation_rejection(self):
        self.assertEqual(extract(*synthetic(status=500,unknown=False))['kind'],'application_response_failure')
    def test_unsupported_success_status_is_not_accepted(self):
        self.assertEqual(extract(*synthetic(status=201))['kind'],'application_response_failure')
    def test_snapshot_boolean_cannot_hide_empty_author_query(self):
        raw,spec,fixture=synthetic();read=raw['identity']['prefix']['reads'][1];read['data']['articles']=[];read['data']['articlesCount']=0
        raw['trace'][read['response_sequence']-1]['data']=deepcopy(read['data'])
        self.assertEqual(extract(raw,spec,fixture)['kind'],'missing_evidence')
    def test_projection_not_backed_by_capture_is_incomplete(self):
        raw,spec,fixture=synthetic();raw['identity']['prefix']['data']['user']['username']='fake'
        self.assertEqual(extract(raw,spec,fixture)['kind'],'missing_evidence')
    def test_unexpected_username_or_email_fails(self):
        for key in ('username','email'):
            raw,spec,fixture=synthetic('ui');event=next(e for e in raw['trace'] if e['type']=='response' and e.get('source')=='ui' and e['path']=='/api/users/login');event['data']['user'][key]='wrong'
            self.assertEqual(extract(raw,spec,fixture)['kind'],'missing_evidence')
    def test_ui_full_form_submission_must_match_expected_principal(self):
        raw,spec,fixture=synthetic('ui');event=next(e for e in raw['trace'] if e['type']=='request' and e.get('source')=='ui' and e['path']=='/api/user');event['payload']['user']['username']='pilotresearch'
        self.assertEqual(extract(raw,spec,fixture)['kind'],'missing_evidence')
    def test_forged_pass_flag_is_recomputed(self):
        raw,spec,fixture=synthetic();event=raw['trace'][-1];event['data']['profile']['bio']='not saved'
        self.assertEqual(extract(raw,spec,fixture)['kind'],'missing_evidence')
    def test_truthy_integer_does_not_substitute_for_check_boolean(self):
        raw,spec,fixture=synthetic();raw['checks'][0]['passed']=1
        self.assertEqual(extract(raw,spec,fixture)['kind'],'missing_evidence')
    def test_unregistered_extra_write_rejected(self):
        raw,spec,fixture=synthetic();events=[{'type':t,'source':'api','phase':'shared_readback','method':'DELETE','path':'/api/articles/base','status':204} for t in ('request','response')]
        for e in events:e['sequence']=len(raw['trace'])+1;raw['trace'].append(e)
        self.assertEqual(extract(raw,spec,fixture)['kind'],'missing_evidence')
    def test_unfinished_api_request_is_incomplete(self):
        raw,spec,fixture=synthetic();raw['trace'].pop()
        self.assertEqual(extract(raw,spec,fixture)['kind'],'missing_evidence')
    def test_missing_ui_response_or_drain_is_incomplete(self):
        for kind in ('response','capture_drain'):
            raw,spec,fixture=synthetic('ui');raw['trace']=[e for e in raw['trace'] if not (e['type']==kind and (e.get('source')=='ui' or kind=='capture_drain'))]
            for i,e in enumerate(raw['trace']):e['sequence']=i+1
            self.assertEqual(extract(raw,spec,fixture)['kind'],'missing_evidence')
    def test_before_fixture_cannot_be_replaced_with_other_articles(self):
        raw,spec,fixture=synthetic();fixture['base']['body']='different baseline'
        self.assertEqual(extract(raw,spec,fixture)['kind'],'missing_evidence')
    def test_readback_before_write_is_incomplete_even_after_reindexing(self):
        raw,spec,fixture=synthetic();write=[e for e in raw['trace'] if e['phase']=='continuation'];rest=[e for e in raw['trace'] if e['phase']!='continuation'];raw['trace']=rest+write
        mapping={e['sequence']:i+1 for i,e in enumerate(raw['trace'])}
        for i,e in enumerate(raw['trace']):e['sequence']=i+1
        for value in raw['identity'].values():
            if isinstance(value,dict) and 'reads' in value:
                for read in value['reads']:read['response_sequence']=mapping[read['response_sequence']]
        self.assertEqual(extract(raw,spec,fixture)['kind'],'missing_evidence')
    def test_python_projection_matches_javascript_contract(self):
        raw,spec,fixture=synthetic();snapshot=raw['identity']['prefix'];principal=raw['prefix_state'];refs=[v['slug'] for v in fixture.values()]
        import shutil
        pinned=Path.home()/'.nvm/versions/node/v20.19.6/bin/node'
        node=str(pinned) if pinned.is_file() else shutil.which('node')
        script="import {projectIdentitySnapshot} from './scripts/realworld_identity_v1.mjs';let s='';for await(const c of process.stdin)s+=c;const x=JSON.parse(s);console.log(JSON.stringify(projectIdentitySnapshot(...x)));"
        result=subprocess.run([node,'--input-type=module','-e',script],cwd=ROOT,input=json.dumps([snapshot['reads'],principal,refs]),text=True,capture_output=True,check=True)
        self.assertEqual(json.loads(result.stdout),snapshot['data'])

    def test_actual_api_adapter_output_is_independently_reconstructible(self):
        import tempfile,shutil
        pinned=Path.home()/'.nvm/versions/node/v20.19.6/bin/node'
        node=str(pinned) if pinned.is_file() else shutil.which('node')
        for status in (200,422,500):
            raw,spec,fixture=synthetic(status=status,unknown=status==200)
            traffic=[];request=None
            for event in raw['trace']:
                if event['type']=='request':request=event
                elif event['type']=='response':traffic.append({'request':request,'response':event})
            with tempfile.TemporaryDirectory() as temp:
                d=Path(temp)
                for name,value in [('case.json',spec),('fixture.json',fixture),('traffic.json',traffic)]: (d/name).write_text(json.dumps(value))
                mock=d/'mock.mjs'
                mock.write_text("""import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const traffic=JSON.parse(readFileSync(new URL('./traffic.json',import.meta.url)));let index=0;
globalThis.fetch=async(url,options)=>{
 const row=traffic[index++];assert.ok(row,'Unexpected request');
 assert.equal(new URL(url).pathname+new URL(url).search,row.request.path);assert.equal(options.method,row.request.method);
 const payload=options.body?JSON.parse(options.body):null;
 if(payload?.user?.password)payload.user.password='[REDACTED]';
 assert.deepEqual(payload,row.request.payload??null);
 const data=structuredClone(row.response.data);if(data.user)data.user.token='test-token';
 return new Response(JSON.stringify(data),{status:row.response.status,headers:{'content-type':'application/json'}});
};
process.on('exit',()=>{if(index!==traffic.length)process.exitCode=1;});
""")
                completed=subprocess.run([node,'--import',str(mock),str(ROOT/'scripts/realworld_identity_case_v1.mjs'),'--case',str(d/'case.json'),'--fixture',str(d/'fixture.json'),'--continuation','api','--output',str(d/'result.json')],capture_output=True,text=True,cwd=ROOT)
                self.assertEqual(completed.returncode,0,completed.stdout+completed.stderr)
                emitted=json.loads((d/'result.json').read_text());observed=extract(emitted,spec,fixture)
                self.assertEqual(observed['kind'],'unresolved_policy' if status==200 else 'matched_rejection' if status==422 else 'application_response_failure',observed)

    def test_observed_reference_mismatch_is_retained_when_check_reports_it(self):
        for unknown in (False,True):
            raw,spec,fixture=synthetic(unknown=unknown)
            raw['trace'][-1]['data']['profile']['bio']='not saved'
            next(c for c in raw['checks'] if c['name']=='profile_reference_resolvable')['passed']=False
            raw['observations']['continuation_outcome']='state_mismatch'
            observed=extract(raw,spec,fixture)
            self.assertEqual(observed['kind'],'unresolved_policy' if unknown else 'completed_mismatch',observed)
            self.assertFalse(observed['checks']['profile_reference_resolvable'])

    def test_unrelated_article_change_during_prefix_is_retained_as_mismatch(self):
        raw,spec,fixture=synthetic(unknown=False)
        for stage in ('prefix','after'):
            record=raw['identity'][stage]
            record['reads'][1]['data']['articles'][0]['body']='unexpected mutation'
            raw['trace'][record['reads'][1]['response_sequence']-1]['data']=deepcopy(record['reads'][1]['data'])
            record['data']['articles'][0]['article']['body']='unexpected mutation'
        next(c for c in raw['checks'] if c['name']=='prefix_related_state_preserved')['passed']=False
        raw['observations']['continuation_outcome']='state_mismatch'
        observed=extract(raw,spec,fixture)
        self.assertEqual(observed['kind'],'completed_mismatch',observed)
        self.assertFalse(observed['checks']['prefix_related_state_preserved'])
