/** Ordinary project-to-members qualification in a fresh pinned image. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {parseArgs} from 'node:util';
const {values:a}=parseArgs({options:{credentials:{type:'string'},out:{type:'string'},branch:{type:'string'}}});
assert.ok(['native_native','api_native','api_api'].includes(a.branch));
const credentials=JSON.parse(await readFile(a.credentials,'utf8'));
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
const base='http://127.0.0.1:8023',name='llm_bulk_inference',path='byteblaze/'+name;
const targets=[{id:2367,username:'primer'},{id:43,username:'convexegg'},{id:5,username:'abisubramanya27'}];
const result={kind:'benchmark_gitlab_members_control_v1',branch:a.branch,scientific_cases_executed:0,ordinary_control_passed:false,stage:'start',api_requests:[],native_writes:[]};
await mkdir(a.out,{recursive:true});const save=()=>writeFile(a.out+'/members-control.json',JSON.stringify(result,null,2)+'\n');
const business=p=>Object.fromEntries(['name','path','path_with_namespace','description','visibility','empty_repo','default_branch','issues_enabled','merge_requests_enabled','wiki_enabled','snippets_enabled','jobs_enabled','lfs_enabled','request_access_enabled','shared_runners_enabled','auto_devops_enabled','builds_access_level','repository_access_level','issues_access_level','merge_requests_access_level'].map(k=>[k,p[k]??null]).concat([['namespace_id',p.namespace?.id??null],['owner_id',p.owner?.id??null]]));
const memberships=rows=>rows.map(r=>({id:r.id,access_level:r.access_level})).sort((a,b)=>a.id-b.id);
let browser,page;
try{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']});
 const context=await browser.newContext({locale:'en-US',timezoneId:'UTC'});
 await context.route('**/*',route=>{const u=new URL(route.request().url());return u.protocol==='http:'&&['localhost','127.0.0.1'].includes(u.hostname)&&u.port==='8023'?route.continue():route.abort();});
 page=await context.newPage();page.setDefaultTimeout(20000);
 page.on('response',r=>{const q=r.request(),u=new URL(q.url());if(!['GET','HEAD'].includes(q.method())&&u.pathname!='/users/sign_in')result.native_writes.push({method:q.method(),path:u.pathname,status:r.status()});});
 await page.goto(base+'/users/sign_in');await page.getByTestId('username-field').fill(credentials.username);await page.getByTestId('password-field').fill(credentials.password);
 await Promise.all([page.waitForURL(u=>u.pathname!='/users/sign_in'),page.getByTestId('sign-in-button').click()]);
 const csrf=await page.locator('meta[name="csrf-token"]').getAttribute('content');assert.ok(csrf);
 async function api(method,url,body,expected=200){const r=await context.request.fetch(base+url,{method,data:body,headers:{'X-CSRF-Token':csrf},timeout:30000});result.api_requests.push({method,path:url,body,status:r.status()});await save();assert.equal(r.status(),expected,method+' '+url);return r.json();}
 const actor=await api('GET','/api/v4/user');assert.equal(actor.id,2330);result.actor={id:actor.id,username:actor.username};
 result.stage='preflight';await api('GET','/api/v4/projects/'+encodeURIComponent(path),undefined,404);result.preflight_project_absent=true;
 for(const target of targets){const user=await api('GET','/api/v4/users/'+target.id);assert.equal(user.username,target.username);}
 result.stage='producer';await save();let id;
 if(a.branch==='native_native'){
  await page.goto(base+'/projects/new');await page.locator('a[href="#blank_project"]').click();
  await page.locator('#project_name:visible').fill(name);await page.locator('#project_path:visible').fill(name);
  await page.locator('#project_visibility_level_0:visible').check();await page.locator('#project_initialize_with_readme:visible').uncheck();
  await page.locator('#project_initialize_with_sast:visible').uncheck();
  await Promise.all([page.waitForURL(u=>u.pathname==='/'+path),page.getByRole('button',{name:'Create project',exact:true}).filter({visible:true}).click()]);
  id=(await api('GET','/api/v4/projects/'+encodeURIComponent(path))).id;
 }else{id=(await api('POST','/api/v4/projects',{name,path:name,visibility:'private',initialize_with_readme:false},201)).id;}
 result.project_id=id;
 const before=business(await api('GET','/api/v4/projects/'+id));result.producer_state=before;
 assert.equal(before.name,name);assert.equal(before.path_with_namespace,path);assert.equal(before.visibility,'private');assert.equal(before.empty_repo,true);
 const initialMembers=await api('GET',`/api/v4/projects/${id}/members/all?per_page=100`);assert.ok(initialMembers.length<100);
 result.initial_members=memberships(initialMembers);assert.ok(targets.every(t=>!initialMembers.some(m=>m.id===t.id)));
 result.stage='continuation';await save();
 if(a.branch==='api_api'){
  for(const target of targets)await api('POST',`/api/v4/projects/${id}/members`,{user_id:target.id,access_level:30},201);
 }else{
  await page.goto(base+'/'+path+'/-/project_members');await page.getByRole('button',{name:'Invite members',exact:true}).click();
  const dialog=page.getByRole('dialog');await dialog.waitFor({state:'visible'});
  const search=dialog.locator('input[placeholder*="username" i]:visible,input[placeholder*="Search members" i]:visible');assert.equal(await search.count(),1);
  for(const target of targets){
   await search.fill(target.username);
   const option=page.getByRole('option').filter({hasText:target.username});await option.waitFor({state:'visible'});assert.equal(await option.count(),1);await option.click();
  }
  await dialog.getByRole('button',{name:'Guest',exact:true}).click();await dialog.getByText('Developer',{exact:true}).click();
  await dialog.getByRole('button',{name:'Invite',exact:true}).click();await dialog.waitFor({state:'hidden'});
 }
 const finalProject=business(await api('GET','/api/v4/projects/'+id));result.final_state=finalProject;assert.deepEqual(finalProject,before);
 const finalMembers=await api('GET',`/api/v4/projects/${id}/members/all?per_page=100`);assert.ok(finalMembers.length<100);result.final_members=memberships(finalMembers);
 const expected=[...result.initial_members,...targets.map(t=>({id:t.id,access_level:30}))].sort((a,b)=>a.id-b.id);assert.deepEqual(result.final_members,expected);
 result.ordinary_control_passed=true;result.stage='complete';
}catch(e){result.error_type=e.name;result.error=e.name==='AssertionError'?String(e.message).slice(0,600):'Instrument step failed; inspect stage and visible controls.';process.exitCode=1;
 if(page){try{result.failure_path=new URL(page.url()).pathname;result.failure_fields=await page.locator('input:not([type=hidden]):not([type=password]),textarea,button,select,[role=option]').evaluateAll(ns=>ns.filter(n=>n.getClientRects().length).map(n=>({tag:n.tagName,name:n.name,id:n.id,type:n.type,role:n.getAttribute('role'),placeholder:n.getAttribute('placeholder'),text:['BUTTON','SELECT'].includes(n.tagName)||n.getAttribute('role')==='option'?n.innerText.trim():null})));}catch{}}
}finally{if(browser)await browser.close();result.browser_cleanup_confirmed=true;await save();}
