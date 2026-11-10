import {readPreferenceFields,requireOrdinaryPreferenceFields} from './memos_preference_fields_v1.mjs';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {parseArgs} from 'node:util';
import {decodeGeneralUpdate} from './memos_general_wire_v1.mjs';
const {values:a}=parseArgs({options:{registry:{type:'string'},workflow:{type:'string'},channel:{type:'string'},out:{type:'string'}}});
const reg=JSON.parse(await readFile(a.registry,'utf8'));assert.equal(a.workflow,'preferences');assert.ok(['api','ui'].includes(a.channel));
const base='http://127.0.0.1:18080',password=process.env.STUDY_EPHEMERAL_PASSWORD,secrets=[password];assert.ok(password);
const result={kind:'memos_preference_control_v1',channel:a.channel,status:'incomplete',requests:[],forms:[]};await mkdir(a.out,{recursive:true});
const redact=s=>secrets.reduce((s,v)=>v?s.replaceAll(v,'[redacted]'):s,String(s));
const save=()=>writeFile(a.out+'/observation.json',redact(JSON.stringify(result,null,2))+'\n');
let token,browser;
async function api(method,path,body,privateCall=false){
 const response=await fetch(base+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});
 const raw=await response.text();let value;try{value=JSON.parse(raw)}catch{value={unparsed:raw}}
 if(!privateCall){result.requests.push({method,path,body,status:response.status,response:value});await save()}
 if(privateCall && response.status!==200){result.bootstrap_failure={method,path,status:response.status,code:value.code,message:redact(value.message??'')};await save()}
 assert.equal(response.status,200,privateCall?'Private bootstrap failed':method+' '+path);return value;
}
const name='users/study-actor/settings/GENERAL',path='/api/'+name;
const seed={locale:'en',memoVisibility:'PROTECTED',theme:'paper',saveMediaMetadata:false};
const allMask='locale,memo_visibility,theme,save_media_metadata';
function project(v){assert.equal(v.name,name);assert.deepEqual(Object.keys(v).sort(),['generalSetting','name']);assert.deepEqual(Object.keys(v.generalSetting).sort(),Object.keys(seed).sort());return v.generalSetting}
try {
 const info=await api('GET','/api/instance/profile');result.instance=info;assert.equal(info.version,reg.version);
 const admin=await api('POST','/api/users',{username:'study-admin',password,role:'ADMIN'},true);assert.equal(admin.role,'ADMIN');
 let login=await api('POST','/api/auth/signin',{passwordCredentials:{username:'study-admin',password}},true);token=login.accessToken;assert.ok(token);secrets.push(token);
 const actor=await api('POST','/api/users',{username:'study-actor',password,role:'USER'},true);assert.equal(actor.role,'USER');
 login=await api('POST','/api/auth/signin',{passwordCredentials:{username:'study-actor',password}},true);token=login.accessToken;assert.ok(token);secrets.push(token);
 assert.equal(login.user.role,'USER');assert.equal(login.user.name,'users/study-actor');result.actor={name:login.user.name,role:login.user.role};
 const initial=await api('GET',path);result.initial_business_state={actor:result.actor,settings:initial,version:info.version};
 await api('PATCH',path+'?updateMask='+allMask,{name,generalSetting:seed});
 result.prefix=project(await api('GET',path));assert.deepEqual(result.prefix,seed);
 const expected={...seed,saveMediaMetadata:true};
 if(a.channel==='api'){
  await api('PATCH',path+'?updateMask='+allMask,{name,generalSetting:expected});
 }else{
  const require=createRequire(import.meta.url);const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH);browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE});
  const context=await browser.newContext({locale:'en-US',colorScheme:'light'}),page=await context.newPage();page.setDefaultTimeout(20000);
  await page.goto(base+'/auth');await page.locator('#signin-username').fill('study-actor');await page.locator('#signin-password').fill(password);await page.locator('form').filter({has:page.locator('#signin-username')}).locator('button[type=submit]').click();await page.waitForURL(u=>u.pathname!='/auth');
  const open=async()=>{await page.goto(base+'/setting#preference');await page.getByRole('switch',{name:'Save media metadata',exact:true}).waitFor();};
  const snapshot=async(label,want)=>{const control=page.getByRole('switch',{name:'Save media metadata',exact:true});const v={label,switch_count:await control.count(),checked:await control.getAttribute('aria-checked'),disabled:await control.isDisabled(),comboboxes:await page.getByRole('combobox').allTextContents()};v.preference_fields=await readPreferenceFields(page);result.forms.push(v);await save();requireOrdinaryPreferenceFields(v.preference_fields);await page.screenshot({path:a.out+'/'+label+'.png',fullPage:true});await save();assert.equal(v.switch_count,1);assert.equal(v.checked,String(want));assert.equal(v.disabled,false);};
  await open();await snapshot('loaded',false);
  const pending=page.waitForResponse(r=>new URL(r.url()).pathname==='/memos.api.UserService/UpdateUserSetting'&&r.request().method()==='POST');pending.catch(()=>{});
  await page.getByRole('switch',{name:'Save media metadata',exact:true}).click();const response=await pending,req=response.request(),bytes=req.postDataBuffer();assert.ok(bytes);
  const raw={method:req.method(),path:new URL(req.url()).pathname,content_type:req.headers()['content-type'],request_base64:bytes.toString('base64'),status:response.status(),response_base64:(await response.body()).toString('base64')};result.native_request=raw;await save();
  raw.decoded=decodeGeneralUpdate(bytes,raw.content_type);await save();assert.equal(response.status(),200);assert.equal(raw.decoded.userSetting.name,name);assert.deepEqual(raw.decoded.updateMask.paths,['save_media_metadata']);assert.equal(raw.decoded.userSetting.generalSetting.saveMediaMetadata,true);
  await open();await snapshot('fresh_final',true);
 }
 result.final=project(await api('GET',path));assert.deepEqual(result.final,expected);result.status='ordinary_control_passed';
}catch(e){result.error={name:e.name,message:redact(e.message)};process.exitCode=1}
finally{try{if(browser)await browser.close();result.browser_cleanup_confirmed=true}catch(e){result.browser_cleanup_confirmed=false;result.status='incomplete';process.exitCode=1}await save()}
