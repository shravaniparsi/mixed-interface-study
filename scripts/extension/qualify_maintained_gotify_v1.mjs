import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import {parseArgs} from 'node:util';
import assert from 'node:assert/strict';
const {values:a}=parseArgs({options:{out:{type:'string'},arm:{type:'string'},base:{type:'string'},fixture:{type:'string'},database:{type:'string'}}});
assert.ok(['ui-ui','producer','api','ui'].includes(a.arm));
assert.equal(a.base,'http://172.30.79.2');
const base=a.base, ordinary={name:'Study application',description:'Study description',defaultPriority:0};
const editedName='Study application edited';
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
const result={arm:a.arm,status:'unavailable',scientific_cases:0,mutations:[],native_mutations:[],blocked:[],page_errors:[]};
let browser,context,page;
await fs.mkdir(a.out,{recursive:true});
const write=async(name,data)=>fs.writeFile(`${a.out}/${name}.json`,JSON.stringify(data,null,2)+'\n');
const dbState=()=>JSON.parse(execFileSync('python3',['scripts/extension/gotify_state_v1.py',a.database],{encoding:'utf8',timeout:10000}));
try {
 assert.equal(process.version,'v20.20.2');
 const fixture=a.fixture?JSON.parse(await fs.readFile(a.fixture,'utf8')):null;
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']});
 assert.equal(browser.version(),'151.0.7922.34');
 context=await browser.newContext({storageState:fixture?.storage,locale:'en-US',timezoneId:'UTC',viewport:{width:1500,height:1000},serviceWorkers:'block'});
 async function request(method,path,body,extra={}) {
  assert.ok(path.startsWith('/')&&!path.startsWith('//'));
  const r=await context.request.fetch(base+path,{method,data:body,headers:{Origin:base,...extra},timeout:15000,maxRedirects:0,maxRetries:0});
  const raw=await r.text();
  let data; try {data=JSON.parse(raw);} catch {data=raw;}
  if(!['GET','HEAD'].includes(method))result.mutations.push({channel:'api',method,path,body,status:r.status(),response:data});
  assert.ok(r.ok(),`${method} ${path}: ${r.status()}`);
  return data;
 }
 if(!fixture)await request('POST','/auth/local/login',{name:'Study browser session'},{Authorization:'Basic '+Buffer.from('studyadmin:StudyFixture2026!').toString('base64')});
 const actor=await request('GET','/current/user');
 result.actor=actor;
 assert.equal(actor.name,'studyadmin');assert.equal(actor.admin,true);
 if(fixture)assert.deepEqual(actor,fixture.actor);
 page=await context.newPage();
 page.on('pageerror',e=>result.page_errors.push(String(e)));
 await context.route('**/*',async route=>{
  const r=route.request(),u=new URL(r.url());
  const read=['GET','HEAD'].includes(r.method());
  const allowed=u.origin===base&&(read||(r.method()==='POST'&&u.pathname==='/application'&&a.arm==='ui-ui')||(r.method()==='PUT'&&/^\/application\/\d+$/.test(u.pathname)&&['ui-ui','ui'].includes(a.arm)));
  if(!allowed){result.blocked.push({method:r.method(),url:r.url()});return route.abort();}
  return route.continue();
 });
 await context.routeWebSocket('**/*',ws=>{
  if(new URL(ws.url()).host===new URL(base).host)ws.connectToServer();
  else {result.blocked.push({websocket:ws.url()});ws.close();}
 });
 const nativeMutations=result.native_mutations;
 page.on('request',r=>{if(!['GET','HEAD'].includes(r.method()))nativeMutations.push({method:r.method(),path:new URL(r.url()).pathname,body:r.postDataJSON()});});
 async function applications(){
  await page.goto(base,{waitUntil:'domcontentloaded',timeout:20000});
  if(!await page.locator('#create-app').isVisible())await page.getByRole('link',{name:'Applications',exact:true}).click();
  await page.locator('#create-app').waitFor({state:'visible',timeout:15000});
 }
 async function readTarget(id){const all=await request('GET','/application');const found=all.filter(x=>x.id===id);assert.equal(found.length,1);return found[0];}
 async function nativeEdit(target){
  const row=page.locator('#app-table tbody tr').filter({has:page.getByRole('cell',{name:target.name,exact:true})});
  assert.equal(await row.count(),1);
  await row.locator('button.edit').click();
  await page.locator('#app-dialog .name input').fill(editedName);
  const responsePromise=page.waitForResponse(r=>new URL(r.url()).pathname===`/application/${target.id}`&&r.request().method()==='PUT',{timeout:15000});
  await page.locator('#app-dialog button.update').click();
  const r=await responsePromise;assert.ok(r.ok());
  await page.locator('#app-dialog').waitFor({state:'hidden',timeout:15000});
 }
 let target;
 if(a.arm==='ui-ui'){
  await applications();await page.locator('#create-app').click();
  await page.locator('#app-dialog .name input').fill(ordinary.name);
  await page.locator('#app-dialog .description textarea').first().fill(ordinary.description);
  const responsePromise=page.waitForResponse(r=>new URL(r.url()).pathname==='/application'&&r.request().method()==='POST',{timeout:15000});
  await page.locator('#app-dialog button.create').click();
  const r=await responsePromise;assert.ok(r.ok());const created=await r.json();
  // Reload closes the token display through navigation, without guessing an
  // uninspected modal selector or mutating any resource.
  await applications();target=await readTarget(created.id);
  assert.deepEqual(nativeMutations.filter(x=>x.method==='POST').map(x=>x.body),[ordinary]);
 } else if(a.arm==='producer'){
  const created=await request('POST','/application',ordinary);
  target=await readTarget(created.id);
  await write('fixture',{actor,target,storage:await context.storageState()});
 } else {
  target=await readTarget(fixture.target.id);assert.deepEqual(target,fixture.target);
  if(a.arm==='ui')await applications();
  const before=dbState();await write('pre-edit-database',before);
  const expected=JSON.parse(await fs.readFile(`${a.fixture}.database.json`,'utf8'));
  assert.deepEqual(before,expected,'Database drift before continuation');
  assert.deepEqual(await readTarget(target.id),fixture.target,'Target changed during navigation');
 }
 if(a.arm!=='producer'){
  const {id,...payload}=target;payload.name=editedName;
  if(a.arm==='api')await request('PUT',`/application/${id}`,payload);
  else {
   await nativeEdit(target);
   const updates=nativeMutations.filter(x=>x.method==='PUT');assert.equal(updates.length,1);
   assert.deepEqual(updates[0],{method:'PUT',path:`/application/${id}`,body:payload},'Native/API serializer mismatch');
  }
  const after=await readTarget(id);await write('readback',{before:target,after});
  assert.deepEqual(after,{...target,name:editedName},'Edit did not preserve unrelated state');
 }
 assert.deepEqual(result.blocked,[]);assert.deepEqual(result.page_errors,[]);
 result.native_mutations=nativeMutations;result.status='qualified';
} catch(e){result.error=String(e);if(page)await page.screenshot({path:`${a.out}/failure.png`,fullPage:true}).catch(()=>{});}
finally{if(browser)await browser.close();await write('control',result);}
process.exitCode=result.status==='qualified'?0:1;
