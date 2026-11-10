/** Draft finite-case executor. Execution requires a separately frozen qualification registry. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {parseArgs} from 'node:util';
import {performance} from 'node:perf_hooks';
const {values:a}=parseArgs({options:{registry:{type:'string'},workflow:{type:'string'},channel:{type:'string'},out:{type:'string'},case:{type:'string'}}});
const registry=JSON.parse(await readFile(a.registry,'utf8'));
assert.equal(registry.execution_authorized,true);assert.ok(['api','ui'].includes(a.channel));
const w=registry.workflows.find(w=>w.id===a.workflow),c=registry.cases.find(c=>c.id===a.case);assert.ok(w&&c&&c.workflow===w.id);
const auth=JSON.parse(process.env.STUDY_EPHEMERAL_AUTH),base='http://127.0.0.1:18080';await mkdir(a.out,{recursive:true});
const result={kind:'linkding_finite_case_v1',case_id:c.id,workflow:w.id,channel:a.channel,status:'incomplete',requests:[],forms:[],timing:{},prefix_status:'unresolved',continuation:'not_attempted'};
const redact=s=>String(s).replaceAll(auth.password,'[redacted]').replaceAll(auth.token,'[redacted]');
const save=()=>writeFile(a.out+'/observation.json',redact(JSON.stringify(result,null,2))+'\n');
const business=x=>Object.fromEntries(w.fields.map(k=>{assert.ok(Object.hasOwn(x,k),'Missing persisted field '+k);return[k,x[k]]}));
const equal=(x,y)=>{try{assert.deepEqual(x,y);return true}catch{return false}};
async function api(method,path,body){const start=performance.now();const response=await fetch(base+path,{method,headers:{Authorization:'Token '+auth.token,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});const raw=await response.text();let value;try{value=JSON.parse(raw)}catch{value={unparsed:raw}}result.requests.push({channel:'api',method,path,body,status:response.status,response:value,elapsed_s:(performance.now()-start)/1000});await save();return{status:response.status,value};}
function outcome(status,after,before,expected){if(equal(after,expected)&&status>=200&&status<400)return'clean_preserving_continuation';if(!equal(after,before)&&!(status>=200&&status<400))return'failed_write_state_change';if(status>=200&&status<400)return'preservation_or_edit_discrepancy';if([400,409,422].includes(status)&&equal(after,before))return'blocked_save';return'execution_unknown';}
let browser;
async function execute(){
 const profile=await api('GET','/api/user/profile/');assert.equal(profile.status,200);assert.equal(String(profile.value.version).replace(/^v/,''),registry.version);
 const initial=await api('GET',w.collection);assert.equal(initial.status,200);assert.equal(initial.value.count,0);result.initial_business_state={actor:auth.username,resource_count:0,version:profile.value.version};
 const start=performance.now();const made=await api('POST',w.collection+w.create_query,c.payload);result.immediate_status=made.status;result.timing.producer_s=(performance.now()-start)/1000;
 if(made.status!==201){const after=await api('GET',w.collection);assert.equal(after.status,200);result.collection_after_rejection=after.value;result.prefix_status=[400,409,422].includes(made.status)&&after.value.count===0?'rejected_without_visible_write':'unresolved';result.status='observed';return;}
 assert.ok(Number.isInteger(made.value.id));const path=w.collection+made.value.id+'/';const before=await api('GET',path);assert.equal(before.status,200);result.resource_id=made.value.id;result.prefix=business(before.value);result.prefix_status='accepted_persisted';result.immediate_schema={has_integer_identity:true,business_fields_present:w.fields.every(k=>Object.hasOwn(made.value,k)),response_matches_readback:equal(business(made.value),result.prefix)};
 result.response_contract_violations=Object.entries(registry.response_contracts[w.id]).filter(([key,rule])=>{const value=made.value[key];return (rule.type==='array'?!Array.isArray(value):typeof value!==rule.type)||(rule.max_length!==undefined&&typeof value==='string'&&value.length>rule.max_length)||(rule.options&&!rule.options.includes(value))}).map(([key])=>key);
 result.producer_input_differences=Object.fromEntries(Object.entries(c.payload).filter(([key,value])=>!equal(value,result.prefix[key])));
 const expected={...result.prefix,[w.edit_field]:w.edit_value};
 if(a.channel==='api'){
  const t=performance.now();const update=await api('PUT',path,expected);const after=await api('GET',path);assert.equal(after.status,200);result.final=business(after.value);result.continuation=outcome(update.status,result.final,result.prefix,expected);result.timing.continuation_s=(performance.now()-t)/1000;result.status='observed';return;
 }
 const t=performance.now(),require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH);browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE,args:['--no-sandbox']});const context=await browser.newContext({locale:'en-US',timezoneId:'UTC'});await context.route('**/*',route=>new URL(route.request().url()).origin===base?route.continue():route.abort());const page=await context.newPage();page.setDefaultTimeout(15000);
 await page.goto(base+'/login/');await page.locator('[name="username"]').fill(auth.username);await page.locator('[name="password"]').fill(auth.password);await Promise.all([page.waitForURL(url=>!url.pathname.startsWith('/login')),page.locator('button[type="submit"], input[type="submit"]').click()]);result.timing.native_auth_setup_s=(performance.now()-t)/1000;
 const editPath=w.edit_path.replace('{id}',String(made.value.id));
 const snapshot=async label=>{const fields=await page.locator('form input:not([type="hidden"]):not([type="password"]):not([type="submit"]),form textarea,form select').evaluateAll(elements=>elements.filter(e=>e.name).map(e=>({name:e.name,id:e.id,type:e.type,value:e.type==='checkbox'?e.checked:e.value,required:e.required,maxlength:e.getAttribute('maxlength'),min:e.getAttribute('min'),max:e.getAttribute('max'),pattern:e.getAttribute('pattern'),options:e.tagName==='SELECT'?[...e.options].map(o=>o.value):undefined})));result.forms.push({label,fields});await page.screenshot({path:a.out+'/'+label+'.png',fullPage:true});await save();return fields;};
 const compare=(fields,values)=>w.form_fields.map(key=>{const found=fields.filter(f=>f.name===key);assert.equal(found.length,1,'Native binding ambiguous: '+key);return{field:key,expected:values[key],observed:found[0].value,agrees:equal(found[0].value,values[key])}});
 const nativeStart=performance.now(),loaded=await page.goto(base+editPath);result.editor_status=loaded.status();if(loaded.status()!==200){result.continuation='editor_load_failure';result.status='observed';return;}
 result.loaded_agreement=compare(await snapshot('loaded'),result.prefix);
 if(!result.loaded_agreement.every(x=>x.agrees)){result.continuation='loaded_value_discrepancy';result.status='observed';return;}
 await page.locator('form [name="'+w.edit_field+'"]').fill(w.edit_value);result.submission_agreement=compare(await snapshot('before_submit'),expected);assert.ok(result.submission_agreement.every(x=>x.agrees),'Adapter changed unexpected field');
 const responsePromise=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname===editPath);
 responsePromise.catch(()=>{});await page.locator('form input[type="submit"][value="Save"]').click();const response=await responsePromise;const posted=new URLSearchParams(response.request().postData()||'');posted.delete('csrfmiddlewaretoken');result.requests.push({channel:'ui',method:'POST',path:editPath,body:[...posted.entries()],status:response.status()});await save();assert.equal(posted.get(w.edit_field),w.edit_value);
 const after=await api('GET',path);assert.equal(after.status,200);result.final=business(after.value);result.continuation=outcome(response.status(),result.final,result.prefix,expected);result.timing.continuation_s=(performance.now()-nativeStart)/1000;
 if(response.status()===422){await page.waitForLoadState('domcontentloaded');result.validation_text=await page.locator('body').innerText();await page.screenshot({path:a.out+'/rejected.png',fullPage:true});}
 await page.goto(base+editPath);result.final_form_agreement=compare(await snapshot('fresh_final'),result.final);if(!result.final_form_agreement.every(x=>x.agrees))result.continuation='fresh_editor_value_discrepancy';result.status='observed';
}
try{await execute()}catch(error){result.error={name:error.name,message:redact(error.message),cause:error.cause?redact(String(error.cause)):undefined};result.status='incomplete';result.continuation='execution_unknown';process.exitCode=1}finally{try{if(browser)await browser.close();result.browser_cleanup_confirmed=true}catch(error){result.browser_cleanup_confirmed=false;result.status='incomplete';result.error={name:error.name,message:redact(error.message),cause:error.cause?redact(String(error.cause)):undefined};process.exitCode=1}await save()}
