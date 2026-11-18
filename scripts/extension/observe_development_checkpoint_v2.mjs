import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {parseArgs} from 'node:util';
import assert from 'node:assert/strict';
const {values:a}=parseArgs({options:{out:{type:'string'},phase:{type:'string'}}});
assert.ok(['seed','restore1','restore2'].includes(a.phase));
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
const base='http://127.0.0.1:8080',path='/api/admin/users',login='studycontrol';
const expected={id:null,login,firstName:'Study',lastName:'Control',email:'studycontrol@example.com',activated:true,langKey:'en',authorities:['ROLE_USER']};
const result={phase:a.phase,status:'failed',blocked:[],write_counts:{authenticate:0,create:0}};
let browser,token;
try {
 assert.equal(process.version,'v20.20.2');
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']});
 assert.equal(browser.version(),'151.0.7922.34');
 const context=await browser.newContext({locale:'en-US',timezoneId:'UTC',viewport:{width:1280,height:900},serviceWorkers:'block'});
 await context.route('**/*',async route=>{
  const r=route.request(),u=new URL(r.url());
  let allow=u.origin===base&&['GET','HEAD'].includes(r.method());
  if(u.origin===base&&u.pathname==='/api/authenticate'&&r.method()==='POST'&&result.write_counts.authenticate===0){result.write_counts.authenticate++;allow=true;}
  if(allow)return route.continue();
  result.blocked.push({method:r.method(),origin:u.origin,path:u.pathname});return route.abort();
 });
 const page=await context.newPage();page.setDefaultTimeout(20000);
 await page.goto(base+'/',{waitUntil:'domcontentloaded'});
 await page.locator('[data-cy="accountMenu"]').click();await page.locator('[data-cy="login"]').click();
 await page.locator('[data-cy="username"]').fill('admin');await page.locator('[data-cy="password"]').fill('admin');
 const [auth,account]=await Promise.all([page.waitForResponse(r=>new URL(r.url()).pathname==='/api/authenticate'&&r.request().method()==='POST'),page.waitForResponse(r=>new URL(r.url()).pathname==='/api/account'&&r.status()===200),page.locator('[data-cy="submit"]').click()]);
 assert.equal(auth.status(),200);const who=await account.json();assert.equal(who.login,'admin');assert.ok(who.authorities.includes('ROLE_ADMIN'));
 result.actor={login:who.login,authorities:who.authorities};
 token=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('jhi-authenticationToken')||localStorage.getItem('jhi-authenticationToken')));
 assert.equal(typeof token,'string');
 if(a.phase==='seed'){
  result.write_counts.create++;
  const r=await context.request.post(base+path,{headers:{Authorization:'Bearer '+token},data:expected,timeout:15000,maxRedirects:0});
  result.producer_status=r.status();assert.equal(r.status(),201);
 }
 const r=await context.request.get(base+path+'/'+login,{headers:{Authorization:'Bearer '+token},timeout:15000,maxRedirects:0});assert.equal(r.status(),200);
 const record=await r.json();
 const allowed=new Set([...Object.keys(expected),'imageUrl','createdBy','createdDate','lastModifiedBy','lastModifiedDate']);
 result.record_keys=Object.keys(record).sort();assert.ok(Object.keys(record).every(k=>allowed.has(k)),'Unexpected DTO keys: do not archive values');
 assert.ok(record.id!==null&&record.id!==undefined);
 for(const [k,v] of Object.entries(expected))if(k!=='id')assert.deepEqual(record[k],v);
 result.record=record;
 await page.goto(base+'/admin/user-management/'+login+'/edit',{waitUntil:'domcontentloaded'});
 await page.locator('input[name="login"]').waitFor({state:'visible'});
 const loaded={};for(const f of ['login','firstName','lastName','email']){loaded[f]=await page.locator('input[name="'+f+'"]').inputValue();assert.equal(loaded[f],expected[f]);}
 loaded.activated=await page.locator('input[name="activated"]').isChecked();assert.equal(loaded.activated,true);
 loaded.langKey=await page.locator('select[name="langKey"]').inputValue();assert.equal(loaded.langKey,'en');
 loaded.authorities=await page.locator('select[name="authority"]').evaluate(el=>Array.from(el.selectedOptions).map(o=>o.textContent.trim()));assert.deepEqual(loaded.authorities,['ROLE_USER']);
 result.loaded=loaded;result.save_enabled=await page.locator('form[name="editForm"] button[type="submit"]').isEnabled();assert.equal(result.save_enabled,true);
 await page.screenshot({path:a.out+'/'+a.phase+'.png'});
 assert.ok(result.blocked.every(r=>r.method==='GET'&&r.origin==='https://fonts.googleapis.com'&&r.path==='/css2'),'Unexpected blocked request');result.status='observed';
} catch(e){result.error_type=e.name;result.error=String(e);}
finally{token=null;if(browser)await browser.close();await fs.writeFile(a.out+'/'+a.phase+'-browser.json',JSON.stringify(result,null,2)+'\n');}
if(result.status!=='observed')process.exitCode=1;
