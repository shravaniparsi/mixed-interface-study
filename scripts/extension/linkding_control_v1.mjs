/** Ordinary API/native controls only; no boundary inventory can be passed here. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {parseArgs} from 'node:util';
import {performance} from 'node:perf_hooks';
const {values:a}=parseArgs({options:{registry:{type:'string'},workflow:{type:'string'},channel:{type:'string'},out:{type:'string'}}});
assert.ok(['api','ui'].includes(a.channel));
const registry=JSON.parse(await readFile(a.registry,'utf8')),w=registry.workflows.find(x=>x.id===a.workflow);assert.ok(w);
const auth=JSON.parse(process.env.STUDY_EPHEMERAL_AUTH);assert.ok(auth.token&&auth.password);
const base='http://127.0.0.1:18080',out=a.out;await mkdir(out,{recursive:true});
const result={kind:'linkding_ordinary_control_v1',workflow:w.id,channel:a.channel,status:'incomplete',requests:[],forms:[],checks:[],timing:{}};
const save=async()=>writeFile(out+'/observation.json',JSON.stringify(result,null,2)+'\n');
const business=x=>Object.fromEntries(w.fields.map(k=>{assert.ok(Object.hasOwn(x,k),'Missing persisted field '+k);return [k,x[k]]}));
async function api(method,path,body){
 const start=performance.now();const response=await fetch(base+path,{method,headers:{Authorization:'Token '+auth.token,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});
 const raw=await response.text();let value;try{value=JSON.parse(raw)}catch{value={unparsed:raw}}
 result.requests.push({channel:'api',method,path,body,status:response.status,response:value,elapsed_s:(performance.now()-start)/1000});await save();return {status:response.status,value};
}
let browser;
try{
 const profile=await api('GET','/api/user/profile/');assert.equal(profile.status,200);assert.equal(String(profile.value.version).replace(/^v/,''),registry.version);result.checks.push('application_version');
 const initial=await api('GET',w.collection);assert.equal(initial.status,200);assert.equal(initial.value.count,0);result.initial_business_state={actor:auth.username,resource_count:0,version:profile.value.version};
 let start=performance.now();const created=await api('POST',w.collection+w.create_query,w.payload);assert.equal(created.status,201);assert.ok(Number.isInteger(created.value.id));
 const path=w.collection+created.value.id+'/';const before=await api('GET',path);assert.equal(before.status,200);assert.deepEqual(business(before.value),w.payload);result.prefix=business(before.value);result.resource_id=created.value.id;result.checks.push('prefix_persisted_exactly');result.timing.prefix_s=(performance.now()-start)/1000;
 const expected={...w.payload,[w.edit_field]:w.edit_value};
 if(a.channel==='api'){
  start=performance.now();const update=await api('PATCH',path,{[w.edit_field]:w.edit_value});assert.equal(update.status,200);const after=await api('GET',path);assert.equal(after.status,200);assert.deepEqual(business(after.value),expected);result.final=business(after.value);result.timing.assigned_continuation_s=(performance.now()-start)/1000;
 }else{
  start=performance.now();const require=createRequire(import.meta.url);const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH);browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE,args:['--no-sandbox']});
  const context=await browser.newContext({locale:'en-US',timezoneId:'UTC'});await context.route('**/*',route=>new URL(route.request().url()).origin===base?route.continue():route.abort());
  const page=await context.newPage();page.setDefaultTimeout(15000);await page.goto(base+'/login/');await page.locator('[name="username"]').fill(auth.username);await page.locator('[name="password"]').fill(auth.password);
  await Promise.all([page.waitForURL(url=>!url.pathname.startsWith('/login')),page.locator('button[type="submit"], input[type="submit"]').click()]);result.timing.native_auth_setup_s=(performance.now()-start)/1000;
  const editPath=w.edit_path.replace('{id}',String(created.value.id));
  const snapshot=async(label,expectedValues)=>{
   const fields=await page.locator('form input:not([type="hidden"]):not([type="password"]):not([type="submit"]),form textarea,form select').evaluateAll(elements=>elements.filter(e=>e.name).map(e=>({name:e.name,id:e.id,type:e.type,value:e.type==='checkbox'?e.checked:e.value,required:e.required,maxlength:e.getAttribute('maxlength'),min:e.getAttribute('min'),max:e.getAttribute('max'),pattern:e.getAttribute('pattern'),options:e.tagName==='SELECT'?[...e.options].map(o=>o.value):undefined})));
   for(const key of w.form_fields){const found=fields.filter(f=>f.name===key);assert.equal(found.length,1,'Expected exactly one native field '+key);assert.deepEqual(found[0].value,expectedValues[key],'Loaded native value differs for '+key)}
   result.forms.push({label,fields});await page.screenshot({path:out+'/'+label+'.png',fullPage:true});await save();
  };
  start=performance.now();await page.goto(base+editPath);await snapshot('loaded',w.payload);
  await page.locator('[name="'+w.edit_field+'"]').fill(w.edit_value);
  const responsePromise=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname===editPath);
  await page.locator('form input[type="submit"][value="Save"]').click();const response=await responsePromise;
  const posted=new URLSearchParams(response.request().postData()||'');posted.delete('csrfmiddlewaretoken');result.requests.push({channel:'ui',method:'POST',path:editPath,body:[...posted.entries()],status:response.status()});await save();assert.ok([200,302,303].includes(response.status()),'Native save rejected');
  const after=await api('GET',path);assert.equal(after.status,200);assert.deepEqual(business(after.value),expected);result.final=business(after.value);result.timing.assigned_continuation_s=(performance.now()-start)/1000;
  await page.goto(base+editPath);await snapshot('fresh_final',expected);
 }
 result.checks.push('edit_persisted','unedited_fields_preserved');result.status='ordinary_control_passed';
}catch(error){result.error={name:error.name,message:String(error.message).replaceAll(auth.password,'[redacted]').replaceAll(auth.token,'[redacted]')};process.exitCode=1}
finally{try{if(browser)await browser.close();result.browser_cleanup_confirmed=true}catch(error){result.browser_cleanup_confirmed=false;result.error={name:error.name,message:String(error.message).replaceAll(auth.password,'[redacted]').replaceAll(auth.token,'[redacted]')};result.status='incomplete';process.exitCode=1}await save()}
