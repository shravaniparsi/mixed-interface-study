import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {parseArgs} from 'node:util';
import {decodeMemoAudienceUpdate} from './memos_memo_wire_v1.mjs';
const {values:a}=parseArgs({options:{registry:{type:'string'},workflow:{type:'string'},channel:{type:'string'},out:{type:'string'}}});
const reg=JSON.parse(await readFile(a.registry,'utf8'));assert.equal(a.workflow,'memo');assert.ok(['api','ui'].includes(a.channel));
const base='http://127.0.0.1:18080',password=process.env.STUDY_EPHEMERAL_PASSWORD,secrets=[password];assert.ok(password);
const result={kind:'memos_memo_control_v1',channel:a.channel,status:'incomplete',requests:[],forms:[]};await mkdir(a.out,{recursive:true});
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
const name='memos/study-control',path='/api/'+name;
const seed={content:'Ordinary memo',visibility:'PRIVATE',createTime:'2026-01-01T00:00:00Z',updateTime:'2026-01-01T00:00:00Z'};
const allMask='content,visibility,space,pinned,state,create_time,update_time,location,attachments,relations';
const mutable=['content','visibility','space','pinned','state','createTime','updateTime','location','attachments','relations'];
function project(v){assert.equal(v.name,name);assert.equal(v.creator,'users/study-actor');return v}
try {
 const info=await api('GET','/api/instance/profile');result.instance=info;assert.equal(info.version,reg.version);
 const admin=await api('POST','/api/users',{username:'study-admin',password,role:'ADMIN'},true);assert.equal(admin.role,'ADMIN');
 let login=await api('POST','/api/auth/signin',{passwordCredentials:{username:'study-admin',password}},true);token=login.accessToken;assert.ok(token);secrets.push(token);
 const actor=await api('POST','/api/users',{username:'study-actor',password,role:'USER'},true);assert.equal(actor.role,'USER');
 login=await api('POST','/api/auth/signin',{passwordCredentials:{username:'study-actor',password}},true);token=login.accessToken;assert.ok(token);secrets.push(token);
 assert.equal(login.user.role,'USER');assert.equal(login.user.name,'users/study-actor');result.actor={name:login.user.name,role:login.user.role};
 const initial=await api('GET','/api/memos');assert.deepEqual(initial.memos,[]);result.initial_business_state={actor:result.actor,memos:initial,version:info.version};
 await api('POST','/api/memos?memoId=study-control',seed);
 result.prefix=project(await api('GET',path));for(const [k,v] of Object.entries(seed))assert.deepEqual(result.prefix[k],v);assert.equal(result.prefix.state,'NORMAL');
 const expected={...result.prefix,visibility:'PROTECTED'};
 if(a.channel==='api'){
  const body={name,...Object.fromEntries(mutable.map(k=>[k,Object.hasOwn(expected,k)?expected[k]:null]))};
  await api('PATCH',path+'?updateMask='+allMask,body);
 }else{
  const require=createRequire(import.meta.url);const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH);browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE});
  const context=await browser.newContext({locale:'en-US',colorScheme:'light'}),page=await context.newPage();page.setDefaultTimeout(20000);
  await page.goto(base+'/auth');await page.locator('#signin-username').fill('study-actor');await page.locator('#signin-password').fill(password);await page.locator('form').filter({has:page.locator('#signin-username')}).locator('button[type=submit]').click();await page.waitForURL(u=>u.pathname!='/auth');
  const card=page.locator('article').filter({has:page.getByText('Ordinary memo',{exact:true})});
  const editor=page.locator('.memo-editor-root[contenteditable="true"]');
  const open=async()=>{await page.goto(base+'/'+name);await card.waitFor();assert.equal(await card.count(),1);await card.getByRole('button',{name:'More',exact:true}).click();await page.getByRole('menuitem',{name:'Edit',exact:true}).click();await editor.waitFor();};
  const snapshot=async(label,audience)=>{const update=page.getByRole('button',{name:'Update',exact:true}),trigger=page.getByRole('button',{name:audience,exact:true});const v={label,editor_count:await editor.count(),content:await editor.innerText(),audience_count:await trigger.count(),audience,update_count:await update.count(),disabled:await update.isDisabled()};result.forms.push(v);await page.screenshot({path:a.out+'/'+label+'.png',fullPage:true});await save();assert.equal(v.editor_count,1);assert.equal(v.content,seed.content);assert.equal(v.audience_count,1);assert.equal(v.update_count,1);assert.equal(v.disabled,false);};
  await open();await snapshot('loaded','Private');
  await page.getByRole('button',{name:'Private',exact:true}).click();await page.getByRole('menuitem',{name:'Protected Anyone signed in',exact:true}).click();await snapshot('before_submit','Protected');
  const pending=page.waitForResponse(r=>new URL(r.url()).pathname==='/memos.api.MemoService/UpdateMemo'&&r.request().method()==='POST');pending.catch(()=>{});
  await page.getByRole('button',{name:'Update',exact:true}).click();const response=await pending,req=response.request(),bytes=req.postDataBuffer();assert.ok(bytes);
  const raw={method:req.method(),path:new URL(req.url()).pathname,content_type:req.headers()['content-type'],request_base64:bytes.toString('base64'),status:response.status(),response_base64:(await response.body()).toString('base64')};result.native_request=raw;await save();
  raw.decoded=decodeMemoAudienceUpdate(bytes,raw.content_type);await save();assert.equal(response.status(),200);assert.deepEqual(raw.decoded,{memo:{name,content:seed.content,visibility:2},updateMask:{paths:['visibility']}});
  await open();await snapshot('fresh_final','Protected');
 }
 result.final=project(await api('GET',path));assert.deepEqual(result.final,expected);result.status='ordinary_control_passed';
}catch(e){result.error={name:e.name,message:redact(e.message)};process.exitCode=1}
finally{try{if(browser)await browser.close();result.browser_cleanup_confirmed=true}catch(e){result.browser_cleanup_confirmed=false;result.status='incomplete';process.exitCode=1}await save()}
