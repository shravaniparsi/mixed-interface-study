import assert from 'node:assert/strict';
import {spawn,spawnSync} from 'node:child_process';
import {mkdirSync,readFileSync,writeFileSync,openSync,closeSync} from 'node:fs';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {framePreserved,decodedConfig,postComparable} from './frame.mjs';
const dir=path.dirname(fileURLToPath(import.meta.url));
const input=JSON.parse(readFileSync(path.join(dir,'input.json')));
const base=process.env.ORDINARY_BASE;assert(base);
const work=path.join(base,'work'),checkpoint=path.join(base,'checkpoint'),out=path.join(base,'evidence');
mkdirSync(path.join(work,'data'),{recursive:true});mkdirSync(out,{recursive:true});
writeFileSync(path.join(work,'config.yaml'),'server:\n  pid_file: ""\n');
const binary=path.join(base,'executable/bin/gomodel');
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
const origin=`http://127.0.0.1:${input.port}`;
const canonical=x=>JSON.stringify(x,(_,v)=>v && typeof v==='object' && !Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
const equal=(a,b)=>canonical(a)===canonical(b);
const save=(name,x)=>writeFileSync(path.join(out,name+'.json'),JSON.stringify(x,null,2)+'\n');
const result={status:'in_progress',stage:'startup',scientific_cases:0,altered_inputs_executed:false,checks:{},branches:[]};
const traces=[];let epoch='startup',proc,browser,context,page,processNumber=0;const pending=[];
const pause=ms=>new Promise(r=>setTimeout(r,ms));
function state(mode,extra){const args=[path.join(dir,'state.py'),mode,work];if(extra)args.push(extra);const p=spawnSync('python3',args,{encoding:'utf8',timeout:10000,maxBuffer:32*1024*1024});assert.equal(p.status,0,p.stderr);return mode==='capture'?JSON.parse(p.stdout):null;}
async function api(route,method='GET',body){
 const req={epoch,channel:'api',method,path:route,body:body??null,actor:input.actor_key};traces.push(req);
 const res=await fetch(origin+route,{method,headers:{Authorization:'Bearer '+input.actor_key,...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(10000)});
 req.status=res.status;req.response=await res.text();assert(res.ok,req.response);return req.response?JSON.parse(req.response):null;
}
async function start(){
 const log=openSync(path.join(out,`application-${++processNumber}.log`),'w');
 const env={PATH:process.env.PATH,LANG:'C.UTF-8',PORT:String(input.port),GOMODEL_MASTER_KEY:input.actor_key,GOMODEL_OFFLINE:'true',GOMODEL_VERSION_CHECK_ENABLED:'false',DASHBOARD_LIVE_LOGS_ENABLED:'false',LOGGING_ENABLED:'false',USAGE_ENABLED:'false',BUDGETS_ENABLED:'false',PLUGINS_ENABLED:'true',GUARDRAILS_ENABLED:'true',ADMIN_ENDPOINTS_ENABLED:'true',ADMIN_UI_ENABLED:'true',STORAGE_TYPE:'sqlite',SQLITE_PATH:path.join(work,'data/gomodel.db'),XDG_DATA_HOME:path.join(work,'xdg-data'),XDG_CACHE_HOME:path.join(work,'xdg-cache'),XDG_CONFIG_HOME:path.join(work,'xdg-config')};
 proc=spawn(binary,[],{cwd:work,env,stdio:['ignore',log,log]});closeSync(log);
 const errors=[];for(let i=0;i<60;i++){assert(proc.exitCode===null,'application exited '+proc.exitCode);try{const r=await fetch(origin+'/admin/access',{headers:{Authorization:'Bearer '+input.actor_key},signal:AbortSignal.timeout(1000)});if(r.ok){save(`startup-${processNumber}`,{pid:proc.pid,env,access:await r.json()});return;}}catch(e){errors.push(String(e));}await pause(500);}
 throw new Error('startup unavailable: '+errors.slice(-2).join('; '));
}
async function stop(){if(!proc||proc.exitCode!==null||proc.signalCode!==null)return;proc.kill('SIGTERM');for(let i=0;i<100&&proc.exitCode===null&&proc.signalCode===null;i++)await pause(100);if(proc.exitCode===null&&proc.signalCode===null){proc.kill('SIGKILL');throw new Error('graceful shutdown exceeded ten seconds');}}
async function newPage(storage,session){
 context=await browser.newContext({locale:'en-US',...(storage?{storageState:storage}:{})});
 if(session)await context.addInitScript(({origin,session})=>{if(location.origin===origin)for(const [k,v]of Object.entries(session))sessionStorage.setItem(k,v);},{origin,session});
 page=await context.newPage();page.setDefaultTimeout(10000);
 page.on('request',r=>{traces.push({epoch,channel:'browser-request',method:r.method(),url:r.url(),headers:r.headers(),body:r.postData()});});
 page.on('response',r=>{if(!r.url().includes('/admin/')||r.url().includes('/admin/static/'))return;const item={epoch,channel:'browser-response',url:r.url(),status:r.status()};traces.push(item);pending.push(r.text().then(t=>{item.body=t;}).catch(e=>{item.body_error=String(e);}));});
 page.on('pageerror',e=>traces.push({epoch,channel:'page-error',error:String(e)}));
 await page.goto(origin+'/admin/dashboard/guardrails',{waitUntil:'domcontentloaded'});
 if(!storage){await page.locator('#authDialogApiKey').fill(input.actor_key);await page.locator('.auth-dialog-submit-btn').click();}
 await page.getByRole('button',{name:'Create Guardrail',exact:true}).waitFor({state:'visible'});
}
function payload(name){return {name,type:input.type,description:input.description,user_path:input.user_path,config:input.config};}
async function submit(){
 const [response]=await Promise.all([page.waitForResponse(r=>r.url()===origin+'/admin/guardrails'&&r.request().method()==='PUT',{timeout:10000}),page.getByRole('button',{name:'Save Guardrail',exact:true}).click()]);
 assert(response.ok(),await response.text());await page.locator('#guardrail-name').waitFor({state:'hidden'});
 const request=response.request();return {method:request.method(),path:new URL(request.url()).pathname,body:request.postDataJSON(),actor:request.headers().authorization};
}
async function openEdit(){await page.getByRole('button',{name:'Edit Guardrail '+input.api_name,exact:true}).click();await page.locator('#guardrail-field-request_set').waitFor({state:'visible'});}
async function form(){return await page.locator('[aria-label="Guardrail editor"]').evaluate(el=>Array.from(el.querySelectorAll('input,textarea,select')).map(x=>({id:x.id,type:x.type,value:x.value,disabled:x.disabled,required:x.required,checked:x.checked??null})));}
async function storage(){return {persistent:await context.storageState({indexedDB:true}),session:await page.evaluate(()=>Object.fromEntries(Object.entries(sessionStorage)))};}
function record(snapshot,name){const t=snapshot.tables.guardrail_definitions;assert(t);const row=t.rows.find(r=>r[t.columns.indexOf('name')]===name);assert(row,'missing independent DB row');const obj=Object.fromEntries(t.columns.map((k,i)=>[k,row[i]]));obj.config=decodedConfig(obj.config);return obj;}
function checkRecord(snapshot,name,edited=false){const row=record(snapshot,name);assert.equal(row.type,input.type);assert.equal(row.description,input.description);assert.equal(row.user_path,input.user_path);assert(equal(row.config,{...input.config,...(edited?{[input.edit_property]:input.edit_value}:{})}));return row;}
async function branch(label){
 epoch=label;result.stage=label;const before=state('capture');save(label+'-before',before);const formBefore=await form();save(label+'-form-before',formBefore);
 await page.locator('#guardrail-field-'+input.edit_property).fill(input.edit_value);const request=await submit();
 const apiRows=await api('/admin/guardrails');const after=state('capture');save(label+'-after',after);save(label+'-api-after',apiRows);checkRecord(after,input.api_name,true);assert(equal(apiRows.find(x=>x.name===input.api_name).config,{...input.config,[input.edit_property]:input.edit_value}));
 result.checks[label+'_frame_preserved']=framePreserved(before,after,input.api_name,input.edit_property,input.edit_value);
 const row={label,request,intended_edit:true};result.branches.push(row);return {before,after,request,formBefore};
}
try{
 await start();browser=await chromium.launch({headless:true,args:['--no-sandbox']});await newPage();
 result.stage='native_create';epoch='native_create';await page.getByRole('button',{name:'Create Guardrail',exact:true}).click();await page.locator('#guardrail-type').selectOption(input.type);await page.locator('#guardrail-name').fill(input.native_name);await page.locator('#guardrail-description').fill(input.description);await page.locator('#guardrail-user-path').fill(input.user_path);for(const[k,v]of Object.entries(input.config))await page.locator('#guardrail-field-'+k).fill(v);const nativeRequest=await submit();save('native-create-request',nativeRequest);checkRecord(state('capture'),input.native_name);result.checks.native_create=true;
 result.stage='api_create';epoch='api_create';const created=await api('/admin/guardrails','PUT',payload(input.api_name));assert.equal(created.name,input.api_name);checkRecord(state('capture'),input.api_name);result.checks.api_create=true;
 result.stage='maintenance_calibration';epoch='maintenance_calibration';
 const preMaintenance=state('capture');save('maintenance-before',preMaintenance);
 assert(!Object.hasOwn(preMaintenance.files,'data/gomodel.pid'),'PID file must be absent');
 await context.close();await stop();await start();await newPage();
 const postMaintenance=state('capture');save('maintenance-after',postMaintenance);
 const comparable=x=>({...x,tables:Object.fromEntries(Object.entries(x.tables).filter(([k])=>!['sqlite_stat1','sqlite_stat4'].includes(k)))});
 result.checks.maintenance_non_statistics_unchanged=equal(comparable(preMaintenance),comparable(postMaintenance));
 assert(result.checks.maintenance_non_statistics_unchanged,'startup maintenance changed non-statistics state');
 assert(!Object.hasOwn(postMaintenance.files,'data/gomodel.pid'),'PID file must remain absent');
 await openEdit();epoch='checkpoint';result.stage='checkpoint';const access=await api('/admin/access');const before=state('capture');await pause(1000);assert(equal(before,state('capture')),'ordinary pre-state is not quiescent');const savedStorage=await storage(),savedForm=await form();save('checkpoint-browser',savedStorage);save('checkpoint-form',savedForm);save('checkpoint-access',access);save('checkpoint-state',before);state('checkpoint',checkpoint);
 const cp=spawnSync('python3',[path.join(dir,'state.py'),'capture',checkpoint],{encoding:'utf8',timeout:10000,maxBuffer:32*1024*1024});assert.equal(cp.status,0,cp.stderr);assert(equal(before,JSON.parse(cp.stdout)),'backup state differs');result.checks.checkpoint_backup=true;
 const warm=await branch('warm');assert(equal(warm.before,before));await context.close();await stop();state('restore',checkpoint);epoch='restored_start';result.stage='restored_start';await start();await newPage(savedStorage.persistent,savedStorage.session);await openEdit();const restoredBefore=state('capture');save('restored-precheck-state',restoredBefore);const restoredAccess=await api('/admin/access'),restoredStorage=await storage(),restoredForm=await form();save('restored-precheck-browser',restoredStorage);save('restored-precheck-form',restoredForm);save('restored-precheck-access',restoredAccess);
 result.checks.restored_start_state=equal(before,restoredBefore);result.checks.restored_actor=equal(access,restoredAccess);result.checks.restored_browser=equal(savedStorage,restoredStorage);result.checks.restored_form=equal(savedForm,restoredForm);assert(Object.entries(result.checks).filter(([k])=>k.startsWith('restored_')).every(([,v])=>v),'restored start equivalence failed; no restored write allowed');
 const restored=await branch('restored');result.checks.requests_equal=equal(warm.request,restored.request);result.checks.post_state_equal_with_target_timestamp_exception=equal(postComparable(warm.after,input.api_name),postComparable(restored.after,input.api_name));
 result.status=Object.values(result.checks).every(Boolean)?'ordinary_lifecycle_checks_passed':'ordinary_observed_equivalence_unresolved';result.stage='complete';
}catch(e){result.status='qualification_unavailable';result.error=String(e);result.stack=e.stack;if(page)try{await page.screenshot({path:path.join(out,'failure.png'),fullPage:true});writeFileSync(path.join(out,'failure.html'),await page.content());}catch{}}
finally{await Promise.allSettled(pending);if(browser)await browser.close().catch(()=>{});try{await stop();}catch(e){result.shutdown_error=String(e);result.status='qualification_unavailable';}save('trace',traces);save('result',result);console.log(JSON.stringify(result));}
process.exitCode=result.status==='ordinary_lifecycle_checks_passed'?0:1;
