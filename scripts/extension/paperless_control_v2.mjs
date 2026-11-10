/** Ordinary Paperless API/native qualification, with full-object API update. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {parseArgs} from 'node:util';
import {performance} from 'node:perf_hooks';
const {values:a}=parseArgs({options:{registry:{type:'string'},workflow:{type:'string'},channel:{type:'string'},out:{type:'string'}}});
const registry=JSON.parse(await readFile(a.registry,'utf8')),w=registry.workflows.find(w=>w.id===a.workflow),auth=JSON.parse(process.env.STUDY_EPHEMERAL_AUTH);assert.ok(w&&['api','ui'].includes(a.channel));assert.equal(auth.version,registry.version);
const payload={...w.payload,owner:auth.user_id},base='http://127.0.0.1:18080';await mkdir(a.out,{recursive:true});const result={kind:'paperless_ordinary_control_v1',workflow:w.id,channel:a.channel,status:'incomplete',requests:[],forms:[],timing:{}};
const redact=s=>String(s).replaceAll(auth.password,'[redacted]').replaceAll(auth.token,'[redacted]');const save=()=>writeFile(a.out+'/observation.json',redact(JSON.stringify(result,null,2))+'\n');const business=x=>Object.fromEntries(w.fields.map(k=>{assert.ok(Object.hasOwn(x,k),'Missing persisted field '+k);return[k,x[k]]}));
async function api(method,path,body){const t=performance.now(),response=await fetch(base+path,{method,headers:{Authorization:'Token '+auth.token,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});const raw=await response.text();let value;try{value=JSON.parse(raw)}catch{value={unparsed:raw}}result.requests.push({channel:'api',method,path,body,status:response.status,response:value,elapsed_s:(performance.now()-t)/1000});await save();return{status:response.status,value};}
let browser;
try{
 const initial=await api('GET',w.collection);assert.equal(initial.status,200);assert.equal(initial.value.count,0);result.initial_business_state={actor:auth.username,actor_id:auth.user_id,resource_count:0,version:auth.version};
 const made=await api('POST',w.collection,payload);assert.equal(made.status,201);assert.ok(Number.isInteger(made.value.id));const path=w.collection+made.value.id+'/';const before=await api('GET',path);assert.equal(before.status,200);assert.deepEqual(business(before.value),payload);result.prefix=business(before.value);result.resource_id=made.value.id;const expected={...payload,[w.edit_field]:w.edit_value};
 if(a.channel==='api'){
  const t=performance.now(),updated=await api('PUT',path,expected);assert.equal(updated.status,200);const after=await api('GET',path);assert.equal(after.status,200);assert.deepEqual(business(after.value),expected);result.final=business(after.value);result.timing.continuation_s=(performance.now()-t)/1000;
 }else{
  const t=performance.now(),require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH);browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE,args:['--no-sandbox']});const context=await browser.newContext({locale:'en-US',timezoneId:'UTC'});await context.route('**/*',route=>new URL(route.request().url()).origin===base?route.continue():route.abort());const page=await context.newPage();page.setDefaultTimeout(20000);
  await page.goto(base+'/accounts/login/');await page.locator('input[name="login"]').fill(auth.username);await page.locator('input[name="password"]').fill(auth.password);await Promise.all([page.waitForURL(url=>!url.pathname.startsWith('/accounts/')),page.locator('button[type="submit"]').click()]);result.timing.native_auth_setup_s=(performance.now()-t)/1000;
  const open=async()=>{await page.goto(base+w.list_path);await page.locator('table tbody .name-cell button').filter({hasText:payload.name}).click();await page.locator('.modal-content').waitFor({state:'visible'});await page.waitForFunction(()=>{const button=document.querySelector('.modal-content button[aria-label="Close"]');return button&&!button.disabled});};
  const snapshot=async(label,values)=>{
   const dialog=page.locator('.modal-content'),fields=[];
   for(const f of w.native_fields){const loc=dialog.locator(f.selector),count=await loc.count();if(count!==1){fields.push({name:f.field,count,selector:f.selector,kind:f.kind});continue}const observed=f.kind==='label'?(await loc.innerText()).trim():f.kind==='checkbox'?await loc.isChecked():await loc.inputValue();const expectedValue=f.kind==='label'?registry.algorithm_labels[String(values[f.field])]:values[f.field];fields.push({name:f.field,count,value:observed,expected:expectedValue,selector:f.selector,kind:f.kind,attributes:await loc.evaluate(e=>({required:e.required??null,maxlength:e.getAttribute('maxlength'),pattern:e.getAttribute('pattern')}))});}
   result.forms.push({label,fields});await page.screenshot({path:a.out+'/'+label+'.png',fullPage:true});await save();for(const field of fields){assert.equal(field.count,1,'Ambiguous native binding '+field.name);assert.deepEqual(field.value,field.expected,'Native field differs: '+field.name)}
  };
  const nativeStart=performance.now();await open();await snapshot('loaded',payload);await page.locator('.modal-content '+w.edit_selector).fill(w.edit_value);await page.locator('.modal-content '+w.edit_selector).blur();await snapshot('before_submit',expected);
  const pending=page.waitForResponse(r=>r.request().method()==='PUT'&&new URL(r.url()).pathname===path);pending.catch(()=>{});await page.locator('.modal-content button[type="submit"]').click();const response=await pending;result.requests.push({channel:'ui',method:'PUT',path,body:response.request().postDataJSON(),status:response.status()});await save();assert.equal(response.status(),200);await page.locator('.modal-content').waitFor({state:'hidden'});
  const after=await api('GET',path);assert.equal(after.status,200);assert.deepEqual(business(after.value),expected);result.final=business(after.value);result.timing.continuation_s=(performance.now()-nativeStart)/1000;await open();await snapshot('fresh_final',expected);
 }
 result.status='ordinary_control_passed';
}catch(error){result.error={name:error.name,message:redact(error.message),cause:error.cause?redact(String(error.cause)):undefined};process.exitCode=1}
finally{try{if(browser)await browser.close();result.browser_cleanup_confirmed=true}catch(error){result.browser_cleanup_confirmed=false;result.status='incomplete';result.error={name:error.name,message:redact(error.message)};process.exitCode=1}await save()}
