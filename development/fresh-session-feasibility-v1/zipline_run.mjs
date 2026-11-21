import {configure,setField,setObserver} from '../redesign-zipline-input-controls-v2/actions.mjs';
import assert from 'node:assert/strict';
import {randomBytes} from 'node:crypto';
import {createCapture} from '../redesign-harness-qualification-v1/capture.mjs';
import {spawn,execFileSync} from 'node:child_process';
import {snapshot,canonical} from '../redesign-zipline-scientific-v1/state.mjs';
import {mkdirSync,readFileSync,writeFileSync,openSync,closeSync,cpSync,rmSync} from 'node:fs';
import {createRequire} from 'node:module';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const dir=path.dirname(fileURLToPath(import.meta.url));
const databaseUrl='postgresql://research@127.0.0.1:55432/zipline';
const input={...JSON.parse(readFileSync(path.join(dir,'zipline-input.json'))),password:randomBytes(24).toString('base64url'),secret:randomBytes(48).toString('base64url')};
const base=process.env.ORDINARY_BASE,out=path.join(base,'evidence'),work=path.join(base,'work');
mkdirSync(work,{recursive:true});
writeFileSync(path.join(base,'redaction-values.json'),JSON.stringify([input.password,input.secret]),{mode:0o600});
const origin=`http://127.0.0.1:${input.port}`;
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
const save=(n,v)=>writeFileSync(path.join(out,n+'.json'),JSON.stringify(v,null,2)+'\n');
const pause=ms=>new Promise(r=>setTimeout(r,ms));
const controlObservations=[];setObserver(row=>{controlObservations.push(row);save('control-observations',controlObservations);});
const result={status:'in_progress',stage:'startup',development_only:true,scientific_cases:0,checks:{}};
const matrix=JSON.parse(readFileSync(path.join(dir,'../../manifests/fresh-session-ordinary-matrix-v1.json'))).systems.find(s=>s.id==='zipline');
const branches=[],controlCycles=[];let browserActor,contextInitial;const pendingRequests=new Set();
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

async function start(){
 const env={PATH:process.env.PATH,LANG:'C.UTF-8',NODE_ENV:'production',ZIPLINE_ROOT:path.join(base,'runtime'),ZIPLINE_NO_COLOR:'true',CORE_HOSTNAME:'127.0.0.1',CORE_PORT:String(input.port),CORE_SECRET:input.secret,DATABASE_URL:databaseUrl,RATELIMIT_ENABLED:'false',DATASOURCE_TYPE:'local',DATASOURCE_LOCAL_DIRECTORY:path.join(work,'uploads'),CORE_TEMP_DIRECTORY:path.join(work,'tmp'),CORE_RETURN_HTTPS_URLS:'false',FEATURES_VERSION_CHECKING:'false',FEATURES_METRICS_ENABLED:'false',FEATURES_THUMBNAILS_ENABLED:'false',FEATURES_DELETE_ON_MAX_VIEWS:'false',TASKS_DELETE_INTERVAL:'0s',TASKS_CLEAR_INVITES_INTERVAL:'0s',TASKS_MAX_VIEWS_INTERVAL:'0s',TASKS_CLEAN_THUMBNAILS_INTERVAL:'0s'};
 save('environment',env);const fd=openSync(path.join(out,`application-${++processNumber}.log`),'w');proc=spawn('/bin/sh',[path.join(base,'entrypoint.sh')],{cwd:work,env,stdio:['ignore',fd,fd]});closeSync(fd);
 let ready=false;for(let i=0;i<120;i++){assert(proc.exitCode===null,'application exited '+proc.exitCode);try{const r=await fetch(origin+'/api/server/public',{signal:AbortSignal.timeout(1000)});if(r.ok){save('public-startup',await r.json());ready=true;break;}}catch{}await pause(500);}assert(ready,'startup timeout');
}

