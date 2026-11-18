import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {parseArgs} from 'node:util';
import assert from 'node:assert/strict';
const {values:a}=parseArgs({options:{out:{type:'string'},arm:{type:'string'}}});
assert.ok(['ui-ui','api-ui','api-api'].includes(a.arm));
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
const base='http://127.0.0.1:4200',ordinary={title:'Study task',description:'Study description',color:'#feff9c',status:'TODO'};
const result={arm:a.arm,status:'not_run',stages:[],responses:[],blocked:[],request_failures:[],page_errors:[],independent_evaluation_cases:0};
let browser,page;const counts={board:0,create:0,update:0};
await fs.mkdir(a.out,{recursive:true});
try {
 assert.equal(process.version,'v20.20.2');
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']});
 assert.equal(browser.version(),'151.0.7922.34');
 const context=await browser.newContext({locale:'en-US',timezoneId:'UTC',viewport:{width:1280,height:900},serviceWorkers:'block'});
 await context.route('**/*',async route=>{
  const r=route.request(),u=new URL(r.url());let allow=u.origin===base&&['GET','HEAD'].includes(r.method());
  const kind=r.method()==='POST'&&u.pathname==='/api/kanbans/'?'board':r.method()==='POST'&&/^\/api\/kanbans\/[^/]+\/tasks\/$/.test(u.pathname)?'create':r.method()==='PUT'&&/^\/api\/tasks\/[^/]+$/.test(u.pathname)?'update':null;
  if(u.origin===base&&kind&&counts[kind]===0){counts[kind]++;allow=true;}
  if(allow)return route.continue();result.blocked.push({method:r.method(),url:r.url()});return route.abort();
 });
 page=await context.newPage();page.setDefaultTimeout(20000);
 page.on('pageerror',e=>result.page_errors.push(String(e)));
 page.on('requestfailed',r=>result.request_failures.push({method:r.method(),path:new URL(r.url()).pathname,error:r.failure()?.errorText}));
 page.on('response',r=>{if(result.responses.length<250)result.responses.push({method:r.request().method(),path:new URL(r.url()).pathname,status:r.status()});});
 async function get(path){const r=await context.request.get(base+path,{timeout:15000,maxRedirects:0});assert.equal(r.status(),200);return r.json();}
 const dialog=()=>page.locator('mat-dialog-container');
 const save=()=>dialog().getByRole('button',{name:'Save',exact:true});
 await page.goto(base+'/',{waitUntil:'domcontentloaded'});
 if(a.arm==='ui-ui'){
  await page.getByRole('button',{name:'+ Create Kanban',exact:true}).click();
  await dialog().locator('input[formControlName="title"]').fill('Study Board');
  const [r]=await Promise.all([page.waitForResponse(r=>new URL(r.url()).pathname==='/api/kanbans/'&&r.request().method()==='POST'),save().click()]);
  result.board_producer={status:r.status(),body:r.request().postDataJSON()};assert.ok(r.ok());assert.deepEqual(result.board_producer.body,{title:'Study Board'});
 }else{
  counts.board++;const r=await context.request.post(base+'/api/kanbans/',{data:{title:'Study Board'},timeout:15000,maxRedirects:0});result.board_producer={status:r.status(),body:{title:'Study Board'}};assert.ok(r.ok());
 }
 const boards=await get('/api/kanbans/');assert.ok(Array.isArray(boards));const matches=boards.filter(b=>b.title==='Study Board');assert.equal(matches.length,1);const board=matches[0];assert.ok(board.id!=null);result.board_id=board.id;result.stages.push('parent_persisted');
 const createPath='/api/kanbans/'+board.id+'/tasks/';
 await page.goto(base+'/kanbans/'+board.id,{waitUntil:'domcontentloaded'});
 if(a.arm==='ui-ui'){
  await page.getByRole('button',{name:'+ Create Task',exact:true}).click();
  await dialog().locator('input[formControlName="title"]').fill(ordinary.title);
  await dialog().locator('textarea[formControlName="description"]').fill(ordinary.description);
  await dialog().locator('mat-select[formControlName="color"]').click();await page.getByRole('option',{name:'YELLOW',exact:true}).click();
  await page.screenshot({path:a.out+'/before-create.png'});
  const [r]=await Promise.all([page.waitForResponse(r=>new URL(r.url()).pathname===createPath&&r.request().method()==='POST'),save().click()]);
  result.producer={status:r.status(),body:r.request().postDataJSON()};assert.ok(r.ok());assert.deepEqual(result.producer.body,ordinary);
 }else{
  counts.create++;const r=await context.request.post(base+createPath,{data:ordinary,timeout:15000,maxRedirects:0});result.producer={status:r.status(),body:ordinary};assert.ok(r.ok());
 }
 const fullBoard=await get('/api/kanbans/'+board.id);const tasks=fullBoard.tasks.filter(t=>t.title===ordinary.title);assert.equal(tasks.length,1);assert.ok(tasks[0].id!=null);const id=tasks[0].id;
 const raw=await get('/api/tasks/'+id);result.after_create=raw;for(const [k,v] of Object.entries(ordinary))assert.equal(raw[k],v);assert.equal(raw.id,id);result.stages.push('task_persisted');
 const updateBody={...raw,title:'Edited task',status:'TODO'};
 if(a.arm!=='api-api'){
  await page.goto(base+'/kanbans/'+board.id,{waitUntil:'domcontentloaded'});
  await page.locator('.sticky-note').filter({hasText:ordinary.title}).dblclick();
  assert.equal(await dialog().locator('input[formControlName="title"]').inputValue(),ordinary.title);
  assert.equal(await dialog().locator('textarea[formControlName="description"]').inputValue(),ordinary.description);
  await dialog().locator('input[formControlName="title"]').fill('Edited task');assert.equal(await save().isEnabled(),true);
  await page.screenshot({path:a.out+'/before-edit.png'});
  const [r]=await Promise.all([page.waitForResponse(r=>new URL(r.url()).pathname==='/api/tasks/'+id&&r.request().method()==='PUT'),save().click()]);
  result.consumer={status:r.status(),body:r.request().postDataJSON()};assert.ok(r.ok());assert.deepEqual(result.consumer.body,updateBody);
 }else{
  counts.update++;const r=await context.request.put(base+'/api/tasks/'+id,{data:updateBody,timeout:15000,maxRedirects:0});result.consumer={status:r.status(),body:updateBody};assert.ok(r.ok());
 }
 result.after_edit=await get('/api/tasks/'+id);assert.deepEqual(result.after_edit,updateBody);result.stages.push('edit_persisted');result.status='qualified';
}catch(e){result.status='failed';result.error=String(e);result.error_type=e.name;}
finally{
 result.write_counts=counts;
 if(page){result.final_url=page.url();try{await page.screenshot({path:a.out+'/final.png',timeout:5000});}catch(e){result.screenshot_error=String(e);}}
 if(browser)await browser.close();await fs.writeFile(a.out+'/control.json',JSON.stringify(result,null,2)+'\n');
}
if(result.status!=='qualified')process.exitCode=1;
