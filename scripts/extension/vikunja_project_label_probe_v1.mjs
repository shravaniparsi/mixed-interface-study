import {installWriteObserver,collectWriteObserver} from './vikunja_fetch_observer_v1.mjs';
/** Ordinary API-v2/native qualification; no boundary inputs. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {parseArgs} from 'node:util';
const {values:a}=parseArgs({options:{registry:{type:'string'},workflow:{type:'string'},channel:{type:'string'},out:{type:'string'}}});
const reg=JSON.parse(await readFile(a.registry,'utf8')),spec=reg.workflows.find(w=>w.id===a.workflow);assert.ok(spec&&['api','ui'].includes(a.channel));
const base='http://127.0.0.1:18080',password=process.env.STUDY_EPHEMERAL_PASSWORD,secrets=[password];assert.ok(password);
const result={kind:'vikunja_ordinary_control_v1',workflow:a.workflow,channel:a.channel,status:'incomplete',requests:[],forms:[],native_requests:[]};await mkdir(a.out,{recursive:true});
const redact=s=>secrets.reduce((s,v)=>v?s.replaceAll(v,'[redacted]'):s,String(s));
const save=()=>writeFile(a.out+'/observation.json',redact(JSON.stringify(result,null,2))+'\n');
let token,browser,target;
async function api(method,path,body,status=200,privateCall=false){
 const r=await fetch(base+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});
 const raw=await r.text();let value;try{value=JSON.parse(raw)}catch{value={unparsed:raw}}
 if(!privateCall){result.requests.push({method,path,body,status:r.status,response:value});await save()}
 else if(r.status!==status){result.bootstrap_failure={method,path,status:r.status,code:value.code,message:redact(value.message??value.detail??'')};await save()}
 assert.equal(r.status,status,method+' '+path);return value;
}
function business(v){
 const x=structuredClone(v);delete x.created;delete x.updated;
 for(const k of ['owner','created_by'])if(x[k]){delete x[k].created;delete x[k].updated}
 if(x.views)for(const view of x.views){delete view.created;delete view.updated}
 return x;
}
function unchanged(v){const x=structuredClone(v);delete x.updated;return x}
try{
 result.instance=await api('GET','/api/v2/info');await save();
 for(const username of ['study-bootstrap','study-actor'])await api('POST','/api/v2/register',{username,email:username+'@example.invalid',password,language:'en'},201,true);
 const login=await api('POST','/api/v2/login',{username:'study-actor',password},200,true);token=login.token;assert.ok(token);secrets.push(token);
 const actor=await api('GET','/api/v2/user');result.actor={id:actor.id,username:actor.username,is_admin:actor.is_admin};await save();assert.equal(actor.username,'study-actor');assert.equal(actor.is_admin,false);
 const before=await api('GET',spec.collection);assert.ok(Array.isArray(before.items));result.initial_raw=before;result.initial_business_state={...before,items:before.items.map(business)};await save();
 const created=await api('POST',spec.collection,spec.payload,201);assert.ok(created.id>0);target=spec.collection+'/'+created.id;
 result.prefix=await api('GET',target);result.prefix_business=business(result.prefix);await save();
 assert.equal(result.prefix[spec.owner_field].id,actor.id);
 const expected={...result.prefix,title:spec.edit_value},body=Object.fromEntries(spec.fields.map(k=>[k,expected[k]]));assert.ok(spec.fields.every(k=>k in result.prefix));
 if(a.channel==='api'){await api('PUT',target,body)}
 else{
  const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH);browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE});const context=await browser.newContext({locale:'en-US',timezoneId:'UTC'}),page=await context.newPage();page.setDefaultTimeout(20000);await installWriteObserver(page,target,'PUT');
  await page.goto(base+'/login');await page.locator('#username').fill('study-actor');await page.locator('#password').fill(password);
  await Promise.all([page.waitForURL(u=>!u.pathname.startsWith('/login')),page.locator('#loginform').getByRole('button',{name:'Login',exact:true}).click()]);
  async function open(){await page.goto(base+spec.edit_path.replace('{id}',String(created.id)));if(a.workflow==='label')await page.locator('.label-edit-button').click();await page.locator(spec.title_selector).waitFor({state:'visible'});await page.locator('.tiptap__editor').waitFor({state:'visible'})}
  async function snapshot(label){const title=page.locator(spec.title_selector),editor=page.locator('.tiptap__editor'),color=page.locator('input[type=color]');assert.equal(await title.count(),1);assert.equal(await editor.count(),1);assert.equal(await color.count(),1);
   const f={label,title:await title.inputValue(),title_attributes:await title.evaluate(e=>({required:e.required,maxLength:e.maxLength,valid:e.checkValidity()})),description_text:await editor.innerText(),description_html:await editor.innerHTML(),color:await color.inputValue(),color_html:await color.evaluate(e=>e.parentElement.outerHTML)};
   if(a.workflow==='project'){f.identifier=await page.locator('#identifier').inputValue();f.identifier_attributes=await page.locator('#identifier').evaluate(e=>({type:e.type,maxLength:e.maxLength,required:e.required,value:e.value}));}result.forms.push(f);await save();return f;
  }
  await open();const loaded=await snapshot('loaded');assert.equal(loaded.title,result.prefix.title);assert.ok(loaded.description_text.includes('Ordinary description'));assert.equal(loaded.color.toLowerCase(),'#336699');
  if(a.workflow==='project')assert.equal(loaded.identifier,result.prefix.identifier);
  result.synthetic_probe={kind:'detached_native_input_coercion',color:await page.locator('input[type=color]').evaluate(e=>{const inputs=['#336699','','#abc','not-a-color','#12','#1234','#1234567'];return {type:e.type,original:e.value,samples:inputs.map(value=>{const clone=e.cloneNode();clone.value=value;return {input:value,value:clone.value,valid:clone.checkValidity()}})}})};
  if(a.workflow==='project'){const attrs=await page.locator('#identifier').evaluate(e=>({type:e.type,maxLength:e.maxLength,required:e.required}));assert.equal(attrs.maxLength,10);result.synthetic_probe.identifier={attributes:attrs,valid_input:'STUDY',violating_input:'ABCDEFGHIJK',valid_passes:'STUDY'.length<=attrs.maxLength,violation_detected:'ABCDEFGHIJK'.length>attrs.maxLength};}
  await save();assert.equal(result.synthetic_probe.color.type,'color');assert.equal(result.synthetic_probe.color.samples[0].value,'#336699');assert.notEqual(result.synthetic_probe.color.samples.find(x=>x.input==='not-a-color').value,'not-a-color');
  await page.locator(spec.title_selector).fill(spec.edit_value);await snapshot('before_submit');
  const pending=[];page.on('response',r=>{const q=r.request();if(new URL(r.url()).pathname===target&&q.method()==='PUT'){const record={method:q.method(),path:target,body:q.postData(),status:r.status()};result.native_requests.push(record);pending.push((async()=>{await save();record.response=await r.text();await save()})())}});
  const response=page.waitForResponse(r=>new URL(r.url()).pathname===target&&r.request().method()==='PUT');await page.getByRole('button',{name:'Save',exact:true}).click();assert.equal((await response).status(),200);await Promise.all(pending);
  result.fetch_requests=await collectWriteObserver(page);await save();assert.equal(result.native_requests.length,1);assert.equal(result.fetch_requests.length,1);const captured=result.fetch_requests[0];assert.equal(captured.status,200);assert.equal(captured.method,'PUT');assert.equal(captured.path,target);assert.deepEqual(JSON.parse(captured.body),body);if(result.native_requests[0].body!==null)assert.equal(result.native_requests[0].body,captured.body);
  await open();const finalForm=await snapshot('fresh_final');assert.equal(finalForm.title,spec.edit_value);assert.ok(finalForm.description_text.includes('Ordinary description'));assert.equal(finalForm.color.toLowerCase(),'#336699');
 }
 result.final=await api('GET',target);result.final_business=business(result.final);await save();assert.deepEqual(unchanged(result.final),unchanged(expected));result.status='ordinary_control_passed';
}catch(e){result.error={name:e.name,message:redact(e.message)};if(target)try{result.final=await api('GET',target);result.final_business=business(result.final)}catch(readError){result.final_read_error=redact(readError.message)}}
finally{if(browser)try{await browser.close();result.browser_cleanup_confirmed=true}catch(e){result.browser_cleanup_confirmed=false}else result.browser_cleanup_confirmed=true;await save()}
process.exitCode=result.status==='ordinary_control_passed'?0:1;