async function openPage(){
 context=await browser.newContext({locale:'en-US'});contextInitial=await context.storageState({indexedDB:true});assert.deepEqual(contextInitial,{cookies:[],origins:[]});
 page=await context.newPage();page.setDefaultTimeout(10000);
 await context.route('**/*',async route=>{const u=new URL(route.request().url());assert.equal(u.origin,origin,'external browser request');await route.continue();});
 page.on('request',r=>{pendingRequests.add(r);trace.push({phase,channel:'browser-request',method:r.method(),url:r.url(),body:r.postData()});});
 page.on('requestfinished',r=>pendingRequests.delete(r));page.on('requestfailed',r=>{pendingRequests.delete(r);trace.push({phase,channel:'requestfailed',url:r.url(),error:r.failure()});});
 page.on('response',r=>{if(!r.url().includes('/api/'))return;const row={phase,channel:'browser-response',url:r.url(),status:r.status()};trace.push(row);capture.observe(row,()=>r.text());});
 page.on('pageerror',e=>trace.push({phase,channel:'pageerror',error:String(e)}));
}
async function settled(){const deadline=Date.now()+10000;while(pendingRequests.size){assert(Date.now()<deadline,'owned HTTP work incomplete');await pause(20);}await idle();}
const actorSummary=x=>({id:x.user.id,role:x.user.role});
async function login(label){
 await page.goto(origin+'/auth/login?local=true');
 await page.locator('input[autocomplete="username"]').fill(input.username);
 await page.locator('input[autocomplete="current-password"]').fill(input.password);
 const pending=page.waitForResponse(r=>r.url()===origin+'/api/auth/login'&&r.request().method()==='POST');
 await page.locator('form').filter({has:page.locator('input[autocomplete="username"]')}).locator('button[type="submit"]').click();
 const response=await pending;assert(response.ok(),await response.text());await page.waitForURL(origin+'/dashboard');
 const nativeActor=await (await context.request.get(origin+'/api/user')).json(),apiActor=await api('/api/user');
 assert.deepEqual(actorSummary(nativeActor),actorSummary(browserActor));assert.deepEqual(actorSummary(apiActor),actorSummary(browserActor));
 save(label+'-actors',{browser:actorSummary(nativeActor),api:actorSummary(apiActor)});
 return {browser_actor:actorSummary(nativeActor),api_actor:actorSummary(apiActor)};
}
async function checkpoint(){
 await settled();await context.close();context=null;await stop();const rootState=await state('root-state');
 const dump=path.join(base,'root.dump'),files=path.join(base,'root-files');command('pg_dump',['--format=custom','--file',dump,databaseUrl]);cpSync(work,files,{recursive:true});
 command('createdb',['-h','127.0.0.1','-p','55432','-U','research','checkpoint_verify']);
 try{command('pg_restore',['--exit-on-error','--no-owner','-d','postgresql://research@127.0.0.1:55432/checkpoint_verify',dump]);assert(equal(rootState,await state('root-backup-verified','postgresql://research@127.0.0.1:55432/checkpoint_verify')));}
 finally{command('dropdb',['-h','127.0.0.1','-p','55432','-U','research','checkpoint_verify']);}
 return {state:rootState,dump,files};
}
async function restore(root,label){
 if(context){await settled();await context.close();context=null;}await stop();currentRecord=root.state.tables['public.Url'].rows.find(r=>r.id===result.record_id);assert(currentRecord);
 command('dropdb',['-h','127.0.0.1','-p','55432','-U','research','zipline']);command('createdb',['-h','127.0.0.1','-p','55432','-U','research','zipline']);command('pg_restore',['--exit-on-error','--no-owner','-d',databaseUrl,root.dump]);
 rmSync(work,{recursive:true});cpSync(root.files,work,{recursive:true});assert(equal(root.state,await state(label+'-restored')));
 await start();await openPage();phase=label+'-login';const actors=await login(label);const editor=await openEditor();await settled();await state(label+'-loaded');save(label+'-form',await form(editor));
 return {editor,actors};
}
async function saveEdit(editor,label,changes){
 phase=label;const traceStart=trace.length;
 for(const [pointer,value] of Object.entries(changes))await setField(page,editor,input.fields.find(f=>f.pointer===pointer),value);
 save(label+'-form-edited',await form(editor));save(label+'-actions',Object.entries(changes).map(([pointer,value])=>({pointer,value})));
 const pending=page.waitForResponse(r=>r.url()===origin+'/api/user/urls/'+currentRecord.id&&r.request().method()==='PATCH');
 await editor.getByRole('button',{name:'Save changes',exact:true}).click();const response=await pending;
 const request={method:response.request().method(),path:new URL(response.url()).pathname,body:response.request().postDataJSON()};
 const responseText=await response.text();save(label+'-request',request);save(label+'-response',{status:response.status(),text:responseText});
 assert(response.ok(),responseText);await editor.waitFor({state:'hidden'});await settled();const after=await state(label+'-after');currentRecord=after.tables['public.Url'].rows.find(r=>r.id===currentRecord.id);assert(currentRecord);
 const writes=trace.slice(traceStart).filter(r=>r.channel==='browser-request'&&!['GET','HEAD','OPTIONS'].includes(r.method)).map(r=>({method:r.method,path:new URL(r.url).pathname,body:JSON.parse(r.body)}));
 save(label+'-writes',writes);assert.deepEqual(writes,[request]);
 save(label+'-api-readback',await api('/api/user/urls')); // Independent database observation remains decisive.
 return request;
}
try{
 assert.equal(process.version,'v24.11.1');await start();browser=await chromium.launch({headless:true,args:['--no-sandbox']});await openPage();
 phase=result.stage='native_setup';await page.goto(origin+'/auth/setup');await page.locator('input[name="username"]').fill(input.username);await page.locator('input[name="password"]').fill(input.password);await page.locator('input[name="confirmPassword"]').fill(input.password);await page.getByRole('button',{name:'Create account',exact:true}).click();await page.waitForURL(origin+'/dashboard');
 browserActor=await (await context.request.get(origin+'/api/user')).json();save('browser-actor',browserActor);const tokenResponse=await context.request.get(origin+'/api/user/token');assert(tokenResponse.ok());const tokenBody=await tokenResponse.json();token=tokenBody.token;assert(token);writeFileSync(path.join(base,'redaction-values.json'),JSON.stringify([input.password,input.secret,token]),{mode:0o600});save('api-token-response',{issued:true});const apiActor=await api('/api/user');save('api-actor',apiActor);assert.equal(browserActor.user.id,apiActor.user.id);result.checks.same_actor=true;
 await state('native-before');
 phase=result.stage='native_create';await page.goto(origin+'/dashboard/urls');await page.getByRole('button',{name:'Create',exact:true}).click();const create=page.getByRole('dialog',{name:'Shorten URL',exact:true});await create.getByLabel('URL',{exact:true}).fill(input.native.destination);await create.getByLabel('Vanity',{exact:true}).fill(input.native.vanity);await create.getByLabel('Discord link preview',{exact:true}).click();await page.getByRole('option',{name:'Custom Components V2',exact:true}).click();await configure(page,create,[['Container accent color',input.api.discordComponentEmbed.accentColor],['Markdown content',input.api.discordComponentEmbed.components[0].content]]);
 const [createdResponse]=await Promise.all([page.waitForResponse(r=>r.url()===origin+'/api/user/urls'&&r.request().method()==='POST'),create.getByRole('button',{name:'Create',exact:true}).click()]);assert(createdResponse.ok(),await createdResponse.text());save('native-create-request',createdResponse.request().postDataJSON());const native=await createdResponse.json();assert.equal(native.userId,browserActor.user.id);await page.getByRole('dialog',{name:'Shortened URL',exact:true}).waitFor();await page.keyboard.press('Escape');result.checks.native_create=true;save('native-create-response',{status:createdResponse.status(),record:native});await state('native-after');

 phase=result.stage='api_create';await state('api-before');
 currentRecord=await api('/api/user/urls','POST',input.api);assert.equal(currentRecord.userId,browserActor.user.id);save('api-create-response',currentRecord);await state('api-after');
 result.record_id=currentRecord.id;result.actor_id=browserActor.user.id;result.actor_role=browserActor.user.role;
 const root=await checkpoint();invariant(root.state);assert.equal(root.state.tables['public.Url'].rows.length,2);
 // Every selected field is first replaced with its valid alternative and then reset through original controls.
 for(const [i,field] of input.fields.entries()){
  const label='cycle-'+i;phase=result.stage=label;let {editor,actors}=await restore(root,label);
  await state(label+'-before');await saveEdit(editor,label+'-replace',{[field.pointer]:field.replacement});
  editor=await openEditor();await state(label+'-reset-before');await saveEdit(editor,label+'-reset',{[field.pointer]:field.ordinary});
  controlCycles.push({label,field:field.pointer,...actors,context_initial:contextInitial});save('control-cycles',controlCycles);
 }
 for(const branch of matrix.branches){
  const label=branch.id;phase=result.stage=label;const {editor,actors}=await restore(root,label);
  const other=input.fields.find(f=>f.pointer===branch.unrelated),target=input.fields.find(f=>f.pointer===branch.target);
  const changes={...(branch.arm==='noop_repair'?{[target.pointer]:target.ordinary}:{}),[other.pointer]:other.replacement};
  await saveEdit(editor,label,changes);
  branches.push({id:label,...actors,context_initial:contextInitial});save('branches',branches);
 }
 assert.equal(branches.length,24);assert.equal(controlCycles.length,4);result.status='controls_completed';result.stage='complete';
}catch(e){result.status='controls_incomplete';result.error=String(e);result.stack=e.stack;}
finally{
 try{if(browser)await browser.close();}catch(e){result.status='controls_incomplete';result.browser_cleanup_error=String(e);}
 try{await capture.close();}catch(e){result.status='controls_incomplete';result.capture_error=String(e);}
 try{await stop();result.cleanup_complete=true;}catch(e){result.status='controls_incomplete';result.shutdown_error=String(e);}
 save('result',result);save('trace',trace);console.log(JSON.stringify({status:result.status,stage:result.stage,error:result.error}));
}
process.exitCode=result.status==='controls_completed'?0:1;
