#!/usr/bin/env node
/** Native executor for the pinned Quartz v2 registry. It never resets a server. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {createHash,randomBytes} from 'node:crypto';
import {mkdir,readFile,writeFile,rename} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {parseArgs} from 'node:util';

export const REGISTRY_SHA256='fd575f01818659c1efde48514392b8cba8b06812f3e385049314edfcae58d2e0';
export const JOB_PATH='/quartz-manager/jobs/RESEARCH/pilot-job';
export const canonical=x=>Array.isArray(x)?x.map(canonical):x&&typeof x==='object'?Object.fromEntries(Object.keys(x).sort().map(k=>[k,canonical(x[k])])):x;
export const digest=x=>createHash('sha256').update(typeof x==='string'||Buffer.isBuffer(x)?x:JSON.stringify(canonical(x))).digest('hex');
export const equal=(a,b)=>JSON.stringify(canonical(a))===JSON.stringify(canonical(b));
export function registryFromBytes(bytes){
  assert.equal(digest(bytes),REGISTRY_SHA256,'Registry bytes differ from the reviewed v2 catalog; do not silently run a changed corpus.');
  const r=JSON.parse(bytes);assert.equal(r.manifest.manifest_id,'quartz-stored-job-create-description-edit-v2');
  assert.equal(r.cases.length,44);assert.equal(new Set(r.cases.map(c=>c.case_id)).size,44);return r;
}
export function selectCases(registry,mode='controls'){
  assert.ok(['controls','all'].includes(mode),'mode must be controls or all');
  const cases=registry.cases.filter(c=>mode==='all'||c.intervention==='route_only');
  if(mode==='controls')assert.equal(cases.length,4);return cases;
}
export function business(job){
  assert.ok(job&&typeof job==='object'&&!Array.isArray(job),'Missing stored job object');
  return Object.fromEntries(['jobKeyDTO','jobClassName','description','durable','requestsRecovery','jobDataMap','triggerKeys'].map(k=>[k,job[k]]));
}
export function bindConsumer(job,description){
  assert.ok(typeof job?.jobKeyDTO?.group==='string'&&typeof job?.jobKeyDTO?.name==='string','Returned resource identity is missing');
  const path='/quartz-manager/jobs/'+encodeURIComponent(job.jobKeyDTO.group)+'/'+encodeURIComponent(job.jobKeyDTO.name);
  assert.equal(path,JOB_PATH,'Returned identity differs from the fixed registered resource; no guessed or repaired identity is allowed.');
  assert.equal(typeof job.jobClassName,'string');assert.equal(typeof job.durable,'boolean');assert.equal(typeof job.requestsRecovery,'boolean');
  assert.ok(job.jobDataMap&&typeof job.jobDataMap==='object'&&!Array.isArray(job.jobDataMap),'Stored map is not an object');
  return {path,command:structuredClone({jobClass:job.jobClassName,description,durable:job.durable,requestsRecovery:job.requestsRecovery,jobDataMap:job.jobDataMap})};
}
export function expectedProducer(input){
  return {jobKeyDTO:{group:'RESEARCH',name:'pilot-job'},jobClassName:input.jobClass,
    description:input.description??null,durable:input.durable,requestsRecovery:input.requestsRecovery,
    jobDataMap:input.jobDataMap??{},triggerKeys:[]};
}
export function expectedForm(job){
  return {group:job.jobKeyDTO.group,name:job.jobKeyDTO.name,jobClass:job.jobClassName,description:job.description??'',
    durable:job.durable,requestsRecovery:job.requestsRecovery,jobDataMap:structuredClone(job.jobDataMap)};
}
export function decodeNativeEntries(entries){
  const result=Object.create(null);
  for(const row of entries){
    assert.ok(!Object.hasOwn(result,row.key),'Duplicate raw UI key; cannot silently collapse it');
    let value;
    switch(row.type){
      case 'null':value=null;break;
      case 'number':value=Number(row.value);assert.ok(Number.isFinite(value),'Non-finite native number');break;
      case 'boolean':assert.ok(['true','false'].includes(row.value));value=row.value==='true';break;
      case 'json':value=JSON.parse(row.value);break;
      case 'string':value=row.value;break;
      default:throw new Error('Unknown native map entry type: '+row.type);
    }
    result[row.key]=value; // Preserve literal keys; deliberately no trim or fallback.
  }
  return {...result};
}
export function allowedRequest(method,path){return ['GET','HEAD','OPTIONS'].includes(method)||(method==='POST'&&path==='/quartz-manager/auth/login')||(['POST','PUT'].includes(method)&&path===JOB_PATH);}
const principal=x=>({username:x?.username,authorities:x?.authorities});
const safeURL=value=>{const u=new URL(value);for(const k of [...u.searchParams.keys()])if(/token|password|secret/i.test(k))u.searchParams.set(k,'[REDACTED]');return u.href;};
const now=()=>performance.now();

export async function executeCase({registry,caseId,base='http://127.0.0.1:19965',output,playwrightModule='playwright',chromeExecutable,signal,onBrowserCheckpoint}){
  const parsed=new URL(base);assert.equal(parsed.protocol,'http:');assert.ok(['127.0.0.1','localhost','[::1]'].includes(parsed.hostname));assert.equal(parsed.pathname,'/');
  assert.ok(!parsed.username&&!parsed.password&&!parsed.search&&!parsed.hash);base=parsed.origin;
  const c=registry.cases.find(x=>x.case_id===caseId);assert.ok(c,'Case is absent from pinned registry');
  const [producer,consumer]=c.operations;assert.equal(producer.operation_id,'create_stored_job');assert.equal(consumer.operation_id,'edit_job_description');
  assert.equal(producer.input.durable,true);assert.equal(consumer.input.description,'Description after meaningful continuation.');
  if(producer.interface==='ui')assert.equal(c.intervention,'route_only','No UI mutation adapter is implemented');
  const unknown=registry.manifest.oracle.strata.transformation_ids.unresolved_key_policy.includes(c.mutation?.transformation_id);
  const started=now(),out=resolve(output);await mkdir(out,{recursive:true});
  const result={schema_version:1,kind:'quartz_generated_case',case_id:caseId,route:producer.interface+'-'+consumer.interface,
    intervention:c.intervention,mutation:c.mutation??null,expected_producer:c.expectation,policy_unresolved:unknown,
    started_at:new Date().toISOString(),status:'running',phase:'authentication',eligible:true,attempted:false,accepted_prefix:false,
    reached_continuation:false,completed:false,blocked:false,timed_out:false,defect_adjudication:'not_performed',
    registered_inputs:structuredClone(c.operations),trace:[],checks:[],ui_forms:[],actors:[],page_errors:[],blocked_requests:[],
    consumption_observations:[],phase_cost_ms:{},comparison_scope:registry.manifest.oracle.business_state_comparison};
  let token,server,browser,ctx,page,phaseStarted=started,writeQueue=Promise.resolve();const pending=new Set();
  function phase(name){result.phase_cost_ms[result.phase]=(result.phase_cost_ms[result.phase]??0)+now()-phaseStarted;result.phase=name;phaseStarted=now();}
  function event(data){result.trace.push({sequence:result.trace.length+1,elapsed_ms:Math.round(now()-started),phase:result.phase,...data});}
  function check(id,passed,detail,scope='requirement'){result.checks.push({id,passed:Boolean(passed),scope,detail});return Boolean(passed);}
  const checkpoint=()=>{writeQueue=writeQueue.then(async()=>{await writeFile(join(out,'result.json.partial'),JSON.stringify(result,null,2)+'\n');await rename(join(out,'result.json.partial'),join(out,'result.json'));});return writeQueue;};
  function active(){if(signal?.aborted)throw signal.reason??new Error('Interrupted');}
  async function request(method,path,body){
    active();assert.ok(path.startsWith('/quartz-manager/'));assert.ok(allowedRequest(method,path),'Unregistered mutation blocked');
    const headers={Accept:'application/json'};if(token)headers.Authorization=token;if(body!==undefined)headers['Content-Type']='application/json';
    const timeout=AbortSignal.timeout(15000),abort=new AbortController();const cancel=()=>abort.abort();
    signal?.addEventListener('abort',cancel,{once:true});timeout.addEventListener('abort',cancel,{once:true});
    let res,text;try{res=await fetch(base+path,{method,headers,body:body===undefined?undefined:JSON.stringify(body),redirect:'manual',signal:abort.signal});text=await res.text();}
    finally{signal?.removeEventListener('abort',cancel);timeout.removeEventListener('abort',cancel);}
    let data;try{data=JSON.parse(text);}catch{data={non_json_body:text.slice(0,16000)};}
    event({source:'direct_api',method,path,request:body??null,status:res.status,response:path.endsWith('/whoami')?principal(data):data});return {status:res.status,body:data};
  }
  async function read(path){const r=await request('GET',path);if(r.status!==200)throw Object.assign(new Error('Native read returned '+r.status+' for '+path),{observation_kind:'application_read_response',http_status:r.status});return r.body;}
  async function state(label){
    const s={scheduler:await read('/quartz-manager/scheduler'),jobs:await read('/quartz-manager/jobs'),triggers:await read('/quartz-manager/triggers')};
    result[label]=s;result[label+'_sha256']=digest(s);
    const inactive=s.scheduler.status==='STOPPED'&&s.scheduler.numberOfJobsExecuted===0&&s.scheduler.jobStoreSupportsPersistence===false&&s.scheduler.jobStoreClass?.includes('RAMJobStore')&&equal(s.scheduler.triggerKeys,[])&&equal(s.triggers,[]);
    check(label+'_inactive_scheduler',inactive,s.scheduler);assert.ok(inactive,'Scheduler/store safety prerequisite changed');return s;
  }
  async function closeContext(){if(ctx){const old=ctx;ctx=undefined;page=undefined;await old.close();}await Promise.allSettled([...pending]);}
  async function startBrowser(){
    if(browser)return;
    const {chromium}=createRequire(import.meta.url)(playwrightModule);
    const marker='--codex-study-case='+randomBytes(10).toString('hex');
    const ownership=async pid=>{await writeFile(join(out,'browser-pid.json.tmp'),JSON.stringify({pid,marker})+'\n');await rename(join(out,'browser-pid.json.tmp'),join(out,'browser-pid.json'));};
    await ownership(null);result.browser_marker=marker;await checkpoint();await onBrowserCheckpoint?.('before-browser');active();
    server=await chromium.launchServer({headless:true,host:'127.0.0.1',...(chromeExecutable?{executablePath:chromeExecutable}:{}),args:['--disable-background-networking',marker]});
    result.browser_pid=server.process().pid;await ownership(result.browser_pid);await checkpoint();await onBrowserCheckpoint?.('after-browser');active();
    browser=await chromium.connect(server.wsEndpoint());result.browser_version=browser.version();
  }
  async function openUI(){
    active();await closeContext();await startBrowser();ctx=await browser.newContext({viewport:{width:1440,height:1000},locale:'en-US',timezoneId:'UTC',serviceWorkers:'block'});
    await ctx.route('**/*',r=>{const q=r.request(),u=new URL(q.url());if(u.origin!==base||!allowedRequest(q.method(),u.pathname)){result.blocked_requests.push({method:q.method(),url:safeURL(q.url())});return r.abort('blockedbyclient');}return r.continue();});
    page=await ctx.newPage();page.setDefaultTimeout(15000);page.on('pageerror',e=>result.page_errors.push(String(e)));
    page.on('response',res=>{
      const q=res.request(),u=new URL(q.url());if(!u.pathname.startsWith('/quartz-manager/')||u.pathname.includes('/websocket'))return;
      const p=(async()=>{let data;try{data=await res.json();}catch{data=null;}let input=null;if(!u.pathname.includes('/auth/')&&q.postData()){try{input=q.postDataJSON();}catch{input={non_json_body:q.postData()?.slice(0,16000)};}}
        event({source:'ui_network',method:q.method(),path:u.pathname,url:safeURL(q.url()),request:input,status:res.status(),response:u.pathname.includes('/auth/')?(u.pathname.endsWith('/whoami')?principal(data):'[authentication response omitted]'):data});})();
      pending.add(p);p.finally(()=>pending.delete(p)).catch(()=>{});
    });
    await page.goto(base+'/quartz-manager-ui/index.html');await page.getByLabel('Username',{exact:true}).fill('admin');await page.getByLabel('Password',{exact:true}).fill('admin');
    const who=page.waitForResponse(r=>new URL(r.url()).pathname==='/quartz-manager/auth/whoami'&&r.status()===200);who.catch(()=>{});
    await page.locator('form').getByRole('button',{name:'Login',exact:true}).click();const identity=principal(await(await who).json());
    result.actors.push({interface:'ui',phase:result.phase,principal:identity});assert.ok(equal(identity,result.api_actor),'UI/API actor mismatch');
    await page.getByRole('button',{name:'Jobs',exact:true}).click();await page.getByRole('button',{name:'New Job',exact:true}).waitFor({state:'visible'});
  }
  const editor=()=>page.locator('aside[aria-label="Stored job editor"].drawer-open');
  async function form(label){
    const e=editor(),rows=[];for(let i=0;i<await e.locator('[name^="jobDataKey"]').count();i++)rows.push({key:await e.locator(`[name="jobDataKey${i}"]`).inputValue(),type:await e.locator(`[name="jobDataType${i}"]`).inputValue(),value:await e.locator(`[name="jobDataValue${i}"]`).inputValue()});
    const values={group:await e.locator('[name="jobGroup"]').inputValue(),name:await e.locator('[name="jobName"]').inputValue(),jobClass:await e.locator('[name="storedJobClass"]').inputValue(),description:await e.locator('[name="jobDescription"]').inputValue(),durable:await e.locator('[name="jobDurable"]').isChecked(),requestsRecovery:await e.locator('[name="jobRecovery"]').isChecked(),jobDataMap:decodeNativeEntries(rows)};
    result.ui_forms.push({label,values,typed_entries:rows,preview_text:await e.locator('pre.code-block').innerText()});return values;
  }
  async function openEdit(job){
    await page.getByRole('cell',{name:job.jobKeyDTO.group+'.'+job.jobKeyDTO.name,exact:true}).click();
    await page.locator('aside[aria-label="Job detail drawer"].drawer-open').getByRole('button',{name:'Edit Job',exact:true}).click();await editor().waitFor({state:'visible'});
  }
  async function submit(method,label,intended){
    let sent=false;const mark=q=>{if(new URL(q.url()).pathname===JOB_PATH&&q.method()===method)sent=true;};page.on('request',mark);
    const response=page.waitForResponse(r=>new URL(r.url()).pathname===JOB_PATH&&r.request().method()===method).then(async r=>({kind:'response',status:r.status(),body:await r.json().catch(()=>null),request:r.request().postDataJSON()}));response.catch(()=>{});
    const blocked=editor().locator('.warning-box').waitFor({state:'visible'}).then(async()=>({kind:'ui_block',message:await editor().locator('.warning-box').innerText()}));blocked.catch(()=>{});
    let responseOrBlock;try{await editor().getByRole('button',{name:label,exact:true}).click();responseOrBlock=await Promise.race([response,blocked]);if(responseOrBlock.kind==='ui_block'&&sent)responseOrBlock=await response;}finally{page?.off('request',mark);}
    if(responseOrBlock.kind==='response'){
      const exact=equal(responseOrBlock.request,intended);check('native_'+method+'_payload_matches_bound_intent',exact,{intended,actual:responseOrBlock.request},unknown&&method==='PUT'?'unresolved_policy':'requirement');
      if(responseOrBlock.status>=200&&responseOrBlock.status<300)await editor().waitFor({state:'hidden'});
    }
    return responseOrBlock;
  }
  const onAbort=()=>{result.timed_out=true;result.interruption=String(signal?.reason??'signal');server?.close().catch(()=>{});};signal?.addEventListener('abort',onAbort,{once:true});
  try{
    active();const login=await fetch(base+'/quartz-manager/auth/login',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded',Accept:'application/json'},body:'username=admin&password=admin',redirect:'manual',signal:AbortSignal.timeout(15000)});
    event({source:'direct_api',method:'POST',path:'/quartz-manager/auth/login',request:'[synthetic credentials omitted]',status:login.status,response:'[authentication response omitted]'});assert.equal(login.status,200);token=login.headers.get('authorization');assert.ok(token?.startsWith('Bearer '));
    result.api_actor=principal(await read('/quartz-manager/auth/whoami'));assert.equal(result.api_actor.username,'admin');assert.ok(result.api_actor.authorities?.some(x=>x.authority==='ROLE_ADMIN'));result.actors.push({interface:'api',principal:result.api_actor});
    phase('reset_verification');const initial=await state('initial_state');assert.deepEqual(initial.jobs,[],'Fresh empty RAM store required');await checkpoint();
    phase('producer');result.attempted=true;let produced;
    if(producer.interface==='api')produced={kind:'response',...await request('POST',JOB_PATH,producer.input),request:structuredClone(producer.input)};
    else{
      assert.deepEqual(producer.input.jobDataMap,{},'Only the registered empty-map UI controls are supported');await openUI();await page.getByRole('button',{name:'New Job',exact:true}).click();const e=editor();
      await e.locator('[name="jobName"]').fill('pilot-job');await e.locator('[name="jobGroup"]').fill('RESEARCH');await e.locator('[name="storedJobClass"]').selectOption(producer.input.jobClass);await e.locator('[name="jobDescription"]').fill(producer.input.description);
      await e.locator('[name="jobDurable"]').setChecked(producer.input.durable);await e.locator('[name="jobRecovery"]').setChecked(producer.input.requestsRecovery);
      check('native_create_form',equal(await form('producer_form'),expectedForm(expectedProducer(producer.input))),producer.input);produced=await submit('POST','Create Job',producer.input);
    }
    result.producer=produced;result.producer_response_class=produced.kind==='response'?Math.floor(produced.status/100)+'xx':produced.kind;result.accepted_prefix=produced.kind==='response'&&produced.status>=200&&produced.status<300;
    phase('producer_state');const afterProducer=await state('post_producer_state');await checkpoint();
    if(!result.accepted_prefix){
      result.blocked=produced.kind==='ui_block';check('rejected_prefix_left_empty_store',equal(afterProducer.jobs,[]),afterProducer.jobs);
      check('rejected_prefix_full_state_unchanged',equal(initial,afterProducer),{initial_hash:digest(initial),after_hash:digest(afterProducer)});
      check('producer_expectation',c.expectation.outcome!=='accept',{expected:c.expectation.outcome,actual:produced},c.expectation.outcome==='unknown'?'unresolved_policy':'requirement');
      result.continuation={attempted:false,reason:'producer_not_accepted'};result.final_state=afterProducer;result.completed=true;
    }else{
      check('producer_status',produced.status===201,{actual:produced.status,expected:201});
      if(c.expectation.outcome==='reject')check('producer_rejection_expectation',false,{expected:'reject',actual:'accepted'});
      const binding=bindConsumer(produced.body,consumer.input.description);result.bindings={source:'accepted producer response',...binding};
      const stored=await read(binding.path);result.stored_prefix=stored;
      const consistent=check('producer_response_matches_persisted_job',equal(business(stored),business(produced.body)),{response:business(produced.body),stored:business(stored)});
      if(!consistent)throw new Error('Producer response and stored job disagree; binding cannot be silently repaired from either version.');
      const expected=expectedProducer(producer.input),actual=business(stored);
      if(unknown){delete expected.jobDataMap;delete actual.jobDataMap;}
      check('producer_business_fields',equal(actual,expected),{expected,actual});check('single_stored_resource',afterProducer.jobs.length===1,afterProducer.jobs);
      phase('continuation');result.reached_continuation=true;let continued;
      if(consumer.interface==='api'){
        const loaded=await read(binding.path);const match=check('consumer_api_loaded_bound_state',equal(business(loaded),business(produced.body)),business(loaded));
        if(!match)throw new Error('Consumer loaded state differs from bound producer state.');
        result.consumption_observations.push({consumer_interface:'api',resource_identity:loaded.jobKeyDTO,fields_read:Object.keys(business(loaded)),source:'consumer GET before PUT'});
        continued={kind:'response',...await request('PUT',binding.path,binding.command),request:structuredClone(binding.command)};
      }else{
        await openUI();await openEdit(produced.body);const loaded=await form('consumer_loaded');
        const match=check('consumer_ui_loaded_bound_state',equal(loaded,expectedForm(produced.body)),{expected:expectedForm(produced.body),actual:loaded});
        if(!match){result.blocked=true;continued={kind:'representation_block',message:'Native form does not represent bound producer fields; no field repair performed.'};}
        else{
          result.consumption_observations.push({consumer_interface:'ui',resource_identity:produced.body.jobKeyDTO,fields_read:Object.keys(loaded),source:'fresh native edit form before change'});
          await editor().locator('[name="jobDescription"]').fill(binding.command.description);await form('consumer_before_submit');continued=await submit('PUT','Save Job',binding.command);
        }
      }
      result.continuation=continued;result.blocked||=continued.kind!=='response';
      if(result.blocked)check('continuation_submitted',false,continued,unknown?'unresolved_policy':'requirement');
      else check('continuation_status',continued.status===200,continued.status);
      phase('final_read');const final=await read(binding.path);result.final_job=final;
      const success=continued.kind==='response'&&continued.status>=200&&continued.status<300;
      const intended={...business(produced.body),description:success?binding.command.description:produced.body.description};
      const finalFields=business(final);if(unknown){delete intended.jobDataMap;delete finalFields.jobDataMap;check('raw_map_preservation_observation',equal(final.jobDataMap,produced.body.jobDataMap),{before:produced.body.jobDataMap,after:final.jobDataMap},'unresolved_policy');}
      check('final_business_state',equal(finalFields,intended),{expected:intended,actual:finalFields});
      if(success)check('update_response_matches_persisted',equal(business(continued.body),business(final)),{response:continued.body,persisted:final});
      await openUI();await openEdit(final);const fresh=await form('fresh_final_native_read');check('fresh_native_final_read',equal(fresh,expectedForm(final)),{actual:fresh,expected:expectedForm(final)});
      await page.screenshot({path:join(out,'final.png'),fullPage:true,animations:'disabled'});await editor().getByRole('button',{name:'Cancel',exact:true}).click();
      const end=await state('final_state');check('final_single_resource',end.jobs.length===1&&equal(business(end.jobs[0]),business(final)),end.jobs);result.completed=true;
    }
    check('no_unregistered_browser_request',result.blocked_requests.length===0,result.blocked_requests);result.status=unknown?'policy_unresolved':result.checks.some(x=>x.scope==='requirement'&&!x.passed)?'source_expectation_mismatch':!result.accepted_prefix&&produced.status>=500?'rejection_observed_server_error':'pass';
  }catch(error){
    result.status=signal?.aborted?'interrupted':error.observation_kind==='application_read_response'?'application_response_error':'adapter_or_environment_error';result.error={name:error.name,message:error.message,phase:result.phase,observation_kind:error.observation_kind,http_status:error.http_status};result.timed_out=Boolean(signal?.aborted);
    if(page)await page.screenshot({path:join(out,'failure.png'),fullPage:true,animations:'disabled',timeout:3000}).catch(()=>{});
  }finally{
    phase('teardown');await checkpoint();
    try{await closeContext();await browser?.close();await server?.close();}catch(error){result.cleanup_error=String(error);await server?.kill().catch(()=>{});}
    signal?.removeEventListener('abort',onAbort);result.phase_cost_ms.teardown=now()-phaseStarted;result.elapsed_ms=now()-started;result.ended_at=new Date().toISOString();await checkpoint();
  }
  return result;
}

