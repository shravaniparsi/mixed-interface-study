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
const redact=s=>secrets.reduce((s,v)=>v?s.replaceAll(v,'[redacted]'):s,String(s));const save=()=>writeFile(a.out+'/observation.json',redact(JSON.stringify(result,null,2))+'\n');let browser,target;
async function api(method,path,body,status=200){const response=await fetch(base+path,{method,headers:{'Content-Type':'application/json',Authorization:'token '+auth.token},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});const raw=await response.text();let value;try{value=JSON.parse(raw)}catch{value={unparsed:raw}}result.requests.push({method,path,body,status:response.status,response:value});await save();assert.equal(response.status,status,method+' '+path);return value}
const business=v=>{const b=structuredClone(v);delete b.created_at;delete b.updated_at;for(const u of [b.user,b.assignee,...(b.assignees??[])])if(u){delete u.created;delete u.last_login}return b};
const preserved=v=>Object.fromEntries(Object.entries(v).filter(([k])=>k!=='updated_at'));
try{
 result.instance=await api('GET','/api/v1/version');assert.equal(result.instance.version,reg.version);const actor=await api('GET','/api/v1/user');result.actor={id:actor.id,login:actor.login,is_admin:actor.is_admin};await save();assert.equal(actor.login,'study-actor');assert.equal(actor.is_admin,false);
 result.repository=await api('POST','/api/v1/user/repos',reg.repository,201);assert.equal(result.repository.owner.id,actor.id);assert.equal(result.repository.full_name,'study-actor/study-repo');
 const collection=apiRepo+'/'+spec.collection,initial=await api('GET',collection);assert.deepEqual(initial,[]);result.initial_business_state={actor:result.actor,repository:{id:result.repository.id,full_name:result.repository.full_name,owner_id:result.repository.owner.id},resources:initial};
 const created=await api('POST',collection,spec.payload,201);assert.ok(created.id>0);target=collection+'/'+created.number;result.prefix=await api('GET',target);result.prefix_business=business(result.prefix);await save();
 const p=result.prefix;assert.equal(p.milestone,null);assert.deepEqual(p.projects??[],[]);assert.deepEqual(p.assignees??[],[]);assert.deepEqual(p.labels??[],[]);assert.deepEqual(p.assets??[],[]);assert.equal(p.due_date,null);assert.equal(p.ref,'');assert.ok(Number.isInteger(p.content_version));const expected={...p,body:spec.edit_value,content_version:p.content_version+1},body={title:p.title,body:spec.edit_value,ref:p.ref,assignees:[],milestone:0,projects:[],state:p.state,due_date:null,unset_due_date:true,content_version:p.content_version};
 if(a.channel==='api')await api('PATCH',target,body,201);
 else{
  const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH);browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE});const context=await browser.newContext({locale:'en-US',timezoneId:'UTC'}),page=await context.newPage();page.setDefaultTimeout(20000);
  await page.goto(base+'/user/login');await page.locator('#user_name').fill('study-actor');await page.locator('#password').fill(auth.password);await Promise.all([page.waitForURL(u=>u.pathname!='/user/login'),page.locator('form').filter({has:page.locator('#user_name')}).locator('button[type=submit]').click()]);
  const editPath=repoPath+'/issues/'+created.number,writePath=editPath+'/content';
  const scope=()=>page.locator('.issue-content-comment');
  async function open(){await page.goto(base+editPath);await scope().locator('.context-menu').click();await scope().locator('.edit-content').click();await scope().locator('.edit-content-zone textarea[name=content]').waitFor({state:'visible'})}
  async function snapshot(label){const root=scope(),input=root.locator('.edit-content-zone textarea[name=content]');const form={label,title:await page.locator('#issue-title-editor input[name=title]').inputValue(),body:await input.inputValue(),content_version:await root.locator('.edit-content-zone').getAttribute('data-content-version'),body_attributes:await input.evaluate(e=>({required:e.required,maxLength:e.maxLength,valid:e.checkValidity()})),title_attributes:await page.locator('#issue-title-editor input[name=title]').evaluate(e=>({required:e.required,maxLength:e.maxLength}))};result.forms.push(form);await save();return form}
  await open();const loaded=await snapshot('loaded');assert.equal(loaded.title,p.title);assert.equal(loaded.body,p.body);assert.equal(loaded.content_version,String(p.content_version));
  await scope().locator('.edit-content-zone textarea[name=content]').fill(spec.edit_value);await snapshot('before_submit');
  const pending=[];page.on('response',r=>{const q=r.request();if(new URL(r.url()).pathname===writePath&&q.method()==='POST'){const captured=r.text().then(body=>({body}),error=>({error:redact(error.message)}));const work=(async()=>{const raw=q.postData(),contentType=q.headers()['content-type'],entries=await formEntries(raw,contentType);const item={method:'POST',path:writePath,body:raw,content_type:contentType,form_entries:entries,status:r.status()};result.native_requests.push(item);await save();const value=await captured;if(value.error)item.response_body_error=value.error;else item.response=value.body;await save()})();work.catch(()=>{});pending.push(work)}});
  const response=page.waitForResponse(r=>new URL(r.url()).pathname===writePath&&r.request().method()==='POST');await scope().locator('.edit-content-zone button[type=submit]').click();assert.equal((await response).status(),200);await Promise.all(pending);assert.equal(result.native_requests.length,1);
  const submitted=new URLSearchParams(result.native_requests[0].form_entries);assert.equal(submitted.get('content'),spec.edit_value);assert.equal(submitted.get('context'),repoPath);assert.equal(submitted.get('content_version'),String(p.content_version));
  await open();const last=await snapshot('fresh_final');assert.equal(last.title,p.title);assert.equal(last.body,spec.edit_value);assert.equal(last.content_version,String(p.content_version+1));

 }
 result.final=await api('GET',target);result.final_business=business(result.final);await save();assert.deepEqual(preserved(result.final),preserved(expected));result.status='ordinary_control_passed';
}catch(e){result.error={name:e.name,message:redact(e.message)};if(target)try{result.final=await api('GET',target);result.final_business=business(result.final)}catch(readError){result.final_read_error=redact(readError.message)}}
finally{if(browser)try{await browser.close();result.browser_cleanup_confirmed=true}catch(e){result.browser_cleanup_confirmed=false}else result.browser_cleanup_confirmed=true;await save()}
process.exitCode=result.status==='ordinary_control_passed'?0:1;
