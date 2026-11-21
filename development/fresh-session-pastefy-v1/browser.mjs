// Original native controls only; receipts remain private until sanitized export.
import {createHash} from 'node:crypto';
const requireValue=(ok,message)=>{if(!ok)throw new Error(message);};
export async function session(browser, origin, credentials, diagnostics={}, options={}) {
  const context=await browser.newContext({viewport:{width:1440,height:1000},locale:'en-US'});
  context.setDefaultTimeout(15000);context.setDefaultNavigationTimeout(30000);
  const page=await context.newPage();const pending=new Set(), tasks=new Set(), receipts=[], errors=[];
  diagnostics.receipts=receipts;diagnostics.errors=errors;diagnostics.stage='authenticate';
  const isApi=req=>{const u=new URL(req.url());return u.origin===origin&&u.pathname.startsWith('/api/');};
  page.on('request',req=>{if(isApi(req))pending.add(req);});
  page.on('requestfinished',req=>pending.delete(req));
  page.on('requestfailed',req=>{pending.delete(req);if(isApi(req))errors.push({path:new URL(req.url()).pathname,error:req.failure()?.errorText});});
  // The native edit handler reloads immediately after PUT. Buffer its real server
  // response before releasing it, so navigation cannot discard response-body evidence.
  await context.route(url=>url.origin===origin && /^\/api\/v2\/paste(?:\/[^/]+)?$/.test(url.pathname),async route=>{
    const req=route.request();if(!['POST','PUT'].includes(req.method()))return route.continue();
    try {
      const response=await route.fetch({timeout:15000,maxRedirects:0,maxRetries:0});
      const body=await response.body();
      receipts.push({method:req.method(),path:new URL(req.url()).pathname,request:req.postData(),status:response.status(),body:body.toString('utf8'),capture:'unchanged_request_forwarded_response_buffered_before_release'});
      await route.fulfill({response,body});pending.delete(req);
    } catch(error){errors.push({error:String(error),path:new URL(req.url()).pathname});await route.abort();}
  });
  page.on('response',response=>{
    const req=response.request();if(!isApi(req)||['POST','PUT'].includes(req.method()))return;
    const task=(async()=>{receipts.push({method:req.method(),path:new URL(req.url()).pathname,request:req.postData(),status:response.status(),body:await response.text()});pending.delete(req);})();
    tasks.add(task);task.catch(e=>errors.push({error:String(e)})).finally(()=>tasks.delete(task));
  });
  if(options.configureContext)await options.configureContext(context,page);
  async function settled(){
    const end=Date.now()+15000;let emptySince=0;
    while(Date.now()<end){
      if(!pending.size&&!tasks.size){emptySince ||= Date.now();if(Date.now()-emptySince>=250){requireValue(!errors.length,'API request or capture failed');return;}}
      else emptySince=0;
      await page.waitForTimeout(50);
    }
    diagnostics.outstanding=[...pending].map(r=>({method:r.method(),path:new URL(r.url()).pathname}));diagnostics.captureTasks=tasks.size;throw new Error('Outstanding API requests at checkpoint');
  }
  try {
    const identity=page.waitForResponse(async r=>{
      if(new URL(r.url()).pathname!=='/api/v2/user'||r.request().method()!=='GET'||!r.ok())return false;
      const u=await r.json();return u.logged_in===true&&u.id===credentials.user_id;
    });
    await page.goto(origin+'/auth?key='+encodeURIComponent(credentials.api_key));
    const response=await identity;const user=await response.json();
    requireValue(response.ok()&&user.logged_in===true&&user.id===credentials.user_id&&user.type==='USER','Native actor verification failed');
    await settled();
    const form=()=>page.locator('form').filter({has:page.locator('input[placeholder="file.js"]')});
    async function fill(field,value){
      diagnostics.stage='fill-'+field;
      requireValue(['title','content'].includes(field),'Unsupported ordinary field');
      if(field==='title')await form().locator('input[placeholder="file.js"]').fill(value);
      else {await form().locator('.CodeMirror').click();await page.keyboard.press('Control+A');await page.keyboard.insertText(value);}
    }
    async function submit(method,path){
      diagnostics.stage='submit-'+method;
      const reloaded=method==='PUT'?page.waitForEvent('load',{timeout:15000}):null;
      await form().locator('button[type="submit"]').click();diagnostics.stage='capture-'+method;
      const deadline=Date.now()+15000;let response;
      while(Date.now()<deadline){response=receipts.find(r=>r.method===method&&r.path===path);if(response)break;await page.waitForTimeout(50);}
      requireValue(response&&response.status>=200&&response.status<300,'Native write HTTP failure or missing capture');
      const body=JSON.parse(response.body);requireValue(body.success===true,'Native write rejected');if(reloaded)await reloaded;await settled();return body;
    }
    async function prepareEdit(id,field,value){
      diagnostics.stage='edit-navigation';await settled();await page.goto(origin+'/'+encodeURIComponent(id));await settled();
      diagnostics.stage='edit-button';await page.getByRole('button',{name:'Edit',exact:true}).click();
      await form().locator('input[placeholder="file.js"]').waitFor();await fill(field,value);return form();
    }
    return {page,context,receipts,settled,actor:{user_id:user.id,role:user.type,key_sha256:createHash('sha256').update(credentials.api_key).digest('hex')},
      async create(input){await fill('title',input.title);await fill('content',input.content);return submit('POST','/api/v2/paste');},
      prepareEdit,commitEdit:id=>submit('PUT','/api/v2/paste/'+id),
      async edit(id,field,value){await prepareEdit(id,field,value);return submit('PUT','/api/v2/paste/'+id);},
      async close(){diagnostics.stage='close';await settled();await context.close();}};
  } catch(error){diagnostics.url=page.url();diagnostics.dom=await Promise.race([page.content().catch(()=>null),new Promise(resolve=>setTimeout(()=>resolve(null),3000))]);await context.close();throw error;}
}