async function main(){
  const {values:v}=parseArgs({options:{help:{type:'boolean'},registry:{type:'string'},'case-id':{type:'string'},output:{type:'string'},base:{type:'string'},'playwright-module':{type:'string'},'chrome-executable':{type:'string'},'validation-interrupt-at':{type:'string'}}});
  if(v.help){console.log('quartz_generated_case.mjs --registry FILE --case-id ID --output NEW_CASE_DIR [--base http://127.0.0.1:19965] [--playwright-module MODULE] [--chrome-executable BROWSER]\nRequires a fresh running native RAM-store backend. Use run_quartz_registry.mjs for reset and owned-process cleanup.');return;}
  for(const k of ['registry','case-id','output'])assert.ok(v[k],'Missing --'+k);
  if(v['validation-interrupt-at'])assert.ok(['before-browser','after-browser'].includes(v['validation-interrupt-at'])&&typeof process.send==='function','Validation pauses require an orchestrator IPC channel');
  const controller=new AbortController();for(const s of ['SIGTERM','SIGINT'])process.once(s,()=>controller.abort(new Error('Interrupted by '+s)));
  const registry=registryFromBytes(await readFile(v.registry));
  const r=await executeCase({registry,caseId:v['case-id'],base:v.base,output:v.output,playwrightModule:v['playwright-module'],chromeExecutable:v['chrome-executable'],signal:controller.signal,
    onBrowserCheckpoint:async stage=>{if(v['validation-interrupt-at']===stage){process.send({type:'validation_pause',stage});await new Promise(()=>{});}}});
  console.log(JSON.stringify({case_id:r.case_id,status:r.status,completed:r.completed}));if(!r.completed||r.status==='adapter_or_environment_error'||r.status==='interrupted'||(r.intervention==='route_only'&&r.status!=='pass'))process.exitCode=1;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(e=>{console.error(e.stack);process.exitCode=1;});
