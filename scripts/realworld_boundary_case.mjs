#!/usr/bin/env node
// One registered prefix and one continuation, after an orchestrator-owned reset.
import assert from 'node:assert/strict';
import {createResponseCapture} from './response_capture.mjs';
import {command,audit,enforce,profileBundle,profileForm,articleIdentity,commentIdentity,commentPath,snapshot,rejectionState} from './realworld_integrity.mjs';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {readFile,writeFile} from 'node:fs/promises';

const opts={};
for(let i=2;i<process.argv.length;i+=2) opts[process.argv[i].replace(/^--/,'')]=process.argv[i+1];
const spec=JSON.parse(await readFile(opts.case,'utf8'));
const fixture=JSON.parse(await readFile(opts.fixture,'utf8'));
const branch=opts.continuation;
assert.ok(['api','ui'].includes(branch));
const API='http://127.0.0.1:18765', UI='http://127.0.0.1:18766';
const email='pilot@example.com', password='Pilot-Research-123!';
const result={schema_version:1,candidate_id:spec.candidate_id,workflow:spec.workflow,
  prefix_interface:spec.prefix_interface,continuation_interface:branch,expectation:spec.expectation,
  started_at:new Date().toISOString(),execution_status:'running',oracle_revision:2,trace:[],checks:[],observations:{ui_continuation_started:false,api_continuation_started:false}};
