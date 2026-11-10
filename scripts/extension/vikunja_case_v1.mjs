/** Frozen finite observer: raw observations are retained before classification. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {parseArgs} from 'node:util';
import {performance} from 'node:perf_hooks';
import {installWriteObserver,collectWriteObserver} from './vikunja_fetch_observer_v1.mjs';
const {values:a}=parseArgs({options:{registry:{type:'string'},case:{type:'string'},channel:{type:'string'},out:{type:'string'}}});
const reg=JSON.parse(await readFile(a.registry,'utf8')),c=reg.cases.find(c=>c.id===a.case),spec=reg.workflows.find(w=>w.id===c?.workflow);assert.ok(spec&&['api','ui'].includes(a.channel));
const task=c.workflow==='task',project=c.workflow==='project',method=task?'PATCH':'PUT',base='http://127.0.0.1:18080',password=process.env.STUDY_EPHEMERAL_PASSWORD,secrets=[password];assert.ok(password);
const result={kind:'vikunja_finite_observation_v1',case_id:c.id,workflow:c.workflow,channel:a.channel,status:'incomplete',requests:[],forms:[],native_requests:[],timing:{}};await mkdir(a.out,{recursive:true});
const redact=s=>secrets.reduce((s,v)=>v?s.replaceAll(v,'[redacted]'):s,String(s));
const save=()=>writeFile(a.out+'/observation.json',redact(JSON.stringify(result,null,2))+'\n');
let token,browser,target,fixturePath;
async function api(method,path,body,status=200,privateCall=false){
 const start=performance.now(),r=await fetch(base+path,{method,headers:{'Content-Type':method==='PATCH'?'application/json-patch+json':'application/json',...(token?{Authorization:'Bearer '+token}:{})},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});
 const raw=await r.text();let value;try{value=JSON.parse(raw)}catch{value={unparsed:raw}}
 if(!privateCall){result.requests.push({method,path,body,status:r.status,response:value,elapsed_s:(performance.now()-start)/1000});await save()}
 else if(r.status!==status){result.bootstrap_failure={method,path,status:r.status,code:value.code,message:redact(value.message??value.detail??'')};await save()}
 if(status!==null)assert.equal(r.status,status,method+' '+path);return {status:r.status,value};
}
const get=async path=>(await api('GET',path)).value;
function business(v){const x=structuredClone(v);delete x.created;delete x.updated;if(x.subscription)delete x.subscription.created;for(const k of ['owner','created_by'])if(x[k]){delete x[k].created;delete x[k].updated}if(x.views)for(const v of x.views){delete v.created;delete v.updated}return x}
function collection(v){assert.ok(Array.isArray(v.items));return {...v,items:v.items.map(business)}}
async function readFinal(){if(target){result.final=await get(target);result.final_business=business(result.final)}if(fixturePath)result.fixture_final=await get(fixturePath);await save()}
try{
 const setupStart=performance.now();result.instance=await get('/api/v2/info');assert.equal(result.instance.version,reg.version);
 for(const username of ['study-bootstrap','study-actor'])await api('POST','/api/v2/register',{username,email:username+'@example.invalid',password,language:'en'},201,true);
 token=(await api('POST','/api/v2/login',{username:'study-actor',password},200,true)).value.token;assert.ok(token);secrets.push(token);
 const actor=await get('/api/v2/user');result.actor={id:actor.id,username:actor.username,is_admin:actor.is_admin};await save();assert.equal(actor.username,'study-actor');assert.equal(actor.is_admin,false);
 if(task){result.fixture_created=(await api('POST','/api/v2/projects',reg.project_fixture,201)).value;fixturePath='/api/v2/projects/'+result.fixture_created.id;result.fixture_initial=await get(fixturePath)}
 result.initial_raw=await get(spec.collection);result.initial_business_state=collection(result.initial_raw);result.timing.setup_s=(performance.now()-setupStart)/1000;
 let producer={...spec.payload,...(task?{project_id:result.fixture_created.id}:{})};if(c.cohort==='boundary'){if(c.mutation==='omitted')delete producer[c.field];else producer[c.field]=c.value}
 const createPath=task?fixturePath+'/tasks':spec.collection;result.producer_body=producer;const start=performance.now(),created=await api('POST',createPath,producer,null);result.producer_status=created.status;result.timing.producer_s=(performance.now()-start)/1000;
 if(created.status!==201){result.after_failed_producer=await get(spec.collection);if(fixturePath)result.fixture_final=await get(fixturePath);result.status='observed';await save()}
 else{
  assert.ok(Number.isInteger(created.value.id)&&created.value.id>0);target=spec.collection+'/'+created.value.id;result.prefix=await get(target);result.prefix_business=business(result.prefix);if(fixturePath){result.fixture_prefix=await get(fixturePath);result.fixture_business=business(result.fixture_prefix)}await save();assert.equal(result.prefix[spec.owner_field].id,actor.id);
  assert.ok(spec.fields.every(k=>Object.hasOwn(result.prefix,k)));const expected={...result.prefix,[task?'description':'title']:spec.edit_value};
  const body=task?spec.fields.map(k=>({op:'add',path:'/'+k,value:k==='reminders'?(expected[k]??[]):expected[k]})):Object.fromEntries(spec.fields.map(k=>[k,expected[k]]));
  if(a.channel==='api'){const start=performance.now();result.continuation_status=(await api(method,target,body,null)).status;await readFinal();result.timing.continuation_s=(performance.now()-start)/1000;result.status='observed'}
  else{
   const browserStart=performance.now();const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH);browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE});const context=await browser.newContext({locale:'en-US',timezoneId:'UTC'}),page=await context.newPage();page.setDefaultTimeout(20000);await installWriteObserver(page,target,method);
   await page.goto(base+'/login');await page.locator('#username').fill('study-actor');await page.locator('#password').fill(password);await Promise.all([page.waitForURL(u=>!u.pathname.startsWith('/login')),page.locator('#loginform').getByRole('button',{name:'Login',exact:true}).click()]);
   result.timing.browser_setup_s=(performance.now()-browserStart)/1000;const start=performance.now(),pending=[];page.on('response',r=>{const q=r.request();if(new URL(r.url()).pathname===target&&q.method()===method){const record={method:q.method(),path:target,body:q.postData(),content_type:q.headers()['content-type'],status:r.status()};result.native_requests.push(record);pending.push((async()=>{await save();record.response=await r.text();await save()})())}});
   async function open(){await page.goto(base+(task?'/tasks/'+result.prefix.id:spec.edit_path.replace('{id}',String(result.prefix.id))));if(c.workflow==='label')await page.locator('.label-edit-button').click();await page.locator(task?'h1.title.input':spec.title_selector).waitFor({state:'visible'});await page.locator(task?'.tiptap__task-description .tiptap__editor':'.tiptap__editor').waitFor({state:'visible'})}
   async function snapshot(label){const title=page.locator(task?'h1.title.input':spec.title_selector),editor=page.locator(task?'.tiptap__task-description .tiptap__editor':'.tiptap__editor');assert.equal(await title.count(),1);assert.equal(await editor.count(),1);const f={label,title:task?await title.innerText():await title.inputValue(),title_text_content:await title.textContent(),description_text:await editor.innerText(),description_html:await editor.innerHTML()};if(!task){const color=page.locator('input[type=color]');assert.equal(await color.count(),1);f.color=await color.inputValue();f.color_empty=await color.evaluate(e=>e.classList.contains('is-empty'));f.color_html=await color.evaluate(e=>e.parentElement.outerHTML);f.title_attributes=await title.evaluate(e=>({required:e.required,maxLength:e.maxLength,valid:e.checkValidity()}));if(project){f.identifier=await page.locator('#identifier').inputValue();f.identifier_attributes=await page.locator('#identifier').evaluate(e=>({type:e.type,maxLength:e.maxLength,required:e.required,valid:e.checkValidity()}))}}result.forms.push(f);await save();return f}
   await open();await snapshot('loaded');
   const response=page.waitForResponse(r=>new URL(r.url()).pathname===target&&r.request().method()===method);response.catch(()=>{});
   let button;
   if(task){const editor=page.locator('.tiptap__task-description');await editor.getByRole('button',{name:'Edit',exact:true}).click();const field=editor.locator('[contenteditable="true"]');assert.equal(await field.count(),1);await field.fill('Edited ordinary description');button=editor.getByRole('button',{name:'Save',exact:true})}
   else{await page.locator(spec.title_selector).fill(spec.edit_value);button=page.getByRole('button',{name:'Save',exact:true})}
   await snapshot('before_submit');result.save_control={count:await button.count(),disabled:await button.isDisabled()};await save();assert.equal(result.save_control.count,1);
   if(result.save_control.disabled){await button.click({force:true});await page.waitForTimeout(1500);result.no_request_window_ms=1500}
   else{await button.click();try{result.continuation_status=(await response).status()}catch(e){result.native_wait_error=redact(e.message)}}
   await Promise.all(pending);result.fetch_requests=await collectWriteObserver(page);await save();
   if(result.continuation_status===200){await open();await snapshot('fresh_final');await Promise.all(pending);result.fetch_requests.push(...await collectWriteObserver(page))}
   await readFinal();result.timing.continuation_s=(performance.now()-start)/1000;result.status=result.native_wait_error?'incomplete':'observed';
  }
 }
}catch(e){result.error={name:e.name,message:redact(e.message)};try{await readFinal()}catch(readError){result.final_read_error=redact(readError.message)}}
finally{if(browser)try{await browser.close();result.browser_cleanup_confirmed=true}catch(e){result.browser_cleanup_confirmed=false}else result.browser_cleanup_confirmed=true;await save()}
process.exitCode=result.status==='observed'?0:1;
