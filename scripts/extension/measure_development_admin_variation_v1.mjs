import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {parseArgs} from 'node:util';
import assert from 'node:assert/strict';
const {values:a}=parseArgs({options:{out:{type:'string'},case:{type:'string'}}});
const schedule=JSON.parse(await fs.readFile('manifests/development-admin-variation-schedule-v1.json','utf8'));
const c=schedule.cases.find(c=>c.id===a.case);assert.ok(c);
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
const base='http://127.0.0.1:8080',path='/api/admin/users',login='studycontrol';
const expected={id:null,login,firstName:'Study',lastName:'Control',email:'studycontrol@example.com',activated:true,langKey:'en',authorities:['ROLE_USER']};
const body={...expected};if(c.operator==='omit')delete body[c.field];if(c.operator==='null')body[c.field]=null;
const result={kind:'development_admin_input_variation',case:c,request_body:body,status:'not_run',stages:[],responses:[],blocked:[],page_errors:[],console_errors:[],request_failures:[],expected_create:expected,independent_evaluation_cases:0};
let browser,page,token;await fs.mkdir(a.out,{recursive:true});
const counts={authenticate:0,create:0,update:0};
function projection(body){return Object.fromEntries(Object.keys(expected).map(k=>[k,body[k]]));}
try{
 assert.equal(process.version,'v20.20.2');
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']});
 assert.equal(browser.version(),'151.0.7922.34');
 const context=await browser.newContext({locale:'en-US',timezoneId:'UTC',viewport:{width:1280,height:900},serviceWorkers:'block'});
 await context.route('**/*',async route=>{
  const r=route.request(),u=new URL(r.url());let allow=u.origin===base&&['GET','HEAD'].includes(r.method());
  const kind=r.method()==='POST'&&u.pathname==='/api/authenticate'?'authenticate':r.method()==='POST'&&u.pathname===path?'create':r.method()==='PUT'&&u.pathname===path?'update':null;
  if(u.origin===base&&kind&&counts[kind]===0){counts[kind]++;allow=true;}
  if(allow)return route.continue();result.blocked.push({method:r.method(),origin:u.origin,path:u.pathname});return route.abort();
 });
 page=await context.newPage();page.setDefaultTimeout(20000);
 page.on('response',r=>{if(result.responses.length<300)result.responses.push({method:r.request().method(),path:new URL(r.url()).pathname,status:r.status()});});
 page.on('pageerror',e=>result.page_errors.push(String(e).slice(0,1000)));
 page.on('console',m=>{if(m.type()==='error'&&result.console_errors.length<100)result.console_errors.push(m.text().slice(0,1000));});
 page.on('requestfailed',r=>result.request_failures.push({path:new URL(r.url()).pathname,error:r.failure()?.errorText}));
 await page.goto(base+'/',{waitUntil:'domcontentloaded'});
 await page.locator('[data-cy="accountMenu"]').click();await page.locator('[data-cy="login"]').click();
 await page.locator('[data-cy="username"]').fill('admin');await page.locator('[data-cy="password"]').fill('admin');
 const [auth,account]=await Promise.all([page.waitForResponse(r=>new URL(r.url()).pathname==='/api/authenticate'&&r.request().method()==='POST'),page.waitForResponse(r=>new URL(r.url()).pathname==='/api/account'&&r.status()===200),page.locator('[data-cy="submit"]').click()]);
 const who=await account.json();assert.equal(auth.status(),200);assert.equal(who.login,'admin');assert.ok(who.authorities.includes('ROLE_ADMIN'));
 result.actor={login:who.login,authorities:who.authorities};result.stages.push('native_admin_login');
 token=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('jhi-authenticationToken')||localStorage.getItem('jhi-authenticationToken')));
 assert.equal(typeof token,'string');
 async function readback(){const r=await context.request.get(base+path+'/'+login,{headers:{Authorization:'Bearer '+token},timeout:15000,maxRedirects:0});assert.equal(r.status(),200);return projection(await r.json());}
 counts.create++;
 const response=await context.request.post(base+path,{headers:{Authorization:'Bearer '+token},data:body,timeout:15000,maxRedirects:0});
 result.producer={status:response.status(),body};
 result.producer_response=await response.text();
 if(response.status()>=400&&response.status()<500){result.outcome='producer_rejected';result.status='observed';}
 else if(response.status()!==201){result.outcome='producer_unexpected_status';result.status='observed';}
 else if(typeof body.login!=='string'||!body.login){result.outcome='accepted_unaddressable';result.status='observed';}
 else {
  result.stages.push('producer_accepted');
  const created=await readback();result.after_create=created;assert.ok(created.id!=null);result.stages.push('created_state_readback');
  await page.goto(base+'/admin/user-management/'+login+'/edit',{waitUntil:'domcontentloaded'});
  await page.locator('input[name="login"]').waitFor({state:'visible'});
  const loaded={};for(const f of ['login','firstName','lastName','email'])loaded[f]=await page.locator('input[name="'+f+'"]').inputValue();
  result.loaded_fields=loaded;for(const f of Object.keys(loaded))assert.equal(loaded[f],created[f]??'');
  const save=page.locator('form[name="editForm"] button[type="submit"]');
  result.save_enabled_on_load=await save.isEnabled();
  const editField=c.field==='firstName'?'lastName':'firstName';result.edit_field=editField;
  await page.locator('input[name="'+editField+'"]').fill('Edited');
  result.save_enabled_after_unrelated_edit=await save.isEnabled();
  result.before_repair_form=await page.locator('form[name="editForm"]').innerText();
  await page.screenshot({path:a.out+'/before-save.png'});
  let repaired=false;
  if(!result.save_enabled_after_unrelated_edit&&c.field){
   await page.locator('input[name="'+c.field+'"]').fill(expected[c.field]);repaired=true;
   result.save_enabled_after_target_repair=await save.isEnabled();
   await page.screenshot({path:a.out+'/after-target-repair.png'});
  }
  if(await save.isEnabled()){
   const [updated]=await Promise.all([page.waitForResponse(r=>new URL(r.url()).pathname===path&&r.request().method()==='PUT'),save.click()]);
   result.consumer={status:updated.status(),body:updated.request().postDataJSON()};
   if(updated.status()===200){
    result.after_edit=await readback();assert.equal(result.after_edit.id,created.id);assert.equal(result.after_edit[editField],'Edited');
    if(repaired)assert.equal(result.after_edit[c.field],expected[c.field]);
    result.outcome=repaired?'blocked_then_target_repair_saved':'native_edit_saved';
   }else result.outcome=repaired?'repair_submit_rejected':'native_submit_rejected';
  }else result.outcome='native_save_disabled_after_repair';
  result.status='observed';
 }
}catch(e){result.status='failed';result.error_type=e.name;result.error=String(e);}
finally{
 result.write_counts=counts;token=null;
 if(page){result.final_url=page.url();try{await page.screenshot({path:a.out+'/final.png',timeout:5000});}catch(e){result.screenshot_error=String(e);}}
 if(browser)await browser.close();await fs.writeFile(a.out+'/admin-variation.json',JSON.stringify(result,null,2)+'\n');
}
if(result.status!=='observed')process.exitCode=1;