let phase='setup',token,browser,context,page,currentUser,capture,contextCounter=0;
result.capture_integrity={version:1,helper_sha256:createHash('sha256').update(await readFile(new URL('./response_capture.mjs',import.meta.url))).digest('hex'),complete:true,contexts:[]};
result.integrity={version:1,helper_sha256:createHash('sha256').update(await readFile(new URL('./realworld_integrity.mjs',import.meta.url))).digest('hex'),guards:[],before:null,rejection:null};
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
function articleState(a){return a?{slug:a.slug,title:a.title,description:a.description,body:a.body,tagList:a.tagList,author:a.author?.username}:null;}
function commentState(c){return c?{id:c.id,body:c.body,author:c.author?.username}:null;}
function articleBusiness(a){const state=articleState(a);if(state)delete state.slug;return state;}
function equal(a,b){return JSON.stringify(a)===JSON.stringify(b);}
function expectedArticle(original,changes){
  return {title:changes.title??original.title,description:changes.description??original.description,
    body:changes.body??original.body,tagList:changes.tagList??original.tagList??[],author:'pilotresearch'};
}
async function closeCapturedContext(reason){
  if(!context)return;
  const closing=context,ownedCapture=capture;context=null;capture=null;
  try{
    assert.ok(ownedCapture,'Context has no capture owner');
    const record=await ownedCapture.sealAndDrain({timeoutMs:5000});
    result.capture_integrity.contexts.push({...record,reason});
    result.capture_integrity.complete=result.capture_integrity.complete&&record.complete;
    event('capture_drain',{...record,reason});
    assert.ok(record.complete,'Incomplete API response capture');
  }finally{await closing.close();}
}
async function freshLogin(){
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
}
async function uiRequest(method,path,action,expectedPayload=null){
  const p=page.waitForResponse(r=>r.request().method()===method&&new URL(r.url()).origin===API&&new URL(r.url()).pathname.startsWith('/api/'));
  await action();const r=await p;const actual=r.request().postData()?JSON.parse(r.request().postData()):null;
  guarded('submitted_command',command(method,path,expectedPayload),command(r.request().method(),new URL(r.url()).pathname,actual),'ui');
  return {status:r.status(),data:await responseData(r)};
}
async function articlePage(slug,edit=false){
  const p=page.waitForResponse(r=>match(r,'GET',`/api/articles/${slug}`));
  await page.goto(UI+`/#/article/${encodeURIComponent(slug)}${edit?'/edit':''}`);
  const r=await p;return {status:r.status(),data:await responseData(r)};
}
async function settingsEdit(bio,boundUser){
  await page.goto(UI+'/#/settings');
  const form={};for(const [key,label]of[['username','Username'],['email','Email'],['bio','Bio'],['image','Avatar picture url']])form[key]=await page.getByLabel(label,{exact:true}).inputValue();
  form.new_credential_blank=(await page.getByLabel('New password',{exact:true}).inputValue())==='';
  guarded('settings_form_bound',profileForm(boundUser),form,'ui');
  await page.getByLabel('Bio',{exact:true}).fill(bio);
  return uiRequest('PUT','/api/user',()=>page.getByRole('button',{name:'Update Settings',exact:true}).click(),profileBundle(boundUser,bio));
}
async function run(){
  const auth=await api('POST','/api/users/login',{user:{email,password}});assert.equal(auth.status,200);
  assert.equal(auth.data.user.email,email);token=auth.data.user.token;
  const baseline=await api('GET','/api/user');assert.equal(baseline.status,200);assert.equal(baseline.data.user.username,'pilotresearch');
  result.actor={email,stable_fixture_username:'pilotresearch'};
  result.integrity.before=await snapshot((method,path)=>api(method,path,undefined,'state_probe'));
  guarded('pre_state_readable',true,result.integrity.before.readable,'shared_api','setup');
  phase='prefix';
  let prefix,target;
  if(spec.workflow==='article-update-comment'){
    target=fixture[spec.target_fixture];result.original_reference=target.slug;
  }
  if(spec.prefix_interface==='ui'){
    await freshLogin();
    if(spec.workflow==='comment-create-delete'){
      const loaded=await articlePage(fixture.base.slug);assert.equal(loaded.status,200);
      await page.getByLabel('Write comment',{exact:true}).fill(spec.prefix_payload.body);
      prefix=await uiRequest('POST',`/api/articles/${fixture.base.slug}/comments`,()=>page.getByRole('button',{name:'Submit',exact:true}).click(),{comment:spec.prefix_payload});
    }else if(spec.workflow==='profile-update-edit')prefix=await settingsEdit(spec.prefix_payload.bio,baseline.data.user);
    else if(spec.workflow==='article-update-comment'){
      const loaded=await articlePage(target.slug,true);assert.equal(loaded.status,200);
      await page.waitForFunction(v=>document.querySelector('textarea[aria-label="Body"]')?.value===v,target.body);
      assert.equal(await page.getByLabel('Title',{exact:true}).inputValue(),spec.prefix_payload.title);
      assert.equal(await page.getByLabel('Description',{exact:true}).inputValue(),spec.prefix_payload.description);
      await page.getByLabel('Body',{exact:true}).fill(spec.prefix_payload.body);
      prefix=await uiRequest('PUT',`/api/articles/${target.slug}`,()=>page.getByRole('button',{name:'Publish Article',exact:true}).click(),{article:spec.prefix_payload});
    }
    else throw new Error('Unimplemented native producer');
  }else if(spec.workflow==='article-create-edit')prefix=await api('POST','/api/articles',{article:spec.prefix_payload});
  else if(spec.workflow==='comment-create-delete')prefix=await api('POST',`/api/articles/${fixture.base.slug}/comments`,{comment:spec.prefix_payload});
  else if(spec.workflow==='profile-update-edit')prefix=await api('PUT','/api/user',{user:spec.prefix_payload});
  else if(spec.workflow==='article-update-comment'){
    prefix=await api('PUT',`/api/articles/${target.slug}`,{article:spec.prefix_payload});
  }else throw new Error('Unknown workflow');
  result.observations.prefix_status=prefix.status;
  result.observations.prefix_response=clean(prefix.data);
  if(prefix.status<200||prefix.status>=300){
    result.observations.prefix_outcome=prefix.status>=500?'server_error':'rejected';
    result.observations.continuation_outcome='not_executed_prefix_unsuccessful';
    phase='failed_prefix_followup';
    const path=spec.workflow==='profile-update-edit'?'/api/user':spec.workflow==='comment-create-delete'?`/api/articles/${fixture.base.slug}/comments`:'/api/articles?author=pilotresearch';
    const follow=await api('GET',path);
    result.observations.failed_prefix_api_followup={status:follow.status,data:clean(follow.data)};
    const unchanged=spec.workflow==='profile-update-edit'
      ? follow.status===200&&equal(userState(follow.data.user),userState(baseline.data.user))
      : spec.workflow==='comment-create-delete'
        ? follow.status===200&&follow.data.comments.length===0
        : follow.status===200&&follow.data.articlesCount===3;
    const after=await snapshot((method,path)=>api(method,path,undefined,'state_probe'));
    result.integrity.rejection={status:rejectionState(result.integrity.before,after),after};
    // Retain the older, narrower predicate as a separately scoped observation.
    check('failed_prefix_observable_state_unchanged',unchanged,{scope:'legacy narrow predicate; full observable-state comparison is integrity.rejection'});
    return;
  }
  result.observations.prefix_outcome='accepted';
  phase='continuation';
  let before,continued;
  if(spec.workflow==='article-create-edit'||spec.workflow==='article-update-comment'){
    const a=prefix.data.article;assert.ok(a&&typeof a.slug==='string','article response identity');
    result.prefix_state=articleState(a);
    const expected=expectedArticle(target||{},spec.prefix_payload);
    check('prefix_fields_match_declared_input',equal(articleBusiness(a),expected));
    if(target){
      const original=await api('GET',`/api/articles/${target.slug}`);
      result.observations.original_reference_read={status:original.status,article:articleState(original.data.article)};
    }
    if(!a.slug){
      result.observations.continuation_outcome='empty_returned_reference';
      result.observations.reference_api_probe=await api('GET','/api/articles/');
      return;
    }
    if(branch==='api'){result.observations.api_continuation_started=true;before=await api('GET',`/api/articles/${encodeURIComponent(a.slug)}`);}
    else{await freshLogin();result.observations.ui_continuation_started=true;before=await articlePage(a.slug,spec.workflow==='article-create-edit');}
    result.observations.consumer_read_status=before.status;
    if(before.status!==200){result.observations.continuation_outcome='returned_reference_not_resolvable';return;}
    check('consumer_loaded_prefix_fields',JSON.stringify(articleState(before.data.article))===JSON.stringify(articleState(a)));
    guarded('loaded_article_binding',articleIdentity(a),articleIdentity(before.data.article),branch);
    if(spec.workflow==='article-create-edit'){
      const updated={title:a.title,description:a.description,body:'Body after meaningful continuation.',tagList:a.tagList};
      if(branch==='api')continued=await api('PUT',`/api/articles/${a.slug}`,{article:updated});
      else{
        await page.waitForFunction(v=>document.querySelector('textarea[aria-label="Body"]')?.value===v,a.body);
        await page.getByLabel('Body',{exact:true}).fill(updated.body);
        continued=await uiRequest('PUT',`/api/articles/${a.slug}`,()=>page.getByRole('button',{name:'Publish Article',exact:true}).click(),{article:updated});
      }
      result.observations.continuation_write_status=continued.status;
      if(continued.status!==200){result.observations.continuation_outcome='write_failed';return;}
      const final=await api('GET',`/api/articles/${encodeURIComponent(continued.data.article.slug)}`);
      check('persisted_continuation',final.status===200&&equal(articleBusiness(final.data.article),{...expected,body:updated.body}));
      result.final_state=articleState(final.data.article);
    }else{
      const commentBody='Comment after article update.';
      if(branch==='api')continued=await api('POST',`/api/articles/${a.slug}/comments`,{comment:{body:commentBody}});
      else{
        await page.getByLabel('Write comment',{exact:true}).fill(commentBody);
        continued=await uiRequest('POST',`/api/articles/${a.slug}/comments`,()=>page.getByRole('button',{name:'Submit',exact:true}).click(),{comment:{body:commentBody}});
      }
      result.observations.continuation_write_status=continued.status;
      const final=await api('GET',`/api/articles/${a.slug}/comments`);
      check('comment_relationship_persisted',continued.status===201&&final.status===200&&final.data.comments.length===1&&final.data.comments[0].body===commentBody);
      const returned=continued.data.comment;guarded('created_comment_identity_valid',true,Number.isSafeInteger(returned?.id)&&returned.id>0&&returned.body===commentBody&&returned.author?.username==='pilotresearch',branch,'shared_readback');
      guarded('created_comment_parent_binding',[commentIdentity(returned)],final.data.comments.filter(x=>x.id===returned.id).map(commentIdentity),branch,'shared_readback');
      const parent=await api('GET',`/api/articles/${a.slug}`);
      check('parent_article_preserved',parent.status===200&&equal(articleState(parent.data.article),articleState(before.data.article)));
      result.observations.parent_after=articleState(parent.data.article);
      result.final_state={article:articleState(before.data.article),comments:final.data.comments?.map(commentState)};
    }
  }else if(spec.workflow==='comment-create-delete'){
    const c=prefix.data.comment;assert.ok(Number.isInteger(c?.id));result.prefix_state=commentState(c);
    check('prefix_comment_matches_input',c.body===spec.prefix_payload.body&&c.author?.username==='pilotresearch');
    if(branch==='api'){result.observations.api_continuation_started=true;before=await api('GET',`/api/articles/${fixture.base.slug}/comments`);}
    else{
      await freshLogin();result.observations.ui_continuation_started=true;const rp=page.waitForResponse(r=>match(r,'GET',`/api/articles/${fixture.base.slug}/comments`));
      await articlePage(fixture.base.slug);const r=await rp;before={status:r.status(),data:await responseData(r)};
    }
    check('comment_loaded_in_parent',before.status===200&&before.data.comments.some(x=>x.id===c.id&&x.body===c.body));
    guarded('loaded_comment_binding',[commentIdentity(c)],before.data.comments.filter(x=>x.id===c.id).map(commentIdentity),branch);
    const path=commentPath(fixture.base.slug,c.id);
    if(branch==='api')continued=await api('DELETE',path);
    else {guarded('singleton_delete_target',1,before.data.comments.length,'ui');await page.getByRole('button',{name:'Delete comment',exact:true}).waitFor({state:'attached'});guarded('unique_native_delete_control',1,await page.getByRole('button',{name:'Delete comment',exact:true}).count(),'ui');continued=await uiRequest('DELETE',path,()=>page.getByRole('button',{name:'Delete comment',exact:true}).press('Enter'));}
    result.observations.continuation_write_status=continued.status;
    const final=await api('GET',`/api/articles/${fixture.base.slug}/comments`);
    check('deletion_persisted',continued.status===204&&final.status===200&&final.data.comments.length===0);
    const parent=await api('GET',`/api/articles/${fixture.base.slug}`);
    check('parent_article_preserved',parent.status===200&&equal(articleState(parent.data.article),articleState(fixture.base)));
    result.observations.parent_after=articleState(parent.data.article);
    result.final_state={comments:final.data.comments};
  }else{
    const user=await api('GET','/api/user');
    result.prefix_state=userState(user.data.user);
    if(user.status!==200){result.observations.continuation_outcome='current_user_unreadable';return;}
    const expectedUser={...userState(baseline.data.user),...spec.prefix_payload};
    if(expectedUser.bio==='')expectedUser.bio=null;
    if(expectedUser.image==='')expectedUser.image=null;
    check('prefix_profile_matches_input',equal(userState(user.data.user),expectedUser));
    const bio='Bio after meaningful continuation.';
    if(branch==='ui'){
      await freshLogin();check('fresh_ui_principal_matches',JSON.stringify(userState(currentUser))===JSON.stringify(userState(user.data.user)));
      result.observations.ui_continuation_started=true;continued=await settingsEdit(bio,user.data.user);
    }else{
      const payload={username:user.data.user.username,email:user.data.user.email,bio};
      if(user.data.user.image!==null)payload.image=user.data.user.image;
      result.observations.api_continuation_started=true;continued=await api('PUT','/api/user',{user:payload});
    }
    result.observations.continuation_write_status=continued.status;
    const final=await api('GET','/api/user');
    check('profile_edit_persisted',continued.status===200&&final.status===200&&equal(userState(final.data.user),{...expectedUser,bio}));
    const profile=await api('GET',`/api/profiles/${encodeURIComponent(user.data.user.username)}`);
    check('profile_reference_resolvable',profile.status===200&&profile.data.profile.bio===bio);
    result.final_state=userState(final.data.user);
  }
  result.observations.continuation_outcome=result.checks.every(c=>c.passed)?'passed':'state_mismatch';
}
try{await run();result.execution_status='completed';}
catch(e){result.execution_status='runner_or_unadjudicated_error';result.error={phase,name:e.name,message:e.message};}
finally{
  try{try{await closeCapturedContext('final_shutdown');}finally{if(browser)await browser.close();}}catch(e){result.capture_integrity.complete=false;result.execution_status='runner_or_unadjudicated_error';result.error??={phase,name:e.name,message:e.message};}
  result.completed_at=new Date().toISOString();
  await writeFile(opts.output,JSON.stringify(clean(result),null,2)+'\n');
  process.stdout.write(JSON.stringify({candidate_id:spec.candidate_id,branch,status:result.execution_status,observations:result.observations.continuation_outcome,error:result.error})+'\n');
  process.exitCode=result.execution_status==='completed'?0:1;
}
