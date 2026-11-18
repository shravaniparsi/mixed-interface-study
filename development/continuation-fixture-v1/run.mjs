import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFileSync, writeFileSync, mkdirSync} from 'node:fs';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const dir=path.dirname(fileURLToPath(import.meta.url));
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
const out=process.env.FIXTURE_OUTPUT; assert(out);
mkdirSync(out,{recursive:true});
const cases=JSON.parse(readFileSync(path.join(dir,'cases.json')));
const esc=x=>String(x??'').replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;');
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const result={scope:'authored fixture qualification only',scientific_cases:0,cases:[],status:'in_progress'};
let mode,store,trace=[],server,browser;
const persist=x=>writeFileSync(store,JSON.stringify(x));
const read=()=>JSON.parse(readFileSync(store));
function classify(o){
 if(o.producer_status===422 && o.created===null)return 'producer_rejected';
 if(o.page_status===401)return 'authorization_failure';
 if(!o.created || o.before===undefined || o.after===undefined)return 'observation_unavailable';
 if(o.submit_status===409)return 'stale_state_conflict';
 if(o.invalid_events>0 && o.valid===false && o.native_posts===0 && equal(o.before,o.after))return 'native_validation_blocked';
 if(o.submit_status!==200)return 'unclassified';
 const expected={...o.before,description:'Edited description',version:o.before.version+1};
 if(!equal(expected,o.after))return 'unexpected_state_change';
 return !equal(o.input_title,o.created.title)?'normalized_then_continued':'continued';
}
function form(record){
 const create=record===null;
 return `<html><body><form method="POST" action="${create?'/native/create':'/native/save'}">
 <label>Title<input name="title" required value="${esc(record?.title)}"></label>
 <label>Description<input name="description" value="${esc(record?.description??'Initial description')}"></label>
 <input type="hidden" name="version" value="${record?.version??0}">
 <button>Save</button></form></body></html>`;
}
try{
 server=createServer(async(req,res)=>{
  try{
   let body='';for await(const c of req)body+=c;
   const event={method:req.method,path:req.url,body};trace.push(event);
   const send=(status,data,type='application/json')=>{event.status=status;res.writeHead(status,{'Content-Type':type});res.end(type==='application/json'?JSON.stringify(data):data);};
   if(req.headers.cookie!=='actor=study')return send(401,{error:'actor'});
   if(req.method==='POST' && ['/api/create','/native/create'].includes(req.url)){
    const native=req.url==='/native/create';const p=native?Object.fromEntries(new URLSearchParams(body)):JSON.parse(body);
    if(mode==='reject' && p.title===null)return send(422,{error:'title'});
    const record={id:1,title:mode==='normalize' && p.title===null?'Default title':p.title,description:p.description,version:1};persist(record);
    if(native){event.status=303;res.writeHead(303,{Location:'/edit/1'});return res.end();}
    return send(201,record);
   }
   if(req.method==='GET' && req.url==='/new')return send(200,form(null),'text/html');
   if(req.method==='GET' && req.url==='/edit/1')return send(200,form(read()),'text/html');
   if(req.method==='GET' && req.url==='/api/read')return mode==='missing'?send(503,{error:'unavailable'}):send(200,read());
   if(req.method==='POST' && req.url==='/native/save'){
    const p=Object.fromEntries(new URLSearchParams(body)),record=read();
    if(Number(p.version)!==record.version)return send(409,'<p id="conflict">Conflict</p>','text/html');
    const next={...record,title:p.title,description:p.description,version:record.version+1};
    if(mode==='extra')next.title='Unexpected title';persist(next);
    return send(200,'<p id="saved">Saved</p>','text/html');
   }
   return send(404,{error:'not_found'});
  }catch(e){res.writeHead(500);res.end('fixture_error');}
 });
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
 const origin=`http://127.0.0.1:${server.address().port}`;
 browser=await chromium.launch({headless:true});result.browser_version=browser.version();result.node_version=process.version;
 for(const c of cases){
  mode=c.mode;trace=[];store=path.join(out,c.id+'-state.json');persist(null);
  const context=await browser.newContext();
  await context.addCookies([{name:'actor',value:'study',url:origin}]);
  await context.route('**/*',r=>new URL(r.request().url()).origin===origin?r.continue():r.abort());
  const page=await context.newPage();page.setDefaultTimeout(10000);
  await page.addInitScript(()=>{window.invalidEvents=0;document.addEventListener('invalid',()=>window.invalidEvents++,true);});
  const request=async(url,options={})=>fetch(origin+url,{...options,headers:{Cookie:'actor=study','Content-Type':'application/json'}});
  const readback=async()=>{const r=await request('/api/read');return r.status===200?await r.json():undefined;};
  const o={input_title:c.title,native_posts:0,invalid_events:0};
  if(c.producer==='native'){
   await page.goto(origin+'/new');await page.getByLabel('Title',{exact:true}).fill(c.title);
   await Promise.all([page.waitForURL(origin+'/edit/1'),page.getByRole('button',{name:'Save',exact:true}).click()]);
   o.producer_status=trace.find(t=>t.path==='/native/create').status;
  }else{
   const r=await request('/api/create',{method:'POST',body:JSON.stringify({title:c.title,description:'Initial description'})});o.producer_status=r.status;
  }
  // File-backed snapshot is independent of the API response; retained for calibration.
  o.created=read();
  if(o.producer_status!==422){
   if(mode==='auth')await context.clearCookies();
   const response=await page.goto(origin+'/edit/1');o.page_status=response.status();
   if(o.page_status===200){
    o.before=await readback();
    if(mode==='stale'){const r=read();persist({...r,version:r.version+1});o.concurrent_write={version_increment:1};}
    await page.getByLabel('Description',{exact:true}).fill('Edited description');
    o.valid=await page.locator('form').evaluate(f=>f.checkValidity());
    // checkValidity fires invalid events: reset observation before the real click.
    await page.evaluate(()=>{window.invalidEvents=0;});
    if(o.valid){
     const [r]=await Promise.all([page.waitForResponse(r=>r.url()===origin+'/native/save' && r.request().method()==='POST'),page.getByRole('button',{name:'Save',exact:true}).click()]);o.submit_status=r.status();
    }else{
     await page.getByRole('button',{name:'Save',exact:true}).click();
     await page.waitForTimeout(500);o.invalid_events=await page.evaluate(()=>window.invalidEvents);
    }
    o.native_posts=trace.filter(t=>t.path==='/native/save' && t.method==='POST').length;
    o.after=await readback();
   }
  }
  const row={id:c.id,expected:c.expected,observed:classify(o),observation:o,trace:structuredClone(trace)};
  row.matches_expected=row.observed===row.expected;result.cases.push(row);
  await context.close();writeFileSync(path.join(out,'summary.json'),JSON.stringify(result,null,2));
 }
 result.status=result.cases.every(r=>r.matches_expected)?'qualified_authored_fixture':'label_mismatch';
 assert.equal(result.status,'qualified_authored_fixture');
}catch(e){result.status='failed';result.error=String(e);process.exitCode=1;}
finally{
 if(browser)await browser.close();if(server)await new Promise(resolve=>server.close(resolve));
 writeFileSync(path.join(out,'summary.json'),JSON.stringify(result,null,2)+'\n');
}
