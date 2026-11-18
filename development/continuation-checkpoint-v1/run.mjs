import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import path from 'node:path';
const dir=path.dirname(fileURLToPath(import.meta.url));
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
const out=process.env.FIXTURE_OUTPUT;assert(out);mkdirSync(out,{recursive:true});
const store=path.join(out,'state.json');const read=()=>JSON.parse(readFileSync(store));
const persist=x=>writeFileSync(store,JSON.stringify(x));
const hash=x=>createHash('sha256').update(x).digest('hex');
const canonical=x=>JSON.stringify(x,(_,v)=>v && !Array.isArray(v) && typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
const same=(a,b)=>canonical(a)===canonical(b);
const esc=x=>String(x??'').replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;');
const schedule=JSON.parse(readFileSync(path.join(dir,'schedule.json')));
const result={scope:'authored checkpoint and repair qualification only',scientific_cases:0,status:'in_progress',groups:[]};
let server,browser,port=0,origin,trace=[],epoch=0;
async function start(){
 server=createServer(async(req,res)=>{
  let body='';for await(const c of req)body+=c;
  const e={method:req.method,path:req.url,body,epoch};trace.push(e);
  const send=(status,data,type='application/json')=>{e.status=status;res.writeHead(status,{'Content-Type':type});res.end(type==='application/json'?JSON.stringify(data):data);};
  try{
   if(req.headers.cookie!=='actor=study')return send(401,{actor:null});
   if(req.method==='GET' && req.url==='/whoami')return send(200,{actor:'study'});
   if(req.method==='GET' && req.url==='/api/read')return send(200,read());
   if(req.method==='POST' && req.url==='/api/create'){const p=JSON.parse(body);persist({id:1,title:p.title,description:'Initial description',version:1});return send(201,read());}
   if(req.method==='GET' && req.url==='/edit/1'){
    const r=read();return send(200,`<form method="POST" action="/native/save"><label>Title<input name="title" required value="${esc(r.title)}"></label><label>Description<input name="description" value="${esc(r.description)}"></label><input name="version" type="hidden" value="${r.version}"><button>Save</button></form>`,'text/html');
   }
   if(req.method==='POST' && req.url==='/native/save'){
    const p=Object.fromEntries(new URLSearchParams(body)),r=read();if(Number(p.version)!==r.version)return send(409,{error:'stale'});
    persist({...r,title:p.title,description:p.description,version:r.version+1});return send(200,'<p>Saved</p>','text/html');
   }
   return send(404,{error:'not_found'});
  }catch(e){return send(500,{error:'fixture_error'});}
 });
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(port,'127.0.0.1',resolve);});
 port=server.address().port;origin=`http://127.0.0.1:${port}`;
}
async function stop(){if(server){await new Promise(resolve=>server.close(resolve));server=null;}}
async function context(storageState){
 const c=await browser.newContext(storageState?{storageState}:{});
 if(!storageState)await c.addCookies([{name:'actor',value:'study',url:origin}]);
 await c.route('**/*',r=>new URL(r.request().url()).origin===origin?r.continue():r.abort());
 await c.addInitScript(()=>{window.invalidEvents=0;document.addEventListener('invalid',()=>window.invalidEvents++,true);});
 return c;
}
async function snapshot(c,page){
 const actor=await c.request.get(origin+'/whoami');const r=await c.request.get(origin+'/api/read');
 return {actor_status:actor.status(),actor:await actor.json(),read_status:r.status(),api:await r.json(),disk:read(),storage:await c.storageState(),form:await page.locator('form').count()?await page.locator('form').evaluate(f=>Object.fromEntries(new FormData(f))):null};
}
try{
 persist(null);await start();browser=await chromium.launch({headless:true});result.browser_version=browser.version();result.node_version=process.version;
 for(const plan of schedule){
  persist(null);let c=await context();let page=await c.newPage();page.setDefaultTimeout(10000);
  const producer=await c.request.post(origin+'/api/create',{data:{title:plan.title}});assert.equal(producer.status(),201);
  await page.goto(origin+'/edit/1');await page.evaluate(()=>localStorage.setItem('fixture-context','stable'));
  const saved=readFileSync(store);const checkpoint=await snapshot(c,page);
  assert(same(checkpoint.disk,checkpoint.api));assert.equal(checkpoint.actor.actor,'study');
  const group={id:plan.id,checkpoint_sha256:hash(saved),checkpoint,branches:[]};result.groups.push(group);
  for(const branch of plan.branches){
   if(branch.id!=='warm'){
    await c.close();await stop();writeFileSync(store,saved);epoch++;await start();
    const restoredStorage=structuredClone(checkpoint.storage);
    if(branch.id==='corrupt_state')persist({...read(),description:'Wrong restored description'});
    if(branch.id==='corrupt_actor')restoredStorage.cookies=[];
    c=await context(restoredStorage);page=await c.newPage();page.setDefaultTimeout(10000);await page.goto(origin+'/edit/1');
   }
   trace=[];const before=await snapshot(c,page);
   const actorOK=before.actor_status===200 && same(before.actor,checkpoint.actor) && same(before.storage,checkpoint.storage);
   const stateOK=same(before.disk,checkpoint.disk) && same(before.api,checkpoint.api) && same(before.form,checkpoint.form);
   const row={id:branch.id,expected:branch.expected,epoch,before,actor_gate:actorOK,state_gate:stateOK,checkpoint_bytes_match:hash(readFileSync(store))===hash(saved),intervention:branch.id==='restored_repair'?'fill_title_with_Repaired_title':'none',native_posts:0};
   if(!actorOK)row.observed='actor_gate_rejected';
   else if(!stateOK || !row.checkpoint_bytes_match)row.observed='state_gate_rejected';
   else{
    if(branch.id==='restored_repair')await page.getByLabel('Title',{exact:true}).fill('Repaired title');
    await page.getByLabel('Description',{exact:true}).fill('Edited description');
    row.form_before_click=await page.locator('form').evaluate(f=>Object.fromEntries(new FormData(f)));
    row.valid=await page.locator('form').evaluate(f=>f.checkValidity());await page.evaluate(()=>window.invalidEvents=0);
    if(row.valid){
     const [response]=await Promise.all([page.waitForResponse(r=>r.url()===origin+'/native/save' && r.request().method()==='POST'),page.getByRole('button',{name:'Save',exact:true}).click()]);row.submit_status=response.status();
    }else{await page.getByRole('button',{name:'Save',exact:true}).click();await page.waitForTimeout(500);row.invalid_events=await page.evaluate(()=>window.invalidEvents);}
    row.native_posts=trace.filter(t=>t.method==='POST' && t.path==='/native/save').length;
    row.after=read();
    if(row.valid===false && row.invalid_events===1 && row.native_posts===0 && same(row.after,before.disk))row.observed='blocked';
    else if(row.submit_status===200 && row.native_posts===1 && same(row.after,{...before.disk,title:branch.id==='restored_repair'?'Repaired title':before.disk.title,description:'Edited description',version:before.disk.version+1}))row.observed='continued';
    else row.observed='unexpected';
   }
   row.trace=structuredClone(trace);row.matches_expected=row.observed===row.expected;group.branches.push(row);
   writeFileSync(path.join(out,'summary.json'),JSON.stringify(result,null,2));
  }
  await c.close();
  const [warm,sham,repair]=group.branches;
  assert.equal(warm.observed,sham.observed);assert(same(warm.after,sham.after));
  assert(same(warm.form_before_click,sham.form_before_click));
  assert(same(repair.form_before_click,{...sham.form_before_click,title:'Repaired title'}));
  assert(group.branches.every(b=>b.matches_expected));
 }
 result.status='qualified_authored_checkpoint';
}catch(e){result.status='failed';result.error=String(e);process.exitCode=1;}
finally{if(browser)await browser.close();await stop();writeFileSync(path.join(out,'summary.json'),JSON.stringify(result,null,2)+'\n');}
