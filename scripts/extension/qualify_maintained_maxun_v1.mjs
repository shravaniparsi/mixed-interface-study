// Prepared ordinary controls only; separate deployment/execution freeze required.
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import {parseArgs} from 'node:util';
import assert from 'node:assert/strict';
import {ORDINARY, EDIT, nativeLogin, nativeCreate, openNativeEdit, nativeEdit} from './maxun_native_controls_v1.mjs';
import {crawlEditBody, sameState} from './maxun_serializer_v1.mjs';
import {captureBrowserState, restoreBrowserState} from './maxun_browser_state_v1.mjs';
import {applicationState, assertSameApplicationState, assertOrdinaryEdit} from './maxun_comparison_v1.mjs';

const {values:a}=parseArgs({options:{out:{type:'string'},arm:{type:'string'},fixture:{type:'string'}}});
assert.equal(process.env.GITHUB_ACTIONS,'true');
assert.ok(['ui-ui','producer','api','ui'].includes(a.arm));
assert.equal(['api','ui'].includes(a.arm),Boolean(a.fixture),'Fixture required only for restored branches');
const frontend='http://localhost:5173',backend='http://localhost:8080';
const credentials={email:'study@example.test',password:'StudyFixture2026!'};
const result={arm:a.arm,status:'unavailable',scientific_cases:0,traces:[],blocked:[],page_errors:[]};
await fs.mkdir(a.out); // Refuse overwrite/repeated arm.
const write=(name,value)=>fs.writeFile(`${a.out}/${name}.json`,JSON.stringify(value,null,2)+'\n');
const record=async trace=>{result.traces.push(trace);await write('control',result);};
const remaining=()=>Math.max(1,Math.min(30000,Number(process.env.STUDY_JOB_DEADLINE)*1000-Date.now()));
const state=()=>JSON.parse(execFileSync('python3',['scripts/extension/maxun_postgres_state_v1.py','--container','study-maxun-postgres'],{encoding:'utf8',timeout:remaining(),maxBuffer:64*1024*1024}));
let browser,context,page;
try {
 const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']});
 result.browser_version=browser.version();result.node_version=process.version;
 const fixture=a.fixture?JSON.parse(await fs.readFile(a.fixture,'utf8')):null;
 const options={locale:'en-US',timezoneId:'UTC',viewport:{width:1500,height:1000},serviceWorkers:'block'};
 if(fixture) ({context,page}=await restoreBrowserState(browser,fixture.browser,options));
 else {context=await browser.newContext(options);page=await context.newPage();}
 context.setDefaultTimeout(15000);context.setDefaultNavigationTimeout(30000);
 await context.route('**/*',async route=>{
  const request=route.request(),url=new URL(request.url());
  const runMutation=!['GET','HEAD','OPTIONS'].includes(request.method()) && /\/(?:runs|run|schedule)(?:\/|$)/.test(url.pathname);
  const allowed=[frontend,backend].includes(url.origin) && !runMutation;
  if(!allowed){result.blocked.push({url:request.url(),method:request.method()});await route.abort();return;}
  await route.continue();
 });
 page.on('pageerror',error=>result.page_errors.push(String(error)));
 async function request(method,path,body){
  assert.ok(path.startsWith('/')&&!path.startsWith('//'));
  const response=await context.request.fetch(backend+path,{method,data:body,headers:{Origin:frontend},timeout:remaining(),maxRetries:0,maxRedirects:0});
  const raw=await response.text();let data;try{data=JSON.parse(raw);}catch{data=raw;}
  await record({kind:'api',method,path,body,status:response.status(),response:data});
  assert.ok(response.ok(),`${method} ${path}: ${response.status()}`);return data;
 }
 if(!fixture){await request('POST','/auth/register',credentials);await nativeLogin(page,frontend,credentials);}
 const actor=await request('GET','/auth/current-user');assert.equal(actor.ok,true);
 if(fixture)assert.ok(sameState(actor,fixture.actor),'Restored actor differs');
 let id=fixture?.id;
 if(a.arm==='ui-ui') id=await nativeCreate(page,frontend,backend,record);
 if(a.arm==='producer'){
  const created=await request('POST','/storage/recordings/crawl',ORDINARY);id=created.robot?.recording_meta?.id;
 }
 assert.match(id,/^[a-f0-9-]+$/i);
 let target=await request('GET','/storage/recordings/'+id);
 assert.equal(target.userId,actor.user.id,'Target belongs to different actor');
 assert.equal(target.recording_meta.id,id);
 const before=state();applicationState(before);
 await write('before-database',before);await write('before-readback',target);
 if(a.arm==='producer'){
  await page.goto(frontend+'/robots',{waitUntil:'domcontentloaded'});
  await page.getByRole('row').filter({has:page.getByText(target.recording_meta.name,{exact:true})}).first().waitFor({state:'visible'});
  assertSameApplicationState(before,state());
  const checkpoint=await captureBrowserState(context,page,frontend);
  await write('fixture',{id,target,actor,database:before,browser:checkpoint});
  result.status='producer_prepared';
 }else{
  if(fixture){assertSameApplicationState(fixture.database,before);assert.ok(sameState(fixture.target,target),'Restored readback differs');}
  if(a.arm==='ui'||a.arm==='ui-ui'){
   await openNativeEdit(page,frontend,target);
   const afterNavigation=state();await write('navigation-database',afterNavigation);
   assertSameApplicationState(before,afterNavigation);
   const navigatedTarget=await request('GET','/storage/recordings/'+id);
   assert.ok(sameState(target,navigatedTarget),'Native navigation changes target readback');
   if(fixture){const observed=await captureBrowserState(context,page,frontend);assert.ok(sameState(observed.storage,fixture.browser.storage)&&sameState(observed.session,fixture.browser.session),'Native navigation changes actor browser state');}
   await nativeEdit(page,backend,target,record);
  }else await request('PUT','/storage/recordings/'+id,crawlEditBody(target,EDIT.field,EDIT.value));
  const after=await request('GET','/storage/recordings/'+id),afterDatabase=state();
  await write('after-readback',after);await write('after-database',afterDatabase);
  assert.equal(after.recording_meta.name,EDIT.value);
  assertOrdinaryEdit(before,afterDatabase,id,EDIT.value);
  result.status='ordinary_arm_passed';
 }
 assert.equal(result.blocked.length,0,'Blocked external or run request during ordinary control');
 assert.equal(result.page_errors.length,0,'Native page error during ordinary control');
}catch(error){result.status='unavailable';result.error={name:error.name,message:error.message};
 if(page)await page.screenshot({path:`${a.out}/failure.png`,fullPage:true}).catch(()=>{});
}finally{
 await write('control',result);
 if(context)await context.close().catch(()=>{});
 if(browser)await browser.close().catch(()=>{});
}
if(result.status==='unavailable')process.exitCode=1;
