import {configure,setField,put,setObserver} from '../redesign-zipline-input-controls-v2/actions.mjs';
import {frame} from '../redesign-zipline-inputs-v1/frame.mjs';
import assert from 'node:assert/strict';
import {createCapture} from '../redesign-harness-qualification-v1/capture.mjs';
import {spawn,execFileSync} from 'node:child_process';
import {snapshot,canonical,sha,compareFrame} from './state.mjs';
import {mkdirSync,readFileSync,writeFileSync,openSync,closeSync,cpSync,rmSync} from 'node:fs';
import {createRequire} from 'node:module';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const dir=path.dirname(fileURLToPath(import.meta.url));
const databaseUrl='postgresql://research@127.0.0.1:55432/zipline';
const input=JSON.parse(readFileSync(path.join(dir,'input.json')));
const base=process.env.ORDINARY_BASE,out=path.join(base,'evidence'),work=path.join(base,'work');
mkdirSync(work,{recursive:true});
writeFileSync(path.join(base,'redaction-values.json'),JSON.stringify([input.password,input.secret]),{mode:0o600});
const origin=`http://127.0.0.1:${input.port}`;
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
const save=(n,v)=>writeFileSync(path.join(out,n+'.json'),JSON.stringify(v,null,2)+'\n');
const pause=ms=>new Promise(r=>setTimeout(r,ms));
const controlObservations=[];setObserver(row=>{controlObservations.push(row);save('control-observations',controlObservations);});
const result={status:'in_progress',stage:'startup',scientific_workflows:1,producer_attempts:0,altered_inputs_executed:false,checks:{}};
let currentRecord;
let proc,browser,page,context,token,phase='startup',processNumber=0;const trace=[];
const capture=createCapture({bodyTimeoutMs:2000,flushTimeoutMs:2500,write:rows=>save('response-capture',rows)});
async function api(route,method='GET',body){const r=await fetch(origin+route,{method,headers:{Authorization:token,...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(10000)});const text=await r.text();trace.push({phase,channel:'api',route,method,body,status:r.status,response:text});assert(r.ok,text);return JSON.parse(text);}

const equal=(a,b)=>canonical(a)===canonical(b);
const runtime=path.join(base,'runtime'),pg=process.env.PG_BIN;
assert(pg,'PG_BIN required');
function command(name,args){return execFileSync(path.join(pg,name),args,{encoding:'utf8',timeout:30000,maxBuffer:16*1024*1024});}
async function state(label,url=databaseUrl){const value=await snapshot({runtime,databaseUrl:url,fileRoot:work});save(label,value);return value;}
function invariant(s){for(const name of ['public.File','public.Thumbnail','public.Invite'])assert.equal(s.tables[name]?.rows.length,0,name);assert(s.files.every(x=>x.type==='directory'),'nonempty file fixture');}
async function stop(){if(!proc||proc.exitCode!==null||proc.signalCode!==null)return;proc.kill('SIGTERM');for(let i=0;i<100&&proc.exitCode===null&&proc.signalCode===null;i++)await pause(100);if(proc.exitCode===null&&proc.signalCode===null){proc.kill('SIGKILL');throw new Error('application shutdown timeout');}}
async function idle(){const {Client}=createRequire(path.join(runtime,'package.json'))('pg');const c=new Client({connectionString:databaseUrl});await c.connect();try{const r=await c.query("SELECT count(*)::int AS n FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() AND state<>'idle'");assert.equal(r.rows[0].n,0,'other database activity');}finally{await c.end();}}
async function openEditor(){await page.goto(origin+'/dashboard/urls');const row=page.getByRole('row').filter({has:page.getByRole('link',{name:currentRecord.vanity??currentRecord.code,exact:true})});await row.waitFor();assert.equal(await row.count(),1);const button=row.getByRole('button').filter({has:page.locator('svg.tabler-icon-pencil')});assert.equal(await button.count(),1);assert(await button.isEnabled());await button.click();const editor=page.getByRole('dialog',{name:`Editing "${currentRecord.vanity??currentRecord.code}"`,exact:true});await editor.getByLabel('Destination',{exact:true}).waitFor();return editor;}
async function form(editor){return await editor.locator('input,textarea,select').evaluateAll(xs=>xs.map(x=>({tag:x.tagName,type:x.type,value:x.value,required:x.required,disabled:x.disabled,checked:x.checked??null})));}
async function storage(){const persistent=await context.storageState({indexedDB:true});persistent.cookies.sort((a,b)=>(a.domain+a.path+a.name).localeCompare(b.domain+b.path+b.name));persistent.origins.sort((a,b)=>a.origin.localeCompare(b.origin));for(const origin of persistent.origins)origin.localStorage.sort((a,b)=>a.name.localeCompare(b.name));return {persistent,session:await page.evaluate(()=>Object.fromEntries(Object.entries(sessionStorage)))};}
function normalizedPost(s,id,timestamp){const x=structuredClone(s),table=x.tables['public.Url'];table.rows.find(r=>r.id===id).updatedAt=timestamp;table.rows.sort((a,b)=>canonical(a).localeCompare(canonical(b),'en'));table.row_sha256=table.rows.map(r=>sha(canonical(r)));return x;}

async function start(){
 const env={PATH:process.env.PATH,LANG:'C.UTF-8',NODE_ENV:'production',ZIPLINE_ROOT:path.join(base,'runtime'),ZIPLINE_NO_COLOR:'true',CORE_HOSTNAME:'127.0.0.1',CORE_PORT:String(input.port),CORE_SECRET:input.secret,DATABASE_URL:databaseUrl,RATELIMIT_ENABLED:'false',DATASOURCE_TYPE:'local',DATASOURCE_LOCAL_DIRECTORY:path.join(work,'uploads'),CORE_TEMP_DIRECTORY:path.join(work,'tmp'),CORE_RETURN_HTTPS_URLS:'false',FEATURES_VERSION_CHECKING:'false',FEATURES_METRICS_ENABLED:'false',FEATURES_THUMBNAILS_ENABLED:'false',FEATURES_DELETE_ON_MAX_VIEWS:'false',TASKS_DELETE_INTERVAL:'0s',TASKS_CLEAR_INVITES_INTERVAL:'0s',TASKS_MAX_VIEWS_INTERVAL:'0s',TASKS_CLEAN_THUMBNAILS_INTERVAL:'0s'};
 save('environment',env);const fd=openSync(path.join(out,`application-${++processNumber}.log`),'w');proc=spawn('/bin/sh',[path.join(base,'entrypoint.sh')],{cwd:work,env,stdio:['ignore',fd,fd]});closeSync(fd);
 let ready=false;for(let i=0;i<120;i++){assert(proc.exitCode===null,'application exited '+proc.exitCode);try{const r=await fetch(origin+'/api/server/public',{signal:AbortSignal.timeout(1000)});if(r.ok){save('public-startup',await r.json());ready=true;break;}}catch{}await pause(500);}assert(ready,'startup timeout');
}
async function openPage(saved){context=await browser.newContext({locale:'en-US',...(saved?{storageState:saved.persistent}:{})});if(saved)await context.addInitScript(({origin,session})=>{if(location.origin===origin)for(const[k,v]of Object.entries(session))sessionStorage.setItem(k,v);},{origin,session:saved.session});page=await context.newPage();page.setDefaultTimeout(10000);
 page.on('request',r=>trace.push({phase,channel:'browser-request',method:r.method(),url:r.url(),body:r.postData()}));
 page.on('response',r=>{if(!r.url().includes('/api/'))return;const row={phase,channel:'browser-response',url:r.url(),status:r.status()};trace.push(row);capture.observe(row,()=>r.text());});
 page.on('pageerror',e=>trace.push({phase,channel:'pageerror',error:String(e)}));
}
try{
 assert.equal(process.version,'v24.11.1');await start();browser=await chromium.launch({headless:true,args:['--no-sandbox']});await openPage();
 phase=result.stage='native_setup';await page.goto(origin+'/auth/setup');await page.locator('input[name="username"]').fill(input.username);await page.locator('input[name="password"]').fill(input.password);await page.locator('input[name="confirmPassword"]').fill(input.password);await page.getByRole('button',{name:'Create account',exact:true}).click();await page.waitForURL(origin+'/dashboard');
 const browserActor=await (await context.request.get(origin+'/api/user')).json();save('browser-actor',browserActor);const tokenResponse=await context.request.get(origin+'/api/user/token');assert(tokenResponse.ok());const tokenBody=await tokenResponse.json();token=tokenBody.token;assert(token);writeFileSync(path.join(base,'redaction-values.json'),JSON.stringify([input.password,input.secret,token]),{mode:0o600});save('api-token-response',{issued:true});const apiActor=await api('/api/user');save('api-actor',apiActor);assert.equal(browserActor.user.id,apiActor.user.id);result.checks.same_actor=true;
 phase=result.stage='native_create';await page.goto(origin+'/dashboard/urls');await page.getByRole('button',{name:'Create',exact:true}).click();const create=page.getByRole('dialog',{name:'Shorten URL',exact:true});await create.getByLabel('URL',{exact:true}).fill(input.native.destination);await create.getByLabel('Vanity',{exact:true}).fill(input.native.vanity);await create.getByLabel('Discord link preview',{exact:true}).click();await page.getByRole('option',{name:'Custom Components V2',exact:true}).click();await configure(page,create,[['Container accent color',input.api.discordComponentEmbed.accentColor],['Markdown content',input.api.discordComponentEmbed.components[0].content]]);
 const [createdResponse]=await Promise.all([page.waitForResponse(r=>r.url()===origin+'/api/user/urls'&&r.request().method()==='POST'),create.getByRole('button',{name:'Create',exact:true}).click()]);assert(createdResponse.ok(),await createdResponse.text());save('native-create-request',createdResponse.request().postDataJSON());const native=await createdResponse.json();assert.equal(native.userId,browserActor.user.id);await page.getByRole('dialog',{name:'Shortened URL',exact:true}).waitFor();await page.keyboard.press('Escape');result.checks.native_create=true;
 phase=result.stage='root_checkpoint';await page.goto(origin+'/dashboard/urls');await page.getByRole('link',{name:input.native.vanity,exact:true}).waitFor();
 const rootState=await state('root-state');invariant(rootState);assert.equal(rootState.tables['public.Url'].rows.length,1);assert.equal(rootState.tables['public.Url'].rows[0].id,native.id);assert(equal(rootState.tables['public.Url'].rows[0].discordComponentEmbed,input.api.discordComponentEmbed));
 const producerResults=[],branchResults=[];
 function schema(rows,label){const source=path.join(base,label+'-schema-input.json'),output=path.join(out,label+'-schema.json');writeFileSync(source,JSON.stringify(rows));execFileSync(process.execPath,[path.join(dir,'schema.mjs'),runtime,source,output],{cwd:work,timeout:15000,maxBuffer:1024*1024,env:{PATH:process.env.PATH,LANG:'C.UTF-8',NODE_ENV:'production',DATABASE_URL:databaseUrl}});return JSON.parse(readFileSync(output));}
 const producerSchemas=schema(input.producers.map(p=>({name:p.id,method:'POST',httpPart:'body',value:p.body})),'producer');assert.equal(producerSchemas.rows.length,9);assert(equal(rootState,await state('root-after-schema')));
 async function checkpoint(label,expected,editor){
  await idle();await pause(1000);assert(equal(expected,await state(label+'-repeat')));const saved=await storage(),loaded=editor?await form(editor):null,actor=await api('/api/user');
  save(label+'-browser-identity',{sha256:sha(canonical(saved))});save(label+'-form',loaded);save(label+'-actor',actor);
  const dump=path.join(base,label+'.dump'),files=path.join(base,label+'-files');cpSync(work,files,{recursive:true});command('pg_dump',['--format=custom','--file',dump,databaseUrl]);assert(equal(expected,await state(label+'-after-backup')));
  command('createdb',['-h','127.0.0.1','-p','55432','-U','research','checkpoint_verify']);command('pg_restore',['--exit-on-error','--no-owner','-d','postgresql://research@127.0.0.1:55432/checkpoint_verify',dump]);assert(equal(expected,await state(label+'-backup-state','postgresql://research@127.0.0.1:55432/checkpoint_verify')));command('dropdb',['-h','127.0.0.1','-p','55432','-U','research','checkpoint_verify']);return {label,state:expected,saved,loaded,actor,dump,files};
 }
 async function verifyBrowser(cp,label,editor){const saved=await storage(),loaded=editor?await form(editor):null,actor=await api('/api/user');save(label+'-browser-identity',{sha256:sha(canonical(saved))});save(label+'-form',loaded);save(label+'-actor',actor);assert(equal(cp.saved,saved),'browser identity');assert(equal(cp.loaded,loaded),'loaded form');assert(equal(cp.actor,actor),'actor');assert(equal(cp.state,await state(label+'-state')),'logical starting state');}
 async function restore(cp,label,editorNeeded){
  await context.close();await stop();command('dropdb',['-h','127.0.0.1','-p','55432','-U','research','zipline']);command('createdb',['-h','127.0.0.1','-p','55432','-U','research','zipline']);command('pg_restore',['--exit-on-error','--no-owner','-d',databaseUrl,cp.dump]);rmSync(work,{recursive:true});cpSync(cp.files,work,{recursive:true});assert(equal(cp.state,await state(label+'-before-start')));await start();await openPage(cp.saved);let editor;if(editorNeeded)editor=await openEditor();else{await page.goto(origin+'/dashboard/urls');await page.getByRole('link',{name:input.native.vanity,exact:true}).waitFor();}await verifyBrowser(cp,label,editor);await idle();await pause(1000);assert(equal(cp.state,await state(label+'-repeat')));return editor;
 }
 const root=await checkpoint('root',rootState,null);
 function creationFrame(before,after,id){const x=structuredClone(after),t=x.tables['public.Url'];const ids=before.tables['public.Url'].rows.map(r=>r.id);if(t.rows.length!==ids.length+1||t.rows.filter(r=>r.id===id).length!==1)return false;t.rows=t.rows.filter(r=>r.id!==id);if(t.rows.some(r=>!ids.includes(r.id)))return false;t.rows.sort((a,b)=>ids.indexOf(a.id)-ids.indexOf(b.id));t.row_sha256=t.rows.map(r=>sha(canonical(r)));return equal(x,before);}
 async function responseRecord(route,method,body,label){const response=await fetch(origin+route,{method,headers:{Authorization:token,...(body!==undefined?{'Content-Type':'application/json'}:{})},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(10000)});const text=await response.text();let json=null,parsed=false;try{json=JSON.parse(text);parsed=true;}catch{}const value={route,method,body,status:response.status,text,json,parsed};save(label,value);return value;}
 async function perform(cp,label,targetField,repair,warm=false){
  phase=result.stage=label;let editor=warm?await openEditor():await restore(cp,label,true);if(warm)await verifyBrowser(cp,label,editor);
  const unrelated=input.fields.find(f=>f.pointer===targetField.unrelated_pointer);const changes={[unrelated.pointer]:unrelated.replacement,...(repair?{[targetField.pointer]:targetField.ordinary}:{})};const observation={label,target:targetField.pointer,repair,warm,changes,status:'in_progress'};branchResults.push(observation);save('branches',branchResults);
  async function actions(){if(repair)await setField(page,editor,targetField,targetField.ordinary);await setField(page,editor,unrelated,unrelated.replacement);}
  const mutations=[];await context.route('**/*',async route=>{const request=route.request();if(!['GET','HEAD','OPTIONS'].includes(request.method())){mutations.push({method:request.method(),path:new URL(request.url()).pathname,body:request.postDataJSON()});await route.abort('blockedbyclient');}else await route.continue();});
  try{await actions();const attempted=page.waitForEvent('requestfailed',{predicate:r=>r.url()===origin+'/api/user/urls/'+currentRecord.id&&r.method()==='PATCH',timeout:10000});const [,failed]=await Promise.all([editor.getByRole('button',{name:'Save changes',exact:true}).click(),attempted]);save(label+'-abort',{method:failed.method(),path:new URL(failed.url()).pathname,failure:failed.failure()});assert(failed.failure()?.errorText.includes('ERR_BLOCKED_BY_CLIENT'));assert.equal(mutations.length,1);save(label+'-preflight-request',mutations[0]);assert(equal(cp.state,await state(label+'-preflight-after')));}
  catch(e){observation.status='preflight_unavailable';observation.error=String(e);save(label+'-preflight-observed-requests',mutations);await state(label+'-preflight-failure-state');save('branches',branchResults);return observation;}
  schema([{name:label,method:'PATCH',httpPart:'body',value:mutations[0].body}],label);assert(equal(cp.state,await state(label+'-schema-after')));
  await context.close();await openPage(cp.saved);editor=await openEditor();await verifyBrowser(cp,label+'-reset',editor);
  try{await actions();save(label+'-edited-form',await form(editor));const awaited=page.waitForResponse(r=>r.url()===origin+'/api/user/urls/'+currentRecord.id&&r.request().method()==='PATCH',{timeout:10000});const [,response]=await Promise.all([editor.getByRole('button',{name:'Save changes',exact:true}).click(),awaited]);const request={method:response.request().method(),path:new URL(response.url()).pathname,body:response.request().postDataJSON()};const text=await response.text();save(label+'-request',request);save(label+'-response',{status:response.status(),text});await responseRecord('/api/user/urls','GET',undefined,label+'-api-after');const after=await state(label+'-after');const correct=frame(cp.state,after,currentRecord.id,changes);observation.preflight_request_agreement=equal(mutations[0],request);observation.http_status=response.status();observation.status=response.ok()?(correct?'intended_edit_persisted':'persistence_or_frame_mismatch'):(equal(cp.state,after)?'native_request_rejected':'write_after_rejection');observation.frame_valid=correct;}
  catch(e){observation.status='native_observation_unavailable';observation.error=String(e);await state(label+'-unavailable-state');}
  save('branches',branchResults);return observation;
 }
 for(const [index,producer] of input.producers.entries()){
  const label='p'+index;phase=result.stage=label;await restore(root,label+'-root',false);const before=await state(label+'-producer-before');assert(equal(before,rootState));
  result.producer_attempts++;if(index>0)result.altered_inputs_executed=true;save('result',result);
  const response=await responseRecord('/api/user/urls','POST',producer.body,label+'-producer-response');await responseRecord('/api/user/urls','GET',undefined,label+'-producer-api-readback');const after=await state(label+'-producer-after');
  const observation={id:producer.id,index,target:producer.target??null,operation:producer.operation??'ordinary',http_status:response.status,schema_accepted:producerSchemas.rows[index].accepted,status:'unclassified'};producerResults.push(observation);
  const responseId=response.parsed&&response.json?.id;const record=after.tables['public.Url'].rows.find(r=>r.id===responseId);
  if(response.status<200||response.status>=300){observation.status=equal(before,after)?'producer_rejected_unchanged':'producer_rejected_with_effects';save('producers',producerResults);assert(equal(before,after),'rejected producer changed state');continue;}
  if(!record||record.userId!==browserActor.user.id||!creationFrame(before,after,responseId)){observation.status='producer_response_persistence_or_frame_mismatch';save('producers',producerResults);throw new Error('producer admission/frame mismatch');}
  observation.status='accepted_persisted';observation.record_id=responseId;observation.persisted=record;save('producers',producerResults);currentRecord=record;
  let editor,cp;
  try{editor=await openEditor();assert(equal(after,await state(label+'-editor-state')));cp=await checkpoint(label,after,editor);}
  catch(e){observation.continuation='editor_or_checkpoint_unavailable';observation.error=String(e);await state(label+'-editor-failure-state');save('producers',producerResults);if(index===0)throw e;continue;}
  const targets=index===0?input.fields:[input.fields.find(f=>f.pointer===producer.target)];assert(targets.every(Boolean));
  if(index===0){const warm=await perform(cp,label+'-warm',targets[0],false,true);assert.equal(warm.status,'intended_edit_persisted');assert(warm.preflight_request_agreement);}
  for(const [fieldIndex,targetField] of targets.entries())for(const repair of [false,true]){
   const branchLabel=label+'-b'+fieldIndex+'-'+(repair?'repair':'sham');const outcome=await perform(cp,branchLabel,targetField,repair);
   if(index===0){assert.equal(outcome.status,'intended_edit_persisted','ordinary gate');assert(outcome.preflight_request_agreement);if(fieldIndex===0&&!repair){const warm=JSON.parse(readFileSync(path.join(out,label+'-warm-request.json'))),restored=JSON.parse(readFileSync(path.join(out,branchLabel+'-request.json')));assert(equal(warm,restored),'ordinary warm/restored request mismatch');}}
  }
  observation.continuation='fixed_schedule_observed';save('producers',producerResults);
 }
 assert.equal(result.producer_attempts,9);result.status='scientific_schedule_completed';result.stage='complete';
}catch(e){result.status='scientific_execution_incomplete';result.error=String(e);result.stack=e.stack;save('result',result);save('trace',trace);}
finally{save('result',result);save('trace',trace);if(page)page.removeAllListeners('response');try{await capture.close();}catch(e){result.status='scientific_execution_incomplete';result.capture_error=String(e);}if(browser)await browser.close().catch(()=>{});try{await stop();result.cleanup_complete=true;}catch(e){result.status='scientific_execution_incomplete';result.shutdown_error=String(e);}save('trace',trace);save('result',result);console.log(JSON.stringify(result));}
process.exitCode=result.status==='scientific_schedule_completed'?0:1;
