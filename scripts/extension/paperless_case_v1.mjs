/** Ordinary Paperless API/native qualification, with full-object API update. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {parseArgs} from 'node:util';
import {performance} from 'node:perf_hooks';
const {values:a}=parseArgs({options:{registry:{type:'string'},workflow:{type:'string'},channel:{type:'string'},out:{type:'string'},case:{type:'string'}}});
const registry=JSON.parse(await readFile(a.registry,'utf8')),w=registry.workflows.find(w=>w.id===a.workflow),auth=JSON.parse(process.env.STUDY_EPHEMERAL_AUTH);assert.ok(w&&['api','ui'].includes(a.channel));assert.equal(auth.version,registry.version);
assert.equal(registry.execution_authorized,true);const c=registry.cases.find(c=>c.id===a.case);assert.ok(c&&c.workflow===w.id);
const payload={...c.payload,owner:auth.user_id},base='http://127.0.0.1:18080';await mkdir(a.out,{recursive:true});const result={kind:'paperless_finite_case_v1',case_id:c.id,prefix_status:'unresolved',continuation:'not_attempted',workflow:w.id,channel:a.channel,status:'incomplete',requests:[],forms:[],timing:{}};
const redact=s=>String(s).replaceAll(auth.password,'[redacted]').replaceAll(auth.token,'[redacted]');const save=()=>writeFile(a.out+'/observation.json',redact(JSON.stringify(result,null,2))+'\n');const business=x=>Object.fromEntries(w.fields.map(k=>{assert.ok(Object.hasOwn(x,k),'Missing persisted field '+k);return[k,x[k]]}));
async function api(method,path,body){const t=performance.now(),response=await fetch(base+path,{method,headers:{Authorization:'Token '+auth.token,'Content-Type':'application/json',Accept:'application/json; version=10'},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});const raw=await response.text();let value;try{value=JSON.parse(raw)}catch{value={unparsed:raw}}result.requests.push({channel:'api',api_version:10,method,path,body,status:response.status,response:value,elapsed_s:(performance.now()-t)/1000});await save();return{status:response.status,value};}
const equal=(a,b)=>{try{assert.deepEqual(a,b);return true}catch{return false}};
function outcome(status,after,before,expected){if(equal(after,expected)&&status>=200&&status<400)return'clean_preserving_continuation';if(!equal(after,before)&&!(status>=200&&status<400))return'failed_write_state_change';if(status>=200&&status<400)return'preservation_or_edit_discrepancy';if([400,409,422].includes(status)&&equal(after,before))return'blocked_save';return'execution_unknown';}
let browser;
async function execute(){
 const initial=await api('GET',w.collection);assert.equal(initial.status,200);assert.equal(initial.value.count,0);result.initial_business_state={actor:auth.username,actor_id:auth.user_id,resource_count:0,version:auth.version};
 const producerStart=performance.now(),made=await api('POST',w.collection,payload);result.immediate_status=made.status;result.timing.producer_s=(performance.now()-producerStart)/1000;
 if(made.status!==201){const after=await api('GET',w.collection);assert.equal(after.status,200);result.collection_after_rejection=after.value;result.prefix_status=[400,409,422].includes(made.status)&&after.value.count===0?'rejected_without_visible_write':'unresolved';result.status='observed';return;}
 assert.ok(Number.isInteger(made.value.id));const path=w.collection+made.value.id+'/';const before=await api('GET',path);assert.equal(before.status,200);result.prefix=business(before.value);result.prefix_status='accepted_persisted';result.resource_id=made.value.id;const expected={...result.prefix,[w.edit_field]:w.edit_value};
 result.immediate_schema={has_integer_identity:true,business_fields_present:w.fields.every(k=>Object.hasOwn(made.value,k)),response_matches_readback:equal(business(made.value),result.prefix)};
 result.response_contract_violations=Object.entries(registry.response_contracts[w.id]).filter(([key,rule])=>{const value=made.value[key];if(value===null&&rule.nullable)return false;return typeof value!==rule.type||(rule.integer&&!Number.isInteger(value))||(rule.max_length!==undefined&&typeof value==='string'&&value.length>rule.max_length)||(rule.options&&!rule.options.includes(value))||(rule.pattern&&typeof value==='string'&&!new RegExp(rule.pattern).test(value))}).map(([key])=>key);
 result.producer_input_differences=Object.fromEntries(Object.entries(payload).filter(([key,value])=>!equal(value,result.prefix[key])));
 if(a.channel==='api'){
  const t=performance.now(),updated=await api('PUT',path,expected);const after=await api('GET',path);assert.equal(after.status,200);result.final=business(after.value);result.continuation=outcome(updated.status,result.final,result.prefix,expected);result.timing.continuation_s=(performance.now()-t)/1000;
 }else{
  const t=performance.now(),require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH);browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE,args:['--no-sandbox']});const context=await browser.newContext({locale:'en-US',timezoneId:'UTC'});await context.route('**/*',route=>new URL(route.request().url()).origin===base?route.continue():route.abort());const page=await context.newPage();page.setDefaultTimeout(20000);
  await page.goto(base+'/accounts/login/');await page.locator('input[name="login"]').fill(auth.username);await page.locator('input[name="password"]').fill(auth.password);await Promise.all([page.waitForURL(url=>!url.pathname.startsWith('/accounts/')),page.locator('button[type="submit"]').click()]);result.timing.native_auth_setup_s=(performance.now()-t)/1000;
  const open=async(name)=>{await page.goto(base+w.list_path);await page.locator('table tbody .name-cell button').filter({hasText:name}).click();await page.locator('.modal-content').waitFor({state:'visible'});await page.waitForFunction(()=>{const button=document.querySelector('.modal-content button[aria-label="Close"]');return button&&!button.disabled});};
  const snapshot=async(label,values)=>{
   const dialog=page.locator('.modal-content'),fields=[];
   for(const f of w.native_fields){
    const loc=dialog.locator(f.selector),count=await loc.count(),displayed=!(f.hidden_for_algorithms||[]).includes(values.matching_algorithm);
    const expectedValue=f.kind==='label'?(registry.algorithm_labels[String(values[f.field])]??null):values[f.field];
    const observed=count===1?(f.kind==='label'?(await loc.innerText()).trim():f.kind==='checkbox'?await loc.isChecked():await loc.inputValue()):null;
    fields.push({name:f.field,count,displayed,value:observed,expected:displayed?expectedValue:null,selector:f.selector,kind:f.kind,agrees:displayed?(count===1&&expectedValue!==undefined&&expectedValue!==null&&equal(observed,expectedValue)):count===0,attributes:count===1?await loc.evaluate(e=>({required:e.required??null,maxlength:e.getAttribute('maxlength'),pattern:e.getAttribute('pattern')})):null});
   }
   result.forms.push({label,fields});await page.screenshot({path:a.out+'/'+label+'.png',fullPage:true});await save();return fields.every(f=>f.agrees);
  };
  const nativeStart=performance.now();await open(result.prefix.name);if(!await snapshot('loaded',result.prefix)){result.continuation='loaded_value_discrepancy';result.status='observed';return;}await page.locator('.modal-content '+w.edit_selector).fill(w.edit_value);await page.locator('.modal-content '+w.edit_selector).blur();assert.ok(await snapshot('before_submit',expected),'Adapter changed unexpected field');
  const pending=page.waitForResponse(r=>r.request().method()==='PUT'&&new URL(r.url()).pathname===path);pending.catch(()=>{});await page.locator('.modal-content button[type="submit"]').click();const response=await pending;result.requests.push({channel:'ui',method:'PUT',path,body:response.request().postDataJSON(),accept:response.request().headers()['accept'],status:response.status()});await save();assert.ok(response.request().headers()['accept'].includes('version=10'),'Native API version differs');if(response.status()===200)await page.locator('.modal-content').waitFor({state:'hidden'});
  const after=await api('GET',path);assert.equal(after.status,200);result.final=business(after.value);result.continuation=outcome(response.status(),result.final,result.prefix,expected);result.timing.continuation_s=(performance.now()-nativeStart)/1000;if(response.status()!==200){result.validation_text=await page.locator('.modal-content').innerText();await page.screenshot({path:a.out+'/rejected.png',fullPage:true});await page.locator('.modal-content button[aria-label="Close"]').click();await page.locator('.modal-content').waitFor({state:'hidden'});}await open(result.final.name);if(!await snapshot('fresh_final',result.final))result.continuation='fresh_editor_value_discrepancy';
 }
 result.status='observed';
}
try{await execute()}catch(error){result.error={name:error.name,message:redact(error.message),cause:error.cause?redact(String(error.cause)):undefined};result.continuation='execution_unknown';process.exitCode=1}
finally{try{if(browser)await browser.close();result.browser_cleanup_confirmed=true}catch(error){result.browser_cleanup_confirmed=false;result.status='incomplete';result.error={name:error.name,message:redact(error.message)};process.exitCode=1}await save()}
