/** Finite scientific observer. Raw observations precede outcome interpretation. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {parseArgs} from 'node:util';
import {performance} from 'node:perf_hooks';
import {decodeGeneralUpdate} from './memos_general_wire_v1.mjs';
import {decodeMemoAudienceUpdate} from './memos_memo_wire_v1.mjs';
import {readPreferenceFields} from './memos_preference_fields_v2.mjs';
const {values:a}=parseArgs({options:{registry:{type:'string'},case:{type:'string'},channel:{type:'string'},out:{type:'string'}}});
const reg=JSON.parse(await readFile(a.registry,'utf8')),spec=reg.cases.find(c=>c.id===a.case);assert.ok(spec&&['api','ui'].includes(a.channel));
const memo=spec.workflow==='memo',base='http://127.0.0.1:18080',password=process.env.STUDY_EPHEMERAL_PASSWORD,secrets=[password];assert.ok(password);
const name=memo?'memos/study-control':'users/study-actor/settings/GENERAL',path='/api/'+name;
const seed=memo?{content:'Ordinary memo',visibility:'PRIVATE',createTime:'2026-01-01T00:00:00Z',updateTime:'2026-01-01T00:00:00Z'}:{locale:'en',memoVisibility:'PROTECTED',theme:'paper',saveMediaMetadata:false};
const mask=memo?'content,visibility,space,pinned,state,create_time,update_time,location,attachments,relations':'locale,memo_visibility,theme,save_media_metadata';
const mutable=['content','visibility','space','pinned','state','createTime','updateTime','location','attachments','relations'];
const result={kind:'memos_finite_observation_v1',case_id:spec.id,workflow:spec.workflow,channel:a.channel,status:'incomplete',requests:[],forms:[],native_requests:[],timing:{}};await mkdir(a.out,{recursive:true});
const redact=s=>secrets.reduce((s,v)=>v?s.replaceAll(v,'[redacted]'):s,String(s));
const save=()=>writeFile(a.out+'/observation.json',redact(JSON.stringify(result,null,2))+'\n');
let token,browser;
async function api(method,p,body,privateCall=false){
 const start=performance.now(),response=await fetch(base+p,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});
 const raw=await response.text();let value;try{value=JSON.parse(raw)}catch{value={unparsed:raw}}
 if(!privateCall){result.requests.push({method,path:p,body,status:response.status,response:value,elapsed_s:(performance.now()-start)/1000});await save()}
 else if(response.status!==200){result.bootstrap_failure={method,path:p,status:response.status,code:value.code,message:redact(value.message??'')};await save()}
 return {status:response.status,value};
}
async function ok(method,p,body,priv=false){const r=await api(method,p,body,priv);assert.equal(r.status,200,priv?'Private setup':method+' '+p);return r.value}
function project(v){assert.equal(v.name,name);if(memo){assert.equal(v.creator,'users/study-actor');return v}assert.deepEqual(Object.keys(v).sort(),['generalSetting','name']);return v.generalSetting}
function mutate(value){const out={...value};if(spec.cohort==='boundary'){if(spec.mutation==='omitted')delete out[spec.field];else out[spec.field]=spec.value}return out}
async function execute(){
 const info=await ok('GET','/api/instance/profile');result.instance=info;assert.equal(info.version,reg.version);assert.equal(info.commit,reg.application_commit);
 const admin=await ok('POST','/api/users',{username:'study-admin',password,role:'ADMIN'},true);assert.equal(admin.role,'ADMIN');
 let login=await ok('POST','/api/auth/signin',{passwordCredentials:{username:'study-admin',password}},true);token=login.accessToken;assert.ok(token);secrets.push(token);
 const actor=await ok('POST','/api/users',{username:'study-actor',password,role:'USER'},true);assert.equal(actor.role,'USER');
 login=await ok('POST','/api/auth/signin',{passwordCredentials:{username:'study-actor',password}},true);token=login.accessToken;assert.ok(token);secrets.push(token);assert.equal(login.user.role,'USER');assert.equal(login.user.name,'users/study-actor');result.actor={name:login.user.name,role:login.user.role};
 const initial=await ok('GET',memo?'/api/memos':path);if(memo)assert.deepEqual(initial.memos,[]);
 result.initial_business_state={actor:result.actor,version:info.version,resource:initial};
 if(!memo){await ok('PATCH',path+'?updateMask='+mask,{name,generalSetting:seed});result.initialized=project(await ok('GET',path));assert.deepEqual(result.initialized,seed)}
 const body=memo?mutate(seed):{name,generalSetting:mutate(seed)};result.producer_body=body;
 const made=await api(memo?'POST':'PATCH',memo?'/api/memos?memoId=study-control':path+'?updateMask='+mask,body);result.producer_status=made.status;
 if(made.status!==200){
  result.after_failed_producer=await ok('GET',memo?'/api/memos':path);
  const unchanged=JSON.stringify(result.after_failed_producer)===JSON.stringify(memo?initial:{name,generalSetting:result.initialized});
  result.prefix_status=[400,409,422].includes(made.status)&&unchanged?'rejected':'uncertain';result.status='observed';return;
 }
 result.prefix=project(await ok('GET',path));result.prefix_status='accepted';
 const expected={...result.prefix,[memo?'visibility':'saveMediaMetadata']:memo?'PROTECTED':true};result.expected=expected;
 const start=performance.now();
 if(a.channel==='api'){
  const body=memo?{name,...Object.fromEntries(mutable.map(k=>[k,Object.hasOwn(expected,k)?expected[k]:null]))}:{name,generalSetting:expected};
  const r=await api('PATCH',path+'?updateMask='+mask,body);result.continuation_status=r.status;
 }else{
  const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH);browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE});
  const context=await browser.newContext({locale:'en-US',colorScheme:'light'}),page=await context.newPage();page.setDefaultTimeout(20000);
  await page.goto(base+'/auth');await page.locator('#signin-username').fill('study-actor');await page.locator('#signin-password').fill(password);await page.locator('form').filter({has:page.locator('#signin-username')}).locator('button[type=submit]').click();await page.waitForURL(u=>u.pathname!='/auth');
  const target=memo?'/memos.api.MemoService/UpdateMemo':'/memos.api.UserService/UpdateUserSetting';
  const requests=[];page.on('request',req=>{if(new URL(req.url()).pathname===target&&req.method()==='POST')requests.push(req)});
  const editor=page.locator('.memo-editor-root[contenteditable="true"]');
  const open=async()=>{await page.goto(base+(memo?'/'+name:'/setting#preference'));if(memo){const card=page.locator('article');await card.waitFor();assert.equal(await card.count(),1);await card.getByRole('button',{name:'More',exact:true}).click();await page.getByRole('menuitem',{name:'Edit',exact:true}).click();await editor.waitFor()}else await page.getByRole('switch',{name:'Save media metadata',exact:true}).waitFor()};
  const snapshot=async(label)=>{
   let value={label};
   if(memo){const update=page.getByRole('button',{name:'Update',exact:true});value={...value,editor_count:await editor.count(),inner_text:await editor.innerText(),text_content:await editor.textContent(),html:await editor.innerHTML(),update_count:await update.count(),disabled:await update.isDisabled(),audience_buttons:await page.getByRole('button').filter({hasText:/^(Private|Protected|Public)$/}).allTextContents()};assert.equal(value.editor_count,1);assert.equal(value.update_count,1)}
   else{const control=page.getByRole('switch',{name:'Save media metadata',exact:true});value={...value,switch_count:await control.count(),checked:await control.getAttribute('aria-checked'),disabled:await control.isDisabled(),preference_fields:await readPreferenceFields(page,async f=>{(result.field_observations??=[]).push({label,...f});await save()})};assert.equal(value.switch_count,1)}
   result.forms.push(value);await page.screenshot({path:a.out+'/'+label+'.png',fullPage:true});await save();return value;
  };
  await open();await snapshot('loaded');
  if(memo){await page.getByRole('button',{name:'Private',exact:true}).click();await page.getByRole('menuitem',{name:'Protected Anyone signed in',exact:true}).click()}
  const before=await snapshot('before_submit'),control=memo?page.getByRole('button',{name:'Update',exact:true}):page.getByRole('switch',{name:'Save media metadata',exact:true});result.native_disabled=before.disabled;
  if(before.disabled){await control.click({force:true});await page.waitForTimeout(1500)}
  else{const pending=page.waitForResponse(r=>new URL(r.url()).pathname===target&&r.request().method()==='POST',{timeout:20000});pending.catch(()=>{});await control.click();try{await pending}catch(e){result.native_response_timeout=true}}
  for(const req of requests){const bytes=req.postDataBuffer(),response=await req.response();const raw={method:req.method(),path:target,content_type:req.headers()['content-type'],request_base64:bytes?.toString('base64'),status:response?.status()??null,response_base64:response?(await response.body()).toString('base64'):null};result.native_requests.push(raw);await save();if(bytes){try{raw.decoded=(memo?decodeMemoAudienceUpdate:decodeGeneralUpdate)(bytes,raw.content_type)}catch(e){raw.decode_error=e.message}}}
  result.final=project(await ok('GET',path));await save();
  if(!before.disabled&&result.native_requests.length===1&&result.native_requests[0].status===200){await open();await snapshot('fresh_final')}
 }
 if(!result.final)result.final=project(await ok('GET',path));result.timing.continuation_s=(performance.now()-start)/1000;
 result.additional_changes=Object.fromEntries(Object.keys(result.prefix).filter(k=>k!==(memo?'visibility':'saveMediaMetadata')&&JSON.stringify(result.prefix[k])!==JSON.stringify(result.final[k])).map(k=>[k,{before:result.prefix[k],after:result.final[k]}]));
 result.status='observed';
}
try{await execute()}catch(e){result.error={name:e.name,message:redact(e.message)};if(result.prefix_status==='accepted'&&!result.final){try{result.final=project(await ok('GET',path))}catch(readError){result.failed_final_read=redact(readError.message)}}process.exitCode=1}
finally{try{if(browser)await browser.close();result.browser_cleanup_confirmed=true}catch(e){result.browser_cleanup_confirmed=false;result.status='incomplete';process.exitCode=1}await save()}
