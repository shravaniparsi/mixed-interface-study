#!/usr/bin/env node
// One registered prefix and one continuation, after an orchestrator-owned reset.
import assert from 'node:assert/strict';
import {PhaseClock} from './phase_clock.mjs';
import {exact} from './realworld_normalization.mjs';
import {profileIdentityExpected,identitySnapshot} from './realworld_identity_v1.mjs';
const clock=new PhaseClock();
import {createResponseCapture} from './response_capture.mjs';
import {command,audit,enforce,profileBundle,profileForm} from './realworld_integrity.mjs';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {readFile,writeFile} from 'node:fs/promises';

const opts={};
for(let i=2;i<process.argv.length;i+=2) opts[process.argv[i].replace(/^--/,'')]=process.argv[i+1];
const spec=JSON.parse(await readFile(opts.case,'utf8'));
const fixture=JSON.parse(await readFile(opts.fixture,'utf8'));
assert.equal(spec.workflow,'profile-update-edit');assert.equal(spec.prefix_interface,'api');
const branch=opts.continuation;
assert.ok(['api','ui'].includes(branch));
const API='http://127.0.0.1:18765', UI='http://127.0.0.1:18766';
const email='pilot@example.com', password='Pilot-Research-123!';
const result={schema_version:1,candidate_id:spec.candidate_id,workflow:spec.workflow,
  prefix_interface:spec.prefix_interface,continuation_interface:branch,expectation:spec.expectation,
  started_at:new Date().toISOString(),execution_status:'running',oracle_revision:3,trace:[],checks:[],observations:{ui_continuation_started:false,api_continuation_started:false}};
let phase='setup',token,browser,context,page,currentUser,capture,contextCounter=0;
result.capture_integrity={version:1,helper_sha256:createHash('sha256').update(await readFile(new URL('./response_capture.mjs',import.meta.url))).digest('hex'),complete:true,contexts:[]};
result.integrity={version:1,helper_sha256:createHash('sha256').update(await readFile(new URL('./realworld_integrity.mjs',import.meta.url))).digest('hex'),guards:[]};
result.identity={version:1,helper_sha256:createHash('sha256').update(await readFile(new URL('./realworld_identity_v1.mjs',import.meta.url))).digest('hex'),before:null,prefix:null,after:null};
const secrets=new Set([password]);
function guarded(name,expected,observed,source,stage=phase){const record=audit(name,stage,source,expected,observed);result.integrity.guards.push(record);enforce(record);return record;}

