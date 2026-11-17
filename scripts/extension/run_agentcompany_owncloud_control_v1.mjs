import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const [branch,out]=process.argv.slice(2);
assert.ok(['native_native','api_native','api_api'].includes(branch));
const registration=JSON.parse(await readFile('manifests/agentcompany-owncloud-ordinary-v1.json','utf8'));
const payload=await readFile('fixtures/agentcompany-owncloud-control-v1/job_description.md');
const sha=b=>createHash('sha256').update(b).digest('hex');
assert.equal(sha(payload),registration.payload_sha256);
const base='http://the-agent-company.com:8092',path=registration.destination;
const dav='/remote.php/webdav'+path;
const shares='/ocs/v1.php/apps/files_sharing/api/v1/shares';
const {chromium,request}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
await mkdir(out,{recursive:true});
const result={kind:'agentcompany_owncloud_ordinary_branch_v1',branch,passed:false,stage:'start',scientific_cases_executed:0,api_requests:[],native_requests:[]};
const save=()=>writeFile(out+'/result.json',JSON.stringify(result,null,2)+'\n');
let api,anon,browser,page;
async function fetchAPI(method,url,options={}){
 const response=await api.fetch(base+url,{method,...options,timeout:20000});
 result.api_requests.push({method,path:url,status:response.status()});await save();return response;
}
async function readShares(){
 const response=await fetchAPI('GET',shares+'?format=json&path='+encodeURIComponent(path));
 assert.equal(response.status(),200);const body=await response.json();
 assert.ok([100,200].includes(Number(body.ocs.meta.statuscode)));assert.ok(Array.isArray(body.ocs.data));return body.ocs.data;
}
async function fileState(){
 const response=await fetchAPI('GET',dav);assert.equal(response.status(),200);
 const bytes=await response.body();assert.equal(sha(bytes),registration.payload_sha256);
 return {path,sha256:sha(bytes),length:bytes.length,content_type:response.headers()['content-type']??null};
}
try{
 await save();
 api=await request.newContext({extraHTTPHeaders:{Authorization:'Basic '+Buffer.from('theagentcompany:theagentcompany').toString('base64'),'OCS-APIRequest':'true'},ignoreHTTPSErrors:false});
 anon=await request.newContext();
 result.stage='preflight';await save();
 assert.equal((await fetchAPI('PROPFIND','/remote.php/webdav/Documents',{headers:{Depth:'0'}})).status(),207);
 assert.equal((await fetchAPI('GET',dav)).status(),404,'Requested filename already exists; do not overwrite');
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage','--proxy-server=direct://','--proxy-bypass-list=*']});
 const context=await browser.newContext({locale:'en-US',timezoneId:'UTC',serviceWorkers:'block'});
 await context.route('**/*',route=>{
  const u=new URL(route.request().url());
  return u.protocol==='http:'&&['the-agent-company.com','localhost','127.0.0.1'].includes(u.hostname)?route.continue():route.abort();
 });
 page=await context.newPage();page.setDefaultTimeout(20000);
 page.on('response',response=>{
  const req=response.request(),u=new URL(response.url());
  if(!['GET','HEAD','OPTIONS'].includes(req.method()))result.native_requests.push({method:req.method(),path:u.pathname,status:response.status()});
 });
 if(branch!=='api_api'){
  result.stage='login';await save();await page.goto(base+'/index.php/login');
  await page.locator('#user').fill('theagentcompany');await page.locator('#password').fill('theagentcompany');
  await page.locator('#submit').click();await page.waitForURL(u=>u.pathname.includes('/apps/files'));
 }
 result.stage='producer';await save();
 if(branch==='native_native'){
  await page.goto(base+'/index.php/apps/files/?dir=%2FDocuments');
  await page.locator('#file_upload_start').setInputFiles({name:'job_description.md',mimeType:'text/markdown',buffer:payload});
  await page.locator('tr[data-file="job_description.md"]').waitFor({state:'visible'});
 }else{
  assert.equal((await fetchAPI('PUT',dav,{data:payload,headers:{'Content-Type':'text/markdown'}})).status(),201);
 }
 result.producer=await fileState();
 assert.deepEqual(await readShares(),[],'Unexpected pre-existing share');
 result.stage='consumer';await save();
 if(branch==='api_api'){
  const response=await fetchAPI('POST',shares+'?format=json',{form:{path,shareType:3,permissions:1}});
  assert.equal(response.status(),200);const body=await response.json();assert.ok([100,200].includes(Number(body.ocs.meta.statuscode)));
 }else{
  await page.goto(base+'/index.php/apps/files/?dir=%2FDocuments');
  const row=page.locator('tr[data-file="job_description.md"]');await row.waitFor({state:'visible'});
  await row.locator('.action-share').click();
  await page.locator('.addLink:visible').click();
  const radio=page.locator('input[name="publicPermissions"][value="1"]');
  assert.equal(await radio.count(),1);
  if(!await radio.isChecked())await page.locator('label[for="'+await radio.getAttribute('id')+'"]').click();
  await page.getByRole('button',{name:'Share',exact:true}).click();
  await page.locator('.public-link-modal').waitFor({state:'hidden'});
 }
 result.stage='verification';await save();
 const records=await readShares();assert.equal(records.length,1);const share=records[0];
 assert.equal(share.path,path);assert.equal(Number(share.share_type),3);assert.equal(Number(share.permissions),1);
 assert.ok(share.share_with===null||share.share_with==='');
 assert.ok(share.expiration===null||share.expiration==='');
 const url=new URL(share.url);assert.equal(url.origin,base);assert.ok(url.pathname.includes('/s/'));
 result.share={path:share.path,share_type:Number(share.share_type),permissions:Number(share.permissions),expiration:share.expiration,share_with:share.share_with,url:share.url,uid_owner:share.uid_owner};
 assert.equal(share.uid_owner,'theagentcompany');
 const downloaded=await anon.get(share.url.replace(/\/$/,'')+'/download',{timeout:20000});
 assert.equal(downloaded.status(),200);result.public_download_sha256=sha(await downloaded.body());
 assert.equal(result.public_download_sha256,registration.payload_sha256);
 result.final_file=await fileState();assert.deepEqual(result.final_file,result.producer);
 await writeFile(out+'/link.txt',share.url+'\n');
 if(branch==='native_native')assert.equal(result.api_requests.filter(r=>['PUT','POST','DELETE','PATCH'].includes(r.method)).length,0);
 if(branch==='api_native')assert.equal(result.api_requests.filter(r=>r.method==='POST').length,0);
 result.passed=true;result.stage='completed';
}catch(error){
 result.error_type=error.name;result.error=String(error.stack??error);
 if(page){await page.screenshot({path:out+'/failure.png',fullPage:true}).catch(()=>{});await writeFile(out+'/failure.html',await page.content().catch(()=>''));}
}finally{
 await save();await api?.dispose();await anon?.dispose();await browser?.close();
}
process.exitCode=result.passed?0:1;
