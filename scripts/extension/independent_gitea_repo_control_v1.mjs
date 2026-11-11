import {formEntries} from './gitea_form_wire_v1.mjs';
/** Ordinary issue body qualification in a fresh local pinned Gitea. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {parseArgs} from 'node:util';
const {values:a}=parseArgs({options:{registry:{type:'string'},workflow:{type:'string'},channel:{type:'string'},out:{type:'string'}}});
const reg=JSON.parse(await readFile(a.registry,'utf8')),spec=reg.workflows.find(w=>w.id===a.workflow),auth=JSON.parse(process.env.STUDY_EPHEMERAL_AUTH);assert.ok(spec&&['api','ui'].includes(a.channel));
const base='http://127.0.0.1:18080',repoPath='/study-actor/study-repo',apiRepo='/api/v1/repos'+repoPath,secrets=[auth.password,auth.token];assert.ok(auth.password&&auth.token);
const result={kind:'gitea_ordinary_control_v1',workflow:a.workflow,channel:a.channel,status:'incomplete',requests:[],forms:[],native_requests:[]};await mkdir(a.out,{recursive:true});
const redact=s=>secrets.reduce((s,v)=>v?s.replaceAll(v,'[redacted]'):s,String(s));const save=()=>writeFile(a.out+'/observation.json',redact(JSON.stringify(result,null,2))+'\n');let browser,target,page;
async function api(method,path,body,status=200){const response=await fetch(base+path,{method,headers:{'Content-Type':'application/json',Authorization:'token '+auth.token},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});const raw=await response.text();let value;try{value=JSON.parse(raw)}catch{value={unparsed:raw}}result.requests.push({method,path,body,status:response.status,response:value});await save();assert.equal(response.status,status,method+' '+path);return value}
const business=v=>{const b=structuredClone(v);delete b.created_at;delete b.updated_at;if(b.owner){delete b.owner.created;delete b.owner.last_login}return b};
const preserved=v=>Object.fromEntries(Object.entries(v).filter(([k])=>k!=='updated_at'));
try{
 const setupStart=performance.now();
  const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH);browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE});const context=await browser.newContext({locale:'en-US',timezoneId:'UTC'});page=await context.newPage();page.setDefaultTimeout(20000);
  await page.goto(base+'/user/login');await page.locator('#user_name').fill('study-actor');await page.locator('#password').fill(auth.password);await Promise.all([page.waitForURL(u=>u.pathname!='/user/login'),page.locator('form').filter({has:page.locator('#user_name')}).locator('button[type=submit]').click()]);
 result.authentication_setup_ms=performance.now()-setupStart;
 result.instance=await api('GET','/api/v1/version');assert.equal(result.instance.version,reg.version);const actor=await api('GET','/api/v1/user');result.actor={id:actor.id,login:actor.login,is_admin:actor.is_admin};await save();assert.equal(actor.login,'study-actor');assert.equal(actor.is_admin,false);
 const initial=await api('GET','/api/v1/user/repos');assert.deepEqual(initial,[]);result.initial_business_state={actor:result.actor,resources:initial};
 const created=await api('POST','/api/v1/user/repos',spec.payload,201);assert.equal(created.owner.id,actor.id);assert.equal(created.full_name,'study-actor/study-repo');target='/api/v1/repos/'+created.full_name;
 result.prefix=await api('GET',target);result.prefix_business=business(result.prefix);await save();const p=result.prefix,expected={...p,description:spec.edit_value},body=Object.fromEntries(spec.fields.map(k=>[k,expected[k]]));assert.ok(spec.fields.every(k=>Object.hasOwn(p,k)));
 if(a.channel==='api')await api('PATCH',target,body,200);
 else{
  const editPath='/'+created.full_name+'/settings';const scope=()=>page.locator('form').filter({has:page.locator('input[name=action][value=update]')});
  async function open(){await page.goto(base+editPath);await scope().locator('textarea[name=description]').waitFor({state:'visible'})}
  async function snapshot(label){const form={label,fields:[]};for(const f of spec.native_fields){const loc=scope().locator(f.selector);assert.equal(await loc.count(),1);form.fields.push({name:f.field,selector:f.selector,value:f.kind==='checkbox'?await loc.isChecked():await loc.inputValue(),attributes:await loc.evaluate(e=>({required:e.required,maxLength:e.maxLength,valid:e.checkValidity()}))})}result.forms.push(form);await page.screenshot({path:a.out+'/'+label+'.png',fullPage:true});await save();return form}
  function matches(form,values){for(const f of form.fields)assert.deepEqual(f.value,values[f.name])}
  await open();matches(await snapshot('loaded'),p);await scope().locator('textarea[name=description]').fill(spec.edit_value);matches(await snapshot('before_submit'),expected);
  const responsePromise=page.waitForResponse(r=>new URL(r.url()).pathname===editPath&&r.request().method()==='POST');await scope().locator('button[type=submit]').click();const response=await responsePromise,q=response.request();const raw=q.postData(),contentType=q.headers()['content-type'],entries=await formEntries(raw,contentType);for(const [key,value] of entries)if(key==='_csrf'&&value)secrets.push(value,encodeURIComponent(value),new URLSearchParams([['_csrf',value]]).toString().slice(6));result.native_requests.push({method:'POST',path:editPath,body:raw,content_type:contentType,form_entries:entries,status:response.status()});await save();assert.ok([302,303].includes(response.status()));
  const submitted=new URLSearchParams(result.native_requests[0].form_entries);assert.equal(submitted.get('action'),'update');assert.equal(submitted.get('description'),spec.edit_value);assert.equal(submitted.get('repo_name'),p.name);assert.equal(submitted.get('website'),p.website);assert.equal(submitted.has('template'),p.template);
  await page.waitForLoadState('domcontentloaded');await open();matches(await snapshot('fresh_final'),expected);
 }
 result.final=await api('GET',target);result.final_business=business(result.final);await save();assert.deepEqual(preserved(result.final),preserved(expected));result.status='ordinary_control_passed';
}catch(e){result.error={name:e.name,message:redact(e.message)};if(target)try{result.final=await api('GET',target);result.final_business=business(result.final)}catch(readError){result.final_read_error=redact(readError.message)}}
finally{if(browser)try{await browser.close();result.browser_cleanup_confirmed=true}catch(e){result.browser_cleanup_confirmed=false}else result.browser_cleanup_confirmed=true;await save()}
process.exitCode=result.status==='ordinary_control_passed'?0:1;
