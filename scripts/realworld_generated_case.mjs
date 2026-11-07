#!/usr/bin/env node
// Executes exactly the two declared operations; shared oracle observations are separate.
import assert from 'node:assert/strict';
import {createResponseCapture} from './response_capture.mjs';
import {command,audit,enforce,articleIdentity,snapshot,rejectionState} from './realworld_integrity.mjs';
import {createRequire} from 'node:module';
import {readFile,writeFile,rename} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
const options={};for(let i=2;i<process.argv.length;i+=2)options[process.argv[i].slice(2)]=process.argv[i+1];
const c=JSON.parse(await readFile(options.case,'utf8'));
assert.deepEqual(c.operations.map(o=>o.operation_id),['create_article','edit_article_body']);
const producer=c.operations[0],consumer=c.operations[1],input=producer.input.article;
const API='http://127.0.0.1:18765',UI='http://127.0.0.1:18766';
const credentials={email:'pilot@example.com',password:'Pilot-Research-123!'};
const result={schema_version:1,case_id:c.case_id,route:[producer.interface,consumer.interface],status:'running',trace:[],checks:[],coverage:{reached_operations:[],data_consumed:false,state_consumed:false}};
let phase='setup',token,browser,server,context,page,capture,contextCounter=0,requestCounter=0;
result.capture_integrity={version:1,helper_sha256:createHash('sha256').update(await readFile(new URL('./response_capture.mjs',import.meta.url))).digest('hex'),complete:true,contexts:[]};
result.integrity={version:1,helper_sha256:createHash('sha256').update(await readFile(new URL('./realworld_integrity.mjs',import.meta.url))).digest('hex'),guards:[],before:null,rejection:null};
const secrets=new Set([credentials.password]);
function guarded(name,expected,observed,source,stage=phase){stage=stage==='producer'?'prefix':stage==='consumer'?'continuation':stage;const record=audit(name,stage,source,expected,observed);result.integrity.guards.push(record);enforce(record);return record;}
function clean(x,k=''){
  if(/token|password|authorization|cookie/i.test(k))return '[REDACTED]';
  if(Array.isArray(x))return x.map(v=>clean(v));
  if(x&&typeof x==='object')return Object.fromEntries(Object.entries(x).map(([k,v])=>[k,clean(v,k)]));
  if(typeof x==='string')for(const s of secrets)x=x.split(s).join('[REDACTED]');return x;
}
function event(type,data={}){result.trace.push({sequence:result.trace.length+1,phase,type,...clean(data)});}
function parsed(text){try{return JSON.parse(text);}catch{return {non_json:true,characters:text.length,sha256:createHash('sha256').update(text).digest('hex')};}}
async function data(r){const d=parsed(await r.text());if(d?.user?.token)secrets.add(d.user.token);return d;}
async function api(method,path,payload,source='api'){
  if(phase==='producer'&&method==='POST'&&path==='/api/articles')result.coverage.reached_operations.push(producer.operation_id);
  if(phase==='consumer'&&method==='GET'&&path.startsWith('/api/articles/'))result.coverage.reached_operations.push(consumer.operation_id);
  if(source==='api'&&['producer','consumer'].includes(phase)&&['POST','PUT','DELETE'].includes(method))guarded('submitted_command',command(method,path,payload),command(method,path,payload===undefined?null:JSON.parse(JSON.stringify(payload))),'api');
  const request_id=++requestCounter;event('request',{request_id,source,method,path,payload});
  const r=await fetch(API+path,{method,headers:{'content-type':'application/json',...(token?{authorization:`Token ${token}`}:{})},body:payload===undefined?undefined:JSON.stringify(payload),redirect:'manual',signal:AbortSignal.timeout(15000)});
  const d=await data(r);event('response',{request_id,source,method,path,status:r.status,data:d});return {status:r.status,data:d,request_id,response_sequence:result.trace.length};
}
function match(r,method,path){return r.request().method()===method&&new URL(r.url()).pathname===path;}
function state(a){return {title:a.title,description:a.description,body:a.body,tagList:[...new Set(a.tagList)].sort(),author:a.author.username};}
function check(name,passed,detail={}){result.checks.push({name,passed,...clean(detail)});return passed;}
function equal(a,b){return isDeepStrictEqual(a,b);}
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
async function loginUi(){
  await closeCapturedContext('context_replacement');
  if(!server){
    const require=createRequire(import.meta.url);const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
    const marker='--codex-study-case='+createHash('sha256').update(c.case_id+process.pid).digest('hex').slice(0,20);
    // Persist ownership before launch so deadline cleanup can find a browser even
    // when launchServer has not returned its PID. Keep this record after close.
    async function persistOwner(pid){const tmp=options['browser-pid']+'.tmp';await writeFile(tmp,JSON.stringify({pid,marker}));await rename(tmp,options['browser-pid']);}
    await persistOwner(null);
    server=await chromium.launchServer({host:'127.0.0.1',headless:true,executablePath:process.env.CHROME_EXECUTABLE||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',args:[marker,'--disable-background-networking','--disable-component-update','--disable-sync','--no-first-run']});
    await persistOwner(server.process().pid);
    browser=await chromium.connect(server.wsEndpoint());result.browser_version=browser.version();
  }
  context=await browser.newContext({viewport:{width:1280,height:900},timezoneId:'UTC',locale:'en-US',serviceWorkers:'block'});context.setDefaultTimeout(15000);
  await context.route('**/*',r=>{const u=new URL(r.request().url());if(u.protocol==='http:'&&u.hostname==='127.0.0.1'&&['18765','18766'].includes(u.port))return r.continue();event('blocked_external_resource',{url:u.toString()});return r.abort();});
  if(context.routeWebSocket)await context.routeWebSocket('**/*',s=>s.close());
  page=await context.newPage();page.on('pageerror',e=>event('page_error',{message:e.message}));
  capture=createResponseCapture({page,contextId:'page-'+(++contextCounter),getPhase:()=>phase,readResponse:data,
    onRequest:(meta,r)=>{
      event('ui_request',{...meta,payload:r.postData()?parsed(r.postData()):null});
      if(meta.request_phase==='producer'&&meta.method==='POST'&&meta.path==='/api/articles')result.coverage.reached_operations.push(producer.operation_id);
      if(meta.request_phase==='consumer'&&meta.method==='GET'&&meta.path.startsWith('/api/articles/')&&!result.coverage.reached_operations.includes(consumer.operation_id))result.coverage.reached_operations.push(consumer.operation_id);
    },
    onResponse:(meta,r,value)=>event('ui_response',{...meta,status:r.status(),data:value}),
    onError:detail=>event('capture_error',detail)});
  await page.goto(UI+'/#/login');await page.getByLabel('Email',{exact:true}).fill(credentials.email);await page.getByLabel('Password',{exact:true}).fill(credentials.password);
  const rp=page.waitForResponse(r=>match(r,'POST','/api/users/login'));await page.getByRole('button',{name:'Sign in',exact:true}).click();const r=await rp;
  assert.equal(r.status(),200);assert.equal((await r.json()).user.username,'pilotresearch');await page.waitForURL(u=>u.hash==='#/'||u.hash==='');
}
async function uiWrite(method,path,action,expected){
  const rp=page.waitForResponse(r=>r.request().method()===method&&new URL(r.url()).origin===API&&new URL(r.url()).pathname.startsWith('/api/'));await action();const r=await rp;
  const payload=JSON.parse(r.request().postData());const submitted=payload.article;
  const payloadMatches=check(phase+'_actual_payload',equal(submitted,expected),{expected,observed:submitted});
  event('declared_ui_request',{method,path,payload});
  guarded('submitted_command',command(method,path,{article:expected}),command(r.request().method(),new URL(r.url()).pathname,payload),'ui');
  assert.ok(payloadMatches,phase+' actual UI payload differs from declared resolved input');
  return {status:r.status(),data:await data(r),payload_matches:equal(submitted,expected)};
}
async function main(){
  const auth=await api('POST','/api/users/login',{user:credentials});assert.equal(auth.status,200);assert.equal(auth.data.user.username,'pilotresearch');token=auth.data.user.token;
  const initial=await api('GET','/api/articles?author=pilotresearch');assert.equal(initial.status,200);assert.equal(initial.data.articlesCount,0);
  result.integrity.before=await snapshot((method,path)=>api(method,path,undefined,'state_probe'));
  guarded('pre_state_readable',true,result.integrity.before.readable,'shared_api','setup');
  phase='producer';
  let created;
  if(producer.interface==='api')created=await api('POST','/api/articles',producer.input);
  else{
    await loginUi();await page.goto(UI+'/#/article/create');
    for(const [label,key]of[['Title','title'],['Description','description'],['Body','body']])await page.getByLabel(label,{exact:true}).fill(input[key]);
    for(const tag of input.tagList){await page.getByLabel('Tags',{exact:true}).fill(tag);await page.getByLabel('Title',{exact:true}).click();await page.locator('.tag-list .tag-pill').filter({hasText:tag}).waitFor();}
    created=await uiWrite('POST','/api/articles',()=>page.getByRole('button',{name:'Publish Article',exact:true}).click(),input);
  }
  result.prefix_status=created.status;
  if(created.status!==201){
    phase='oracle';const follow=await api('GET','/api/articles?author=pilotresearch');result.failed_prefix_followup={status:follow.status,data:follow.data};
    const after=await snapshot((method,path)=>api(method,path,undefined,'state_probe'));
    result.integrity.rejection={status:rejectionState(result.integrity.before,after),after};
    result.application_outcome=created.status>=500?'prefix_server_error':'prefix_rejected';return;
  }
  const a=created.data.article;result.accepted_producer=state(a);result.resource_reference=a.slug;
  const expected={title:input.title,description:input.description,body:input.body,tagList:[...new Set(input.tagList||[])].sort(),author:'pilotresearch'};
  check('producer_fields',equal(state(a),expected));
  if(!a.slug){result.application_outcome='empty_reference';return;}
  const edit={title:a.title,description:a.description,body:consumer.input.article.body,tagList:a.tagList};
  result.resolved_consumer_input={article:edit};
  phase='consumer';
  let loaded,edited;
  if(consumer.interface==='api'){
    loaded=await api('GET',`/api/articles/${encodeURIComponent(a.slug)}`);
    result.coverage.data_consumed=true;event('consumed_dependency',{field:'article.slug',interface:'api',via:'declared_consumer_GET',reference:a.slug,status:loaded.status});
  }else{
    await loginUi();const rp=page.waitForResponse(r=>match(r,'GET',`/api/articles/${a.slug}`));await page.goto(UI+`/#/article/${encodeURIComponent(a.slug)}/edit`);const r=await rp;loaded={status:r.status(),data:await data(r)};
    result.coverage.data_consumed=true;event('consumed_dependency',{field:'article.slug',interface:'ui',via:'native_editor_GET',reference:a.slug,status:loaded.status});
  }
  if(loaded.status!==200){result.application_outcome='consumer_read_failed';return;}
  const stateLoaded=check('consumer_loaded_state',equal(state(loaded.data.article),expected));
  guarded('loaded_article_binding',articleIdentity(a),articleIdentity(loaded.data.article),consumer.interface);
  if(consumer.interface==='api'){
    edited=await api('PUT',`/api/articles/${a.slug}`,{article:edit});result.coverage.state_consumed=stateLoaded;
  }else{
    await page.waitForFunction(v=>document.querySelector('textarea[aria-label="Body"]')?.value===v,a.body);
    const form={title:await page.getByLabel('Title',{exact:true}).inputValue(),description:await page.getByLabel('Description',{exact:true}).inputValue(),body:await page.getByLabel('Body',{exact:true}).inputValue()};
    const formLoaded=check('native_form_loaded',form.title===a.title&&form.description===a.description&&form.body===a.body,{observed:form});
    await page.getByLabel('Body',{exact:true}).fill(edit.body);
    edited=await uiWrite('PUT',`/api/articles/${a.slug}`,()=>page.getByRole('button',{name:'Publish Article',exact:true}).click(),edit);
    result.coverage.state_consumed=stateLoaded&&formLoaded&&edited.payload_matches;
  }
  if(result.coverage.state_consumed)event('consumed_dependency',{field:'article.editable_state',interface:consumer.interface,via:'declared_consumer_PUT',bound_payload:edit});
  result.consumer_status=edited.status;if(edited.status!==200){result.application_outcome='consumer_write_failed';return;}
  phase='oracle';const slug=edited.data.article.slug;const final=await api('GET',`/api/articles/${encodeURIComponent(slug)}`);
  check('persisted_business_state',final.status===200&&equal(state(final.data.article),{...expected,body:edit.body}));
  // Shared fresh native read is deliberately outside declared coverage.
  await loginUi();const fresh=page.waitForResponse(r=>match(r,'GET',`/api/articles/${slug}`));await page.goto(UI+`/#/article/${encodeURIComponent(slug)}`);const r=await fresh;const rendered=await data(r);
  check('shared_ui_read',r.status()===200&&equal(state(rendered.article),{...expected,body:edit.body}));
  await page.waitForFunction(value=>document.querySelector('#article-content')?.textContent?.replace(/\s+/g,' ').trim()===value,edit.body);
  check('shared_ui_render',(await page.locator('#article-content').innerText()).trim()===edit.body);
  const count=await api('GET','/api/articles?author=pilotresearch');check('one_article',count.status===200&&count.data.articlesCount===1);
  result.final_state=state(final.data.article);result.application_outcome=result.checks.every(x=>x.passed)?'passed':'state_mismatch';
}
try{await main();result.status='completed';}catch(e){result.status='adapter_error';result.error={phase,name:e.name,message:e.message};}
finally{
  try{await closeCapturedContext('final_shutdown');}catch(e){result.capture_integrity.complete=false;result.status='adapter_error';result.error??={phase,name:e.name,message:e.message};}
  if(browser)await browser.close().catch(()=>{});if(server)await server.close().catch(()=>{});
  result.finished_at=new Date().toISOString();await writeFile(options.output,JSON.stringify(clean(result),null,2)+'\n');
  process.exitCode=result.status==='completed'?0:1;
}
