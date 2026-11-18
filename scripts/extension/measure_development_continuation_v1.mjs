import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {parseArgs} from 'node:util';
import assert from 'node:assert/strict';
const {values:a}=parseArgs({options:{out:{type:'string'},phase:{type:'string'}}});
assert.ok(['warm','seed','native','api'].includes(a.phase));
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
const base='http://127.0.0.1:8080',path='/api/admin/users',login='studycontrol';
const expected={id:null,login,firstName:'Study',lastName:'Control',email:'studycontrol@example.com',activated:true,langKey:'en',authorities:['ROLE_USER']};
const result={phase:a.phase,status:'failed',blocked:[],write_counts:{authenticate:0,create:0,update:0}};
const allowed=new Set([...Object.keys(expected),'imageUrl','createdBy','createdDate','lastModifiedBy','lastModifiedDate']);
let browser,token;
const canonical=value=>Array.isArray(value)?value.map(canonical):value!==null&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])])):value;
try {
 assert.equal(process.version,'v20.20.2');
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']});
 assert.equal(browser.version(),'151.0.7922.34');
 const context=await browser.newContext({locale:'en-US',timezoneId:'UTC',viewport:{width:1280,height:900},serviceWorkers:'block'});
 await context.route('**/*',async route=>{
  const r=route.request(),u=new URL(r.url());let allow=u.origin===base&&['GET','HEAD'].includes(r.method());
  if(u.origin===base&&u.pathname==='/api/authenticate'&&r.method()==='POST'&&result.write_counts.authenticate===0){result.write_counts.authenticate++;allow=true;}
  if(['warm','native'].includes(a.phase)&&u.origin===base&&u.pathname===path&&r.method()==='PUT'&&result.write_counts.update===0){result.write_counts.update++;allow=true;}
  if(allow)return route.continue();result.blocked.push({method:r.method(),origin:u.origin,path:u.pathname});return route.abort();
 });
 const page=await context.newPage();page.setDefaultTimeout(20000);
 await page.goto(base+'/',{waitUntil:'domcontentloaded'});
 await page.locator('[data-cy="accountMenu"]').click();await page.locator('[data-cy="login"]').click();
 await page.locator('[data-cy="username"]').fill('admin');await page.locator('[data-cy="password"]').fill('admin');
 const [auth,account]=await Promise.all([page.waitForResponse(r=>new URL(r.url()).pathname==='/api/authenticate'&&r.request().method()==='POST'),page.waitForResponse(r=>new URL(r.url()).pathname==='/api/account'&&r.status()===200),page.locator('[data-cy="submit"]').click()]);
 assert.equal(auth.status(),200);const who=await account.json();assert.equal(who.login,'admin');assert.ok(who.authorities.includes('ROLE_ADMIN'));
 result.actor={login:who.login,authorities:who.authorities};
 token=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('jhi-authenticationToken')||localStorage.getItem('jhi-authenticationToken')));assert.equal(typeof token,'string');
 const headers={Authorization:'Bearer '+token};
 async function readback(){
  const r=await context.request.get(base+path+'/'+login,{headers,timeout:15000,maxRedirects:0});assert.equal(r.status(),200);
  const data=await r.json();assert.ok(Object.keys(data).every(k=>allowed.has(k)),'Unexpected DTO keys; values withheld');return data;
 }
 async function search(){
  const refresh=await context.request.post('http://127.0.0.1:9200/_refresh',{timeout:30000,maxRedirects:0});assert.equal(refresh.status(),200);assert.equal((await refresh.json())._shards.failed,0);
  const r=await context.request.post('http://127.0.0.1:9200/_search',{data:{size:1000,track_total_hits:true,query:{match_all:{}}},timeout:30000,maxRedirects:0});assert.equal(r.status(),200);
  const raw=await r.body();assert.ok(raw.length<=8*1024*1024);const data=JSON.parse(raw);
  assert.equal(data._shards.failed,0);assert.equal(data.hits.total.relation,'eq');assert.equal(data.hits.total.value,data.hits.hits.length);
  const docs=data.hits.hits.map(h=>({index:h._index,id:h._id,source:h._source})).sort((a,b)=>a.index<b.index?-1:a.index>b.index?1:a.id<b.id?-1:a.id>b.id?1:0);
  return {documents:docs.length,canonicalization:'sorted-object-keys-and-index-id; JS JSON numbers; arrays ordered',sha256:createHash('sha256').update(JSON.stringify(canonical(docs))).digest('hex')};
 }
 if(['warm','seed'].includes(a.phase)){
  result.write_counts.create++;const r=await context.request.post(base+path,{headers,data:expected,timeout:15000,maxRedirects:0});result.producer_status=r.status();assert.equal(r.status(),201);
 }
 const record=await readback();assert.ok(record.id!==null&&record.id!==undefined);
 for(const [k,v] of Object.entries(expected))if(k!=='id')assert.deepEqual(record[k],v);
 result.record=record;
 if(['native','api'].includes(a.phase)){const seed=JSON.parse(await fs.readFile(a.out+'/seed-browser.json','utf8'));assert.equal(seed.status,'observed');assert.deepEqual(record,seed.record);assert.deepEqual(result.actor,seed.actor);result.seed_record_gate_passed=true;}
 if(a.phase!=='api'){
  await page.goto(base+'/admin/user-management/'+login+'/edit',{waitUntil:'domcontentloaded'});
  await page.locator('input[name="login"]').waitFor({state:'visible'});
  const loaded={};for(const f of ['login','firstName','lastName','email']){loaded[f]=await page.locator('input[name="'+f+'"]').inputValue();assert.equal(loaded[f],expected[f]);}
  loaded.activated=await page.locator('input[name="activated"]').isChecked();assert.equal(loaded.activated,true);
  loaded.langKey=await page.locator('select[name="langKey"]').inputValue();assert.equal(loaded.langKey,'en');
  loaded.authorities=await page.locator('select[name="authority"]').evaluate(el=>Array.from(el.selectedOptions).map(o=>o.textContent.trim()));assert.deepEqual(loaded.authorities,['ROLE_USER']);
  result.loaded=loaded;result.save_enabled=await page.locator('form[name="editForm"] button[type="submit"]').isEnabled();assert.equal(result.save_enabled,true);
  await page.screenshot({path:a.out+'/'+a.phase+'-before.png'});
 }
 result.search_before=await search();
 if(a.phase!=='seed'){
  const expectedUpdate={...expected,id:record.id,firstName:'Edited'};
  if(a.phase==='api'){
   const reference=JSON.parse(await fs.readFile(a.out+'/native-browser.json','utf8'));
   assert.equal(reference.status,'observed');assert.deepEqual(record,reference.record);assert.deepEqual(result.actor,reference.actor);assert.deepEqual(result.search_before,reference.search_before);
   assert.deepEqual(reference.consumer.body,expectedUpdate);
   result.matched_start_gate_passed=true;result.write_counts.update++;
   const r=await context.request.put(base+path,{headers,data:reference.consumer.body,timeout:15000,maxRedirects:0});result.consumer={status:r.status(),body:reference.consumer.body,route:'api'};
  }else{
   await page.locator('input[name="firstName"]').fill('Edited');const save=page.locator('form[name="editForm"] button[type="submit"]');assert.equal(await save.isEnabled(),true);
   const [r]=await Promise.all([page.waitForResponse(r=>new URL(r.url()).pathname===path&&r.request().method()==='PUT'),save.click()]);
   result.consumer={status:r.status(),body:r.request().postDataJSON(),route:'native'};
  }
  assert.deepEqual(result.consumer.body,expectedUpdate);assert.equal(result.consumer.status,200);
  const final=await readback();result.after_edit=final;
  const expectedFinal={...record,firstName:'Edited',lastModifiedDate:final.lastModifiedDate};assert.deepEqual(final,expectedFinal);
  assert.ok(Number.isFinite(Date.parse(final.lastModifiedDate))&&Date.parse(final.lastModifiedDate)>=Date.parse(record.lastModifiedDate),'Audit time must not move backwards at millisecond precision');
  result.search_after=await search();
 }
 assert.ok(result.blocked.every(r=>r.method==='GET'&&r.origin==='https://fonts.googleapis.com'&&r.path==='/css2'),'Unexpected blocked request');result.status='observed';
}catch(e){result.error_type=e.name;result.error=String(e);}
finally{token=null;if(browser)await browser.close();await fs.writeFile(a.out+'/'+a.phase+'-browser.json',JSON.stringify(result,null,2)+'\n');}
if(result.status!=='observed')process.exitCode=1;
