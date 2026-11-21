/** Original Shlink UI controls only. Deployment and persistent-state checks are caller-owned. */
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createCapture} from '../redesign-harness-qualification-v1/capture.mjs';
const hash=value=>createHash('sha256').update(value).digest('hex');
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
export class ShlinkBrowser {
 constructor({browser,uiOrigin,apiOrigin,apiKey,serverName,write}){
  assert.equal(new URL(uiOrigin).origin,uiOrigin);assert.equal(new URL(apiOrigin).origin,apiOrigin);
  assert(apiKey&&serverName&&typeof write==='function');
  Object.assign(this,{browser,uiOrigin,apiOrigin,serverName,write});this.apiKeyHash=hash(apiKey);
  this.trace=[];this.pending=new Set();this.phase='initialization';this.errors=[];this.requestNumber=0;
  this.capture=createCapture({bodyTimeoutMs:3000,flushTimeoutMs:4000,write:rows=>write('response-capture',rows)});
 }
 record(event){this.trace.push({phase:this.phase,...event});this.write('browser-trace',this.trace);}
 async openFresh(){
  assert(!this.context,'adapter can open only one context');this.context=await this.browser.newContext({locale:'en-US'});
  const initial=await this.context.storageState({indexedDB:true});assert.deepEqual(initial,{cookies:[],origins:[]});this.write('initial-context',initial);
  this.page=await this.context.newPage();this.page.setDefaultTimeout(10000);
  await this.context.route('**/*',async route=>{
   const request=route.request(),origin=new URL(request.url()).origin;
   if(![this.uiOrigin,this.apiOrigin].includes(origin)){this.errors.push({kind:'external_request',url:request.url()});this.record(this.errors.at(-1));await route.abort('blockedbyclient');return;}
   await route.continue();
  });
  const ids=new WeakMap();
  this.page.on('request',request=>{
   this.pending.add(request);const id=++this.requestNumber;ids.set(request,id);
   const url=new URL(request.url()),headers=request.headers(),api=url.origin===this.apiOrigin;
   const fingerprint=api&&headers['x-api-key']?hash(headers['x-api-key']):null;
   if(api&&url.pathname.startsWith('/rest/v3/')&&fingerprint!==this.apiKeyHash)this.errors.push({kind:'wrong_api_key',id});
   this.record({kind:'request',id,url:request.url(),method:request.method(),body:request.postData(),api_key_sha256:fingerprint});
  });
  this.page.on('requestfinished',request=>this.pending.delete(request));
  this.page.on('requestfailed',request=>{this.pending.delete(request);const error={kind:'request_failed',id:ids.get(request),url:request.url(),failure:request.failure()};this.errors.push(error);this.record(error);});
  this.page.on('pageerror',error=>{const value={kind:'page_error',error:String(error)};this.errors.push(value);this.record(value);});
  this.page.on('response',response=>{
   if(new URL(response.url()).origin!==this.apiOrigin)return;
   this.capture.observe({phase:this.phase,id:ids.get(response.request()),url:response.url(),status:response.status()},()=>response.text());
  });
  await this.page.goto(this.uiOrigin+'/');
  const server=this.page.getByRole('link',{name:this.serverName,exact:true});await server.waitFor();assert.equal(await server.count(),1);
  const href=await server.getAttribute('href');assert.match(href,/^\/server\/[^/?#]+$/);this.prefix=href;
  await server.click();await this.page.waitForURL(this.uiOrigin+this.prefix+'/overview');await this.settle();
  this.write('selected-server',{native_route_prefix:this.prefix,api_origin:this.apiOrigin,api_key_sha256:this.apiKeyHash});
 }
 async settle(){
  const deadline=Date.now()+10000;
  while(this.pending.size){assert(Date.now()<deadline,'observed browser work did not finish');await pause(20);}
  assert.deepEqual(this.errors,[],'browser errors or external requests');
  // This covers observed HTTP work only. It does not establish backend queue completion.
 }
 async form({shortCode,expected}={}){
  assert(this.prefix,'native server selection required');
  const suffix=shortCode?'/short-code/'+encodeURIComponent(shortCode)+'/edit':'/create-short-url';
  if(new URL(this.page.url()).pathname!==this.prefix+suffix){
   if(!shortCode){
    const create=this.page.locator('nav a').filter({hasText:'Create short URL'});assert.equal(await create.count(),1);await create.click();
   }else{
    const list=this.page.locator('nav a').filter({hasText:'List short URLs'});assert.equal(await list.count(),1);await list.click();
    const row=this.page.getByRole('row').filter({has:this.page.locator('a[href="http://shlink.test/'+shortCode+'"]')});await row.waitFor();assert.equal(await row.count(),1);
    const menu=row.locator('button[aria-haspopup="true"]');assert.equal(await menu.count(),1);await menu.click();
    const edit=this.page.locator('a[href="'+this.prefix+suffix+'"]');await edit.waitFor();assert.equal(await edit.count(),1);await edit.click();
   }
   await this.page.waitForURL(url=>url.pathname===this.prefix+suffix);
  }
  const form=this.page.locator('form[name="shortUrlForm"]');await form.waitFor();assert.equal(await form.count(),1);
  await form.getByPlaceholder('URL to be shortened',{exact:true}).waitFor();await form.getByPlaceholder('Title',{exact:true}).waitFor();
  if(shortCode){
   assert(expected&&typeof expected.longUrl==='string'&&typeof expected.title==='string','expected persisted values required for native hydration');
   await this.page.waitForFunction(expected=>{const form=document.querySelector('form[name="shortUrlForm"]');return form?.querySelector('input[placeholder="URL to be shortened"]')?.value===expected.longUrl&&form?.querySelector('input[placeholder="Title"]')?.value===expected.title;},expected);
  }
  await this.settle();return form;
 }
 async values(form){return {longUrl:await form.getByPlaceholder('URL to be shortened',{exact:true}).inputValue(),title:await form.getByPlaceholder('Title',{exact:true}).inputValue()};}
 async fill(form,pointer,value){
  assert.equal(typeof value,'string');assert(value.length>0,'ordinary inputs must be nonempty');
  const placeholder={'/longUrl':'URL to be shortened','/title':'Title'}[pointer];assert(placeholder,'unsupported field');
  const input=form.getByPlaceholder(placeholder,{exact:true});assert.equal(await input.count(),1);assert(await input.isEnabled());await input.fill(value);assert.equal(await input.inputValue(),value);
  this.record({kind:'native_fill',pointer,value});
 }
 async save(form,{label,shortCode,changes}){
  this.phase=label;const start=this.trace.length;const before=await this.values(form);this.write(label+'-form-before',before);
  for(const [pointer,value] of Object.entries(changes))await this.fill(form,pointer,value);
  this.write(label+'-form-edited',await this.values(form));
  const method=shortCode?'PATCH':'POST',pathname='/rest/v3/short-urls'+(shortCode?'/'+encodeURIComponent(shortCode):'');
  const save=form.getByRole('button',{name:'Save',exact:true});assert(await save.isEnabled());
  const pending=this.page.waitForResponse(response=>{const url=new URL(response.url());return url.origin===this.apiOrigin&&url.pathname===pathname&&response.request().method()===method;});
  await save.click();const response=await pending;
  const request={method:response.request().method(),path:new URL(response.url()).pathname,query:new URL(response.url()).search,body:response.request().postDataJSON()};
  const text=await response.text();this.write(label+'-request',request);this.write(label+'-response',{status:response.status(),text});assert(response.ok(),text);
  if(shortCode)await this.page.getByText('Short URL properly edited.',{exact:true}).waitFor();
  else await this.page.getByText('Great!',{exact:true}).waitFor();
  await this.settle();
  const writes=this.trace.slice(start).filter(r=>r.kind==='request'&&!['GET','HEAD','OPTIONS'].includes(r.method)).map(r=>{const url=new URL(r.url);return {method:r.method,path:url.pathname,query:url.search,body:JSON.parse(r.body)};});
  assert.deepEqual(writes,[request]);this.write(label+'-writes',writes);
  const outcome={label,form_before:before,actions:Object.entries(changes).map(([pointer,value])=>({pointer,value})),request,response_status:response.status()};
  if(!shortCode){outcome.created=JSON.parse(text);assert.equal(typeof outcome.created.shortCode,'string');assert(outcome.created.shortCode);}
  this.write(label+'-control',outcome);return outcome;
 }
 async close(){
  let failure;
  try{await this.settle();}catch(error){failure=error;}
  if(this.page&&!this.page.isClosed())this.write('final-page-diagnostic',{url:this.page.url(),text:(await this.page.locator('body').innerText()).slice(0,40000),controls:await this.page.locator('form,input,button,a').evaluateAll(nodes=>nodes.slice(0,200).map(n=>({tag:n.tagName,name:n.getAttribute('name'),label:n.getAttribute('aria-label'),text:n.textContent?.slice(0,200),href:n.getAttribute('href')})))});
  if(this.context)await this.context.close();const captured=await this.capture.close();
  this.write('browser-errors',this.errors);assert.deepEqual(this.errors,[],'browser errors at close');assert(captured.every(r=>r.capture.status==='complete'),'incomplete API response capture');
  if(failure)throw failure;
 }
}
