import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {parseArgs} from 'node:util';
import assert from 'node:assert/strict';
const {values:a}=parseArgs({options:{out:{type:'string'},arm:{type:'string'},base:{type:'string'}}});
assert.ok(['ui-ui','api-ui','api-api'].includes(a.arm));
const base=a.base;assert.match(base,/^http:\/\/172\.\d+\.\d+\.\d+:6060$/);
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
const ordinary={oidcGroupClaim:'study-readers',isAdmin:false,permissions:['permissionRead'],libraryIds:[],description:'Study description'};
const path='/api/v1/admin/oidc-group-mappings';
const result={arm:a.arm,status:'not_run',stages:[],responses:[],blocked:[],request_failures:[],page_errors:[],independent_evaluation_cases:0};
let browser,page,context;const counts={create:0,update:0};
await fs.mkdir(a.out,{recursive:true});
try{
 assert.equal(process.version,'v20.20.2');
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']});
 assert.equal(browser.version(),'151.0.7922.34');
 context=await browser.newContext({locale:'en-US',timezoneId:'UTC',viewport:{width:1500,height:1000},serviceWorkers:'block'});
 let token;
 async function req(method,p,body){
  const r=await context.request.fetch(base+p,{method,data:body,headers:token?{Authorization:'Bearer '+token}:{},timeout:20000,maxRedirects:0,maxRetries:0});
  assert.ok(r.ok(),method+' '+p+' status '+r.status());return r;
 }
 const fixture={username:'studyadmin',email:'studyadmin@example.test',name:'Study Admin',password:'StudyFixture2026!'};
 await req('POST','/api/v1/setup',fixture);
 const login=await (await req('POST','/api/v1/auth/login',{username:fixture.username,password:fixture.password})).json();
 assert.ok(login.accessToken&&login.refreshToken);token=login.accessToken;
 await req('PUT','/api/v1/settings',[
  {name:'OIDC_PROVIDER_DETAILS',value:{providerName:'Study local configuration',clientId:'study-client',issuerUri:base+'/unused-issuer',scopes:'openid profile email groups',claimMapping:{username:'preferred_username',email:'email',name:'name',groups:'groups'}}},
  {name:'OIDC_ENABLED',value:true},{name:'OIDC_GROUP_SYNC_MODE',value:'DISABLED'},{name:'OIDC_FORCE_ONLY_MODE',value:false}
 ]);
 result.stages.push('original_local_admin_and_settings');
 await context.addInitScript(({access,refresh})=>{localStorage.setItem('accessToken_Internal',access);localStorage.setItem('refreshToken_Internal',refresh);},{access:login.accessToken,refresh:login.refreshToken});
 await context.route('**/*',async route=>{
  const r=route.request(),u=new URL(r.url());let allow=u.origin===base&&['GET','HEAD'].includes(r.method());
  const kind=r.method()==='POST'&&u.pathname===path?'create':r.method()==='PUT'&&u.pathname.startsWith(path+'/')?'update':null;
  if(u.origin===base&&kind&&counts[kind]===0){counts[kind]++;allow=true;}
  if(allow)return route.continue();result.blocked.push({method:r.method(),path:u.pathname,origin:u.origin});return route.abort();
 });
 await context.routeWebSocket('**/*',ws=>{const u=new URL(ws.url());if(u.host===new URL(base).host)ws.connectToServer();else{result.blocked.push({websocket:u.origin});ws.close();}});
 page=await context.newPage();page.setDefaultTimeout(25000);
 page.on('pageerror',e=>result.page_errors.push(String(e)));
 page.on('requestfailed',r=>result.request_failures.push({method:r.method(),path:new URL(r.url()).pathname,error:r.failure()?.errorText}));
 page.on('response',r=>{if(result.responses.length<300)result.responses.push({method:r.request().method(),path:new URL(r.url()).pathname,status:r.status()});});
 const mappingUI=()=>page.locator('app-authentication-settings');
 const dialog=()=>mappingUI().locator('p-dialog');
 const save=()=>dialog().locator('p-button[icon="pi pi-check"] button');
 async function openSettings(){await page.goto(base+'/settings',{waitUntil:'domcontentloaded'});await page.locator('p-tab').filter({has:page.locator('i.pi-lock')}).click();await mappingUI().waitFor({state:'visible'});}
 if(a.arm==='ui-ui'){
  await openSettings();await mappingUI().locator('p-button[icon="pi pi-plus"] button').click();
  await page.locator('#gmGroupClaim').fill(ordinary.oidcGroupClaim);await page.locator('#gmDescription').fill(ordinary.description);
  await page.screenshot({path:a.out+'/before-create.png'});
  const [r]=await Promise.all([page.waitForResponse(r=>new URL(r.url()).pathname===path&&r.request().method()==='POST'),save().click()]);
  result.producer={status:r.status(),body:r.request().postDataJSON()};assert.ok(r.ok());assert.deepEqual(result.producer.body,ordinary);
 }else{counts.create++;const r=await req('POST',path,ordinary);result.producer={status:r.status(),body:ordinary};}
 async function readOne(id){const all=await (await req('GET',path)).json();assert.ok(Array.isArray(all));const matches=all.filter(x=>id==null?x.oidcGroupClaim===ordinary.oidcGroupClaim:x.id===id);assert.equal(matches.length,1);return matches[0];}
 const raw=await readOne();assert.ok(raw.id!=null);for(const [k,v] of Object.entries(ordinary))assert.deepEqual(raw[k],v);result.after_create=raw;result.stages.push('mapping_persisted');
 const update={...raw,description:'Edited description',permissions:['permissionRead'],libraryIds:[]};
 if(a.arm!=='api-api'){
  await openSettings();await mappingUI().locator('tr').filter({hasText:ordinary.oidcGroupClaim}).locator('p-button[icon="pi pi-pencil"] button').click();
  assert.equal(await page.locator('#gmGroupClaim').inputValue(),ordinary.oidcGroupClaim);assert.equal(await page.locator('#gmDescription').inputValue(),ordinary.description);
  await page.locator('#gmDescription').fill('Edited description');assert.equal(await save().isEnabled(),true);await page.screenshot({path:a.out+'/before-edit.png'});
  const [r]=await Promise.all([page.waitForResponse(r=>new URL(r.url()).pathname===path+'/'+raw.id&&r.request().method()==='PUT'),save().click()]);
  result.consumer={status:r.status(),body:r.request().postDataJSON()};assert.ok(r.ok());assert.deepEqual(result.consumer.body,update);
 }else{counts.update++;const r=await req('PUT',path+'/'+raw.id,update);result.consumer={status:r.status(),body:update};}
 result.after_edit=await readOne(raw.id);assert.deepEqual(result.after_edit,update);result.stages.push('edit_persisted');result.status='qualified';
}catch(e){result.status='failed';result.error=String(e);result.error_type=e.name;}
finally{
 result.write_counts=counts;
 if(page){result.final_url=page.url();try{await page.screenshot({path:a.out+'/final.png',timeout:5000});}catch(e){result.screenshot_error=String(e);}}
 if(browser)await browser.close();await fs.writeFile(a.out+'/control.json',JSON.stringify(result,null,2)+'\n');
}
if(result.status!=='qualified')process.exitCode=1;
