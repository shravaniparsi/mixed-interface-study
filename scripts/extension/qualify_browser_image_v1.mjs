import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createReadStream} from 'node:fs';
import fs from 'node:fs/promises';
import http from 'node:http';
import os from 'node:os';
import {createRequire} from 'node:module';
const out='/study/evidence',result={kind:'isolated_browser_image_smoke',status:'failed',application_executions:0};
let browser,server;
try {
 assert.equal(process.version,'v20.20.2');result.node=process.version;
 result.network_interfaces=os.networkInterfaces();
 assert.ok(Object.values(result.network_interfaces).flat().every(i=>i.internal),'External interface present');
 const require=createRequire('/study/tools/package.json');
 const {chromium}=require('playwright');assert.equal(require('playwright/package.json').version,'1.62.1');
 result.playwright='1.62.1';result.executable=chromium.executablePath();
 const hash=createHash('sha256');for await(const chunk of createReadStream(result.executable))hash.update(chunk);
 result.executable_sha256=hash.digest('hex');
 assert.equal(result.executable_sha256,'0b20b130e7edd9dd51873be867761295fe0cfad490c2b9a64f95bd3cfc08fa71');
 let posted;
 server=http.createServer((req,res)=>{
  if(req.method==='GET'&&req.url==='/'){
   res.setHeader('Content-Type','text/html');res.end('<!doctype html><html><body><form method="post" action="/save"><input name="name" required><select name="role"><option>ROLE_USER</option></select><button type="submit">Save</button></form></body></html>');
  }else if(req.method==='POST'&&req.url==='/save'){
   const chunks=[];let size=0;req.on('data',chunk=>{size+=chunk.length;if(size>1024){req.destroy();return;}chunks.push(chunk);});
   req.on('end',()=>{posted=Buffer.concat(chunks).toString();res.setHeader('Content-Type','application/json');res.end(JSON.stringify({saved:true}));});
  }else{res.statusCode=404;res.end();}
 });
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(8088,'127.0.0.1',resolve);});
 browser=await chromium.launch({headless:true,executablePath:result.executable,args:['--no-sandbox','--disable-dev-shm-usage']});
 result.browser_version=browser.version();assert.equal(result.browser_version,'151.0.7922.34');
 const context=await browser.newContext({locale:'en-US',timezoneId:'UTC',viewport:{width:1280,height:900},serviceWorkers:'block'});
 const blocked=[];await context.route('**/*',route=>{if(new URL(route.request().url()).origin==='http://127.0.0.1:8088')return route.continue();blocked.push(route.request().url());return route.abort();});
 const page=await context.newPage();page.setDefaultTimeout(10000);
 await page.goto('http://127.0.0.1:8088/');await page.locator('input[name="name"]').fill('Study');
 assert.equal(await page.locator('select[name="role"] option:checked').textContent(),'ROLE_USER');
 const [response]=await Promise.all([page.waitForResponse(r=>r.url()==='http://127.0.0.1:8088/save'),page.locator('button').click()]);
 assert.equal(response.status(),200);assert.equal(posted,'name=Study&role=ROLE_USER');assert.deepEqual(blocked,[]);
 result.form_post=posted;result.status='qualified';
}catch(error){result.error_type=error.name;result.error=String(error);}
finally{if(browser)await browser.close();if(server)await new Promise(resolve=>server.close(resolve));await fs.writeFile(out+'/browser-image-smoke.json',JSON.stringify(result,null,2)+'\n');}
if(result.status!=='qualified')process.exitCode=1;
