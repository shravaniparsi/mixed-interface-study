import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {parseArgs} from 'node:util';
const {values:a}=parseArgs({options:{out:{type:'string'}}});
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
const base='http://127.0.0.1:8080';
const result={kind:'original_ui_login_control',status:'not_run',responses:[],blocked:[],request_failures:[],console_errors:[],page_errors:[],authentication_posts:0,business_object_writes:0,independent_evaluation_cases:0};
await fs.mkdir(a.out,{recursive:true});let browser,page;
try{
 if(process.version!=='v20.20.2')throw Error('Node version mismatch');
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']});
 result.node=process.version;result.browser_version=browser.version();
 if(result.browser_version!=='151.0.7922.34')throw Error('Browser version mismatch');
 const context=await browser.newContext({locale:'en-US',timezoneId:'UTC',viewport:{width:1280,height:900},serviceWorkers:'block'});
 await context.route('**/*',async route=>{
  const r=route.request(),u=new URL(r.url());const local=u.origin===base;
  let allow=local&&['GET','HEAD'].includes(r.method());
  if(local&&r.method()==='POST'&&u.pathname==='/api/authenticate'&&result.authentication_posts===0){allow=true;result.authentication_posts++;}
  if(allow)return route.continue();
  result.blocked.push({method:r.method(),origin:u.origin,path:u.pathname});return route.abort();
 });
 page=await context.newPage();page.setDefaultTimeout(20000);
 page.on('response',r=>{if(result.responses.length<200)result.responses.push({path:new URL(r.url()).pathname,status:r.status(),method:r.request().method()});});
 page.on('requestfailed',r=>{if(result.request_failures.length<100)result.request_failures.push({path:new URL(r.url()).pathname,error:r.failure()?.errorText});});
 page.on('console',m=>{if(m.type()==='error'&&result.console_errors.length<100)result.console_errors.push(m.text().slice(0,1000));});
 page.on('pageerror',e=>{if(result.page_errors.length<100)result.page_errors.push(String(e).slice(0,1000));});
 const root=await page.goto(base+'/',{waitUntil:'domcontentloaded',timeout:30000});result.root_status=root.status();
 await page.screenshot({path:a.out+'/before-login.png'});
 await page.locator('[data-cy="accountMenu"]').click();
 await page.locator('[data-cy="login"]').click();
 await page.locator('[data-cy="username"]').fill('user');
 await page.locator('[data-cy="password"]').fill('user');
 const [auth,account]=await Promise.all([
  page.waitForResponse(r=>new URL(r.url()).pathname==='/api/authenticate'&&r.request().method()==='POST',{timeout:30000}),
  page.waitForResponse(r=>new URL(r.url()).pathname==='/api/account'&&r.status()===200,{timeout:30000}),
  page.locator('[data-cy="submit"]').click(),
 ]);
 result.authentication_status=auth.status();result.account_status=account.status();
 const identity=await account.json();result.account_login=identity.login;
 if(auth.status()!==200||identity.login!=='user'||result.authentication_posts!==1)throw Error('Native login identity check failed');
 result.status='qualified';
}catch(e){result.status='failed';result.error_type=e.name;result.error=String(e);}
finally{
 if(page){result.final_url=page.url();try{await page.screenshot({path:a.out+'/after-login.png',timeout:5000});}catch(e){result.screenshot_error=String(e);}}
 if(browser)await browser.close();
 await fs.writeFile(a.out+'/native-login.json',JSON.stringify(result,null,2)+'\n');
}
if(result.status!=='qualified')process.exitCode=1;