function clean(x,key=''){
  if(/token|password|authorization|cookie/i.test(key))return '[REDACTED]';
  if(Array.isArray(x))return x.map(v=>clean(v));
  if(x&&typeof x==='object')return Object.fromEntries(Object.entries(x).map(([k,v])=>[k,clean(v,k)]));
  if(typeof x==='string'){for(const s of secrets)x=x.split(s).join('[REDACTED]');return x;}
  return x;
}
function event(type,data={}){result.trace.push({sequence:result.trace.length+1,phase,type,...clean(data)});}
function body(text){try{return JSON.parse(text);}catch{return {non_json:true,bytes:Buffer.byteLength(text),sha256:createHash('sha256').update(text).digest('hex')};}}
async function responseData(response){const data=body(await response.text());if(data?.user?.token)secrets.add(data.user.token);return data;}
async function api(method,path,payload,source='api'){
  assert.ok(path.startsWith('/api/'));
  if(source==='api'&&['prefix','continuation'].includes(phase)&&['POST','PUT','DELETE'].includes(method))guarded('submitted_command',command(method,path,payload),command(method,path,payload===undefined?null:JSON.parse(JSON.stringify(payload))),'api');
  event('request',{source,method,path,payload});
  const response=await fetch(API+path,{method,headers:{'content-type':'application/json',...(token?{authorization:`Token ${token}`}:{})},body:payload===undefined?undefined:JSON.stringify(payload),redirect:'manual',signal:AbortSignal.timeout(12000)});
  const data=await responseData(response);event('response',{source,method,path,status:response.status,data});
  return {status:response.status,data,response_sequence:result.trace.length};
}
function match(response,method,path){return response.request().method()===method&&new URL(response.url()).pathname===path;}
function check(name,passed,details={}){result.checks.push({name,passed,...clean(details)});return passed;}
function userState(u){return u?{username:u.username,email:u.email,bio:u.bio,image:u.image}:null;}
const equal=exact;
async function closeCapturedContext(reason){
  if(!context)return;
  const closing=context,ownedCapture=capture;context=null;capture=null;
  try{
    assert.ok(ownedCapture,'Context has no capture owner');
    const record=await clock.during('evidence_finalization',()=>ownedCapture.sealAndDrain({timeoutMs:5000}));
    result.capture_integrity.contexts.push({...record,reason});
    result.capture_integrity.complete=result.capture_integrity.complete&&record.complete;
    event('capture_drain',{...record,reason});
    assert.ok(record.complete,'Incomplete API response capture');
  }finally{await clock.during('browser_teardown',()=>closing.close());}
}
async function freshLogin(){return clock.during('authentication_session',async()=>{
  await closeCapturedContext('context_replacement');
  if(!browser){const require=createRequire(import.meta.url);const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
    browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',args:['--disable-background-networking','--disable-component-update','--disable-sync','--no-first-run']});
    result.browser_version=browser.version();}
  context=await browser.newContext({viewport:{width:1280,height:900},locale:'en-US',timezoneId:'UTC',serviceWorkers:'block'});
  context.setDefaultTimeout(12000);
  await context.route('**/*',r=>{
    const u=new URL(r.request().url());
    if(u.protocol==='http:'&&u.hostname==='127.0.0.1'&&['18765','18766'].includes(u.port))return r.continue();
    event('external_resource_blocked',{url:u.toString()});return r.abort();
  });
  if(context.routeWebSocket)await context.routeWebSocket('**/*',s=>s.close());
  page=await context.newPage();
  capture=createResponseCapture({page,contextId:'page-'+(++contextCounter),getPhase:()=>phase,readResponse:responseData,
    onRequest:(meta,r)=>event('request',{source:'ui',...meta,payload:r.postData()?body(r.postData()):null}),
    onResponse:(meta,r,value)=>event('response',{source:'ui',...meta,status:r.status(),data:value}),
    onError:detail=>event('capture_error',detail)});
  page.on('pageerror',e=>event('page_error',{message:e.message}));
  await page.goto(UI+'/#/login');
  await page.getByLabel('Email',{exact:true}).fill(email);await page.getByLabel('Password',{exact:true}).fill(password);
  const rp=page.waitForResponse(r=>match(r,'POST','/api/users/login'));
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  const r=await rp;assert.equal(r.status(),200,'native login');const d=await r.json();
  assert.equal(d.user.email,email,'same actor email');currentUser=d.user;
  await page.waitForURL(u=>u.hash==='#/'||u.hash==='');
});}
async function uiRequest(method,path,action,expectedPayload=null){
  const p=page.waitForResponse(r=>r.request().method()===method&&new URL(r.url()).origin===API&&new URL(r.url()).pathname.startsWith('/api/'));
  await action();const r=await p;const actual=r.request().postData()?JSON.parse(r.request().postData()):null;
  guarded('submitted_command',command(method,path,expectedPayload),command(r.request().method(),new URL(r.url()).pathname,actual),'ui');
  return {status:r.status(),data:await responseData(r)};
}
async function settingsEdit(bio,boundUser){
  await page.goto(UI+'/#/settings');
  const form={};for(const [key,label]of[['username','Username'],['email','Email'],['bio','Bio'],['image','Avatar picture url']])form[key]=await page.getByLabel(label,{exact:true}).inputValue();
  form.new_credential_blank=(await page.getByLabel('New password',{exact:true}).inputValue())==='';
  guarded('settings_form_bound',profileForm(boundUser),form,'ui');
  await page.getByLabel('Bio',{exact:true}).fill(bio);
  return uiRequest('PUT','/api/user',()=>page.getByRole('button',{name:'Update Settings',exact:true}).click(),profileBundle(boundUser,bio));
}
function relatedAfterBio(value,username,bio){
  const output=JSON.parse(JSON.stringify(value));
  for(const row of output){
    for(const entity of [row.article,...row.comments]){
      if(entity.author?.username===username&&Object.hasOwn(entity.author,'bio'))entity.author.bio=bio;
    }
  }
  return output;
}
async function run(){
  const references=['base','duplicate_first','duplicate'].map(k=>fixture[k].slug);
  const take=(principal)=>identitySnapshot((method,path)=>api(method,path,undefined,'state_probe'),principal,references);
  clock.switch('authentication_session');
  const auth=await api('POST','/api/users/login',{user:{email,password}});assert.equal(auth.status,200);
  assert.equal(auth.data.user.email,email);token=auth.data.user.token;
  const baseline=await api('GET','/api/user');assert.equal(baseline.status,200);
  assert.equal(baseline.data.user.username,'pilotresearch');assert.equal(baseline.data.user.email,email);
  result.actor={email,stable_fixture_username:'pilotresearch'};
  clock.switch('prefix_state_inspection');
  result.identity.before=await take(baseline.data.user);
  guarded('pre_state_readable',true,result.identity.before.readable,'shared_api','setup');
  phase='prefix';clock.switch('producer');
  const prefix=await api('PUT','/api/user',{user:spec.prefix_payload});
  result.observations.prefix_status=prefix.status;result.observations.prefix_response=clean(prefix.data);
  if(prefix.status!==200){
    phase='failed_prefix_followup';clock.switch('shared_verification');
    result.identity.after=await take(baseline.data.user);
    result.observations.prefix_outcome=prefix.status>=200&&prefix.status<300?'unsupported_success_status':prefix.status>=500?'server_error':'rejected';
    result.observations.continuation_outcome='not_executed_prefix_unsuccessful';return;
  }
  result.observations.prefix_outcome='accepted';
  const expected=profileIdentityExpected(userState(baseline.data.user),spec.prefix_payload);
  phase='prefix_readback';clock.switch('prefix_state_inspection');
  result.identity.prefix=await take(expected);
  if(!result.identity.prefix.readable){result.observations.continuation_outcome='identity_binding_incomplete';return;}
  result.prefix_state=result.identity.prefix.data.user;
  check('prefix_profile_matches_input',equal(result.prefix_state,expected));
  const prefixRelated=JSON.parse(JSON.stringify(result.identity.before.data.articles));
  for(const row of prefixRelated){for(const entity of [row.article,...row.comments]){
    if(entity.author?.username===baseline.data.user.username){
      for(const key of ['username','bio','image'])if(Object.hasOwn(entity.author,key))entity.author[key]=expected[key];
    }
  }}
  check('prefix_related_state_preserved',equal(prefixRelated,result.identity.prefix.data.articles)&&equal(result.identity.before.data.tags,result.identity.prefix.data.tags));
  // Never bind a continuation to an observed account that differs from the registered input.
  guarded('expected_prefix_user',expected,result.prefix_state,'shared_api','prefix_readback');
  const bio='Bio after meaningful continuation.';let continued;
  if(branch==='ui'){
    phase='continuation_auth';await freshLogin();
    guarded('fresh_identity_bound',expected,userState(currentUser),'ui','continuation_auth');
    phase='continuation';clock.switch('assigned_continuation');
    result.observations.ui_continuation_started=true;continued=await settingsEdit(bio,expected);
  }else{
    phase='continuation';clock.switch('assigned_continuation');
    result.observations.api_continuation_started=true;continued=await api('PUT','/api/user',profileBundle(expected,bio));
  }
  result.observations.continuation_write_status=continued.status;
  phase='shared_readback';clock.switch('shared_verification');
  result.identity.after=await take(expected);
  const profile=await api('GET','/api/profiles/'+encodeURIComponent(expected.username));
  check('profile_reference_resolvable',profile.status===200&&profile.data.profile?.username===expected.username&&profile.data.profile?.bio===bio);
  check('profile_edit_persisted',continued.status===200&&result.identity.after.readable&&equal(result.identity.after.data.user,{...expected,bio}));
  if(result.identity.after.readable){
    result.final_state=result.identity.after.data.user;
    check('related_state_preserved',equal(relatedAfterBio(result.identity.prefix.data.articles,expected.username,bio),result.identity.after.data.articles)&&equal(result.identity.prefix.data.tags,result.identity.after.data.tags));
  }
  result.observations.continuation_outcome=result.checks.every(c=>c.passed)?'passed':'state_mismatch';
}
try{await run();result.execution_status='completed';}
catch(e){result.execution_status='runner_or_unadjudicated_error';result.error={phase,name:e.name,message:e.message};}
finally{
  try{try{await closeCapturedContext('final_shutdown');}finally{if(browser)await clock.during('browser_teardown',()=>browser.close());}}catch(e){result.capture_integrity.complete=false;result.execution_status='runner_or_unadjudicated_error';result.error??={phase,name:e.name,message:e.message};}
  result.timing=clock.finish();
  result.normalization_policy='realworld-identity-preparation-v1';
  result.completed_at=new Date().toISOString();
  await writeFile(opts.output,JSON.stringify(clean(result),null,2)+'\n');
  process.stdout.write(JSON.stringify({candidate_id:spec.candidate_id,branch,status:result.execution_status,observations:result.observations.continuation_outcome,error:result.error})+'\n');
  process.exitCode=result.execution_status==='completed'?0:1;
}
