import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {createRequire} from 'node:module';
import {join} from 'node:path';
import {writeFileSync} from 'node:fs';
const started=Date.now();
const result={kind:'infrastructure_only',status:'failed',scientific_cases:0,requests:[]};
const require=createRequire(join(process.env.PLAYWRIGHT_MODULE_PATH,'package.json'));
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH);
const server=createServer(async(req,res)=>{
 if(req.method==='POST' && req.url==='/save'){
  let body='';for await(const chunk of req)body+=chunk;
  result.requests.push({method:req.method,url:req.url,body});
  res.writeHead(200,{'Content-Type':'text/html'});res.end('<p id="saved">Saved</p>');
 }else if(req.method==='GET' && req.url==='/'){
  res.writeHead(200,{'Content-Type':'text/html'});res.end('<form method="post" action="/save"><label>Value<input name="value"></label><button>Save</button></form>');
 }else{res.writeHead(404);res.end();}
});
let browser;
try{
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
 const origin=`http://127.0.0.1:${server.address().port}`;
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE});
 result.browser_version=browser.version();
 const context=await browser.newContext();
 await context.route('**/*',route=>new URL(route.request().url()).origin===origin?route.continue():route.abort());
 const page=await context.newPage();page.setDefaultTimeout(10000);
 await page.goto(origin);await page.getByLabel('Value').fill('study-runtime');
 await page.getByRole('button',{name:'Save'}).click();await page.locator('#saved').waitFor();
 assert.deepEqual(result.requests,[{method:'POST',url:'/save',body:'value=study-runtime'}]);
 result.status='qualified';
}catch(error){result.error=String(error);process.exitCode=1;}
finally{
 if(browser)await browser.close();
 await new Promise(resolve=>server.close(resolve));
 result.elapsed_seconds=(Date.now()-started)/1000;
 writeFileSync(join(process.env.CI_ARTIFACT_DIR,'smoke.json'),JSON.stringify(result,null,2)+'\n');
}
