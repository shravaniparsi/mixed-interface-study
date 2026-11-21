// Original native controls only; receipts remain private until sanitized export.
import {createHash} from 'node:crypto';
const requireValue=(ok,message)=>{if(!ok)throw new Error(message);};
export async function session(browser, origin, credentials) {
  const context=await browser.newContext({viewport:{width:1440,height:1000},locale:'en-US'});
  const page=await context.newPage();const pending=new Set(), tasks=new Set(), receipts=[], errors=[];
  const isApi=req=>{const u=new URL(req.url());return u.origin===origin&&u.pathname.startsWith('/api/');};
  page.on('request',req=>{if(isApi(req))pending.add(req);});
  page.on('requestfinished',req=>pending.delete(req));
  page.on('requestfailed',req=>{pending.delete(req);if(isApi(req))errors.push({path:new URL(req.url()).pathname,error:req.failure()?.errorText});});
  page.on('response',response=>{
    const req=response.request();if(!isApi(req))return;
    const task=(async()=>{receipts.push({method:req.method(),path:new URL(req.url()).pathname,request:req.postData(),status:response.status(),body:await response.text()});})();
    tasks.add(task);task.catch(e=>errors.push({error:String(e)})).finally(()=>tasks.delete(task));
  });
  async function settled(){
    const end=Date.now()+15000;let emptySince=0;
    while(Date.now()<end){
      if(!pending.size&&!tasks.size){emptySince ||= Date.now();if(Date.now()-emptySince>=250){requireValue(!errors.length,'API request or capture failed');return;}}
      else emptySince=0;
      await page.waitForTimeout(50);
    }
    throw new Error('Outstanding API requests at checkpoint');
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
      requireValue(['title','content'].includes(field),'Unsupported ordinary field');
      if(field==='title')await form().locator('input[placeholder="file.js"]').fill(value);
      else {await form().locator('.CodeMirror').click();await page.keyboard.press('Control+A');await page.keyboard.insertText(value);}
    }
    async function submit(method,path){
      const reply=page.waitForResponse(r=>r.request().method()===method&&new URL(r.url()).pathname===path);
      await form().locator('button[type="submit"]').click();const response=await reply;
      requireValue(response.ok(),'Native write HTTP failure');const body=await response.json();requireValue(body.success===true,'Native write rejected');await settled();return body;
    }
    return {page,context,receipts,settled,actor:{user_id:user.id,role:user.type,key_sha256:createHash('sha256').update(credentials.api_key).digest('hex')},
      async create(input){await fill('title',input.title);await fill('content',input.content);return submit('POST','/api/v2/paste');},
      async edit(id,field,value){await settled();await page.goto(origin+'/'+encodeURIComponent(id));await settled();await page.getByRole('button',{name:'Edit',exact:true}).click();await form().locator('input[placeholder="file.js"]').waitFor();await fill(field,value);return submit('PUT','/api/v2/paste/'+id);},
      async close(){await settled();await context.close();}};
  } catch(error){await context.close();throw error;}
}
