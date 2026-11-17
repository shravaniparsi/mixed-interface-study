/** Ordinary project-to-Web-IDE README qualification in a fresh pinned image. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {parseArgs} from 'node:util';
const {values:a}=parseArgs({options:{credentials:{type:'string'},out:{type:'string'},branch:{type:'string'}}});
assert.ok(['native_native','api_native','api_api'].includes(a.branch));
const credentials=JSON.parse(await readFile(a.credentials,'utf8'));
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
const base='http://127.0.0.1:8023',name='nolan_young_fans',path='byteblaze/'+name;
const expected=await readFile('results/benchmark-wikipedia-article-v1/expected-README.md','utf8');
const commitMessage='Add Nolan film README';
const result={kind:'benchmark_gitlab_readme_control_v1',branch:a.branch,scientific_cases_executed:0,ordinary_control_passed:false,stage:'start',api_requests:[],native_writes:[]};
await mkdir(a.out,{recursive:true});const save=()=>writeFile(a.out+'/readme-control.json',JSON.stringify(result,null,2)+'\n');
const business=p=>Object.fromEntries(['name','path','path_with_namespace','description','visibility','empty_repo','default_branch','issues_enabled','merge_requests_enabled','wiki_enabled','snippets_enabled','jobs_enabled','lfs_enabled','request_access_enabled','shared_runners_enabled','auto_devops_enabled','builds_access_level','repository_access_level','issues_access_level','merge_requests_access_level'].map(k=>[k,p[k]??null]).concat([['namespace_id',p.namespace?.id??null],['owner_id',p.owner?.id??null]]));

let browser,page;
async function step(name,action){result.action=name;await save();return action();}
async function checkedViaLabel(id,wanted){
 const input=page.locator('#'+id+':visible');assert.equal(await input.count(),1);
 if(await input.isChecked()!==wanted)await page.locator('label[for="'+id+'"]:visible').click();
 assert.equal(await input.isChecked(),wanted);
}
try{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']});
 const context=await browser.newContext({locale:'en-US',timezoneId:'UTC',serviceWorkers:'block'});
 await context.route('**/*',route=>{const u=new URL(route.request().url());return u.protocol==='http:'&&['localhost','127.0.0.1'].includes(u.hostname)&&u.port==='8023'?route.continue():route.abort();});
 page=await context.newPage();page.setDefaultTimeout(20000);
 page.on('response',r=>{const q=r.request(),u=new URL(q.url());if(!['GET','HEAD'].includes(q.method())&&u.pathname!='/users/sign_in')result.native_writes.push({method:q.method(),path:u.pathname,status:r.status()});});
 await page.goto(base+'/users/sign_in');await page.getByTestId('username-field').fill(credentials.username);await page.getByTestId('password-field').fill(credentials.password);
 await Promise.all([page.waitForURL(u=>u.pathname!='/users/sign_in'),page.getByTestId('sign-in-button').click()]);
 const csrf=await page.locator('meta[name="csrf-token"]').getAttribute('content');assert.ok(csrf);
 async function api(method,url,body,expected=200){const r=await context.request.fetch(base+url,{method,data:body,headers:{'X-CSRF-Token':csrf},timeout:30000});result.api_requests.push({method,path:url,body,status:r.status()});await save();assert.equal(r.status(),expected,method+' '+url);return r.json();}
 const actor=await api('GET','/api/v4/user');assert.equal(actor.id,2330);result.actor={id:actor.id,username:actor.username};
 result.stage='preflight';await api('GET','/api/v4/projects/'+encodeURIComponent(path),undefined,404);result.preflight_project_absent=true;
 result.stage='producer';await save();let id;
 if(a.branch==='native_native'){
  await step('open_project_form',()=>page.goto(base+'/projects/new'));await step('select_blank_project',()=>page.locator('a[href="#blank_project"]').click());
  await step('project_name',async()=>{await page.locator('#project_name:visible').pressSequentially(name);await page.locator('#project_name:visible').press('Tab');});
  await step('wait_generated_path',()=>page.waitForFunction(expected=>{
   const visible=id=>[...document.querySelectorAll('#'+id)].find(n=>n.getClientRects().length);
   return visible('project_name')?.value===expected&&visible('project_path')?.value===expected;
  },name,{timeout:20000}));
  await step('description_empty',()=>page.locator('#project_description:visible').fill(''));
  await step('private_visibility',()=>checkedViaLabel('project_visibility_level_0',true));
  await step('disable_readme',()=>checkedViaLabel('project_initialize_with_readme',false));
  await step('disable_sast',()=>checkedViaLabel('project_initialize_with_sast',false));
  result.project_form_before_submit={name:await page.locator('#project_name:visible').inputValue(),path:await page.locator('#project_path:visible').inputValue(),private:await page.locator('#project_visibility_level_0:visible').isChecked(),readme:await page.locator('#project_initialize_with_readme:visible').isChecked(),sast:await page.locator('#project_initialize_with_sast:visible').isChecked()};await save();
  assert.deepEqual(result.project_form_before_submit,{name,path:name,private:true,readme:false,sast:false});
  await step('submit_project',()=>Promise.all([page.waitForURL(u=>u.pathname==='/'+path),page.getByRole('button',{name:'Create project',exact:true}).filter({visible:true}).click()]));
  id=(await api('GET','/api/v4/projects/'+encodeURIComponent(path))).id;
 }else{id=(await api('POST','/api/v4/projects',{name,path:name,description:'',visibility:'private',initialize_with_readme:false},201)).id;}
 result.project_id=id;
 const before=business(await api('GET','/api/v4/projects/'+id));result.producer_state=before;
 assert.equal(before.name,name);assert.equal(before.path_with_namespace,path);assert.equal(before.visibility,'private');assert.equal(before.empty_repo,true);
 assert.equal(before.description,'');assert.equal(before.default_branch,null);
 result.stage='continuation';await save();
 if(a.branch==='api_api'){
  await step('api_create_readme',()=>api('POST',`/api/v4/projects/${id}/repository/files/README.md`,{branch:'main',content:expected,commit_message:commitMessage},201));
 }else{
  const qa=n=>page.locator('[data-qa-selector="'+n+'"]:visible');
  await step('open_web_ide',()=>page.goto(base+'/-/ide/project/'+path+'/edit/main'));
  await step('create_first_file',()=>qa('first_file_button').click());
  await step('filename',()=>qa('file_name_field').fill('README.md'));
  await step('create_file',()=>page.getByRole('button',{name:'Create file',exact:true}).click());
  await step('editor_content',async()=>{const editor=qa('editor_container').locator('textarea.inputarea:visible');assert.equal(await editor.count(),1);await editor.click();await page.keyboard.press('Control+a');await page.keyboard.insertText(expected);});
  await step('begin_commit',()=>qa('begin_commit_button').click());
  await step('commit_message',()=>qa('ide_commit_message_field').fill(commitMessage));
  await step('current_branch',async()=>{const box=qa('commit_to_current_branch_radio_container');assert.match(await box.innerText(),/Commit to main branch/);await box.locator('input[type=radio]').check();});
  await step('submit_commit',async()=>{await Promise.all([page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname.includes('/repository/commits')&&r.status()===201,{timeout:30000}),qa('commit_button').click()]);});
 }
 const final=business(await api('GET','/api/v4/projects/'+id));result.final_state=final;
 assert.equal(final.default_branch,'main');assert.equal(final.empty_repo,false);
 const preserved=p=>Object.fromEntries(Object.entries(p).filter(([k])=>!['empty_repo','default_branch'].includes(k)));
 assert.deepEqual(preserved(final),preserved(before));
 const file=await api('GET',`/api/v4/projects/${id}/repository/files/README.md?ref=main`);
 result.final_file={path:file.file_path,encoding:file.encoding,content:Buffer.from(file.content,'base64').toString('utf8'),commit_id:file.commit_id,blob_id:file.blob_id};
 assert.equal(result.final_file.path,'README.md');assert.equal(result.final_file.content,expected);
 const tree=await api('GET',`/api/v4/projects/${id}/repository/tree?ref=main&recursive=true&per_page=100`);
 result.final_tree=tree.map(x=>({path:x.path,type:x.type,mode:x.mode}));assert.deepEqual(result.final_tree,[{path:'README.md',type:'blob',mode:'100644'}]);
 const branches=await api('GET',`/api/v4/projects/${id}/repository/branches?per_page=100`);result.final_branches=branches.map(b=>({name:b.name,default:b.default}));assert.deepEqual(result.final_branches,[{name:'main',default:true}]);
 const commits=await api('GET',`/api/v4/projects/${id}/repository/commits?ref_name=main&per_page=100`);result.final_commits=commits.map(c=>({id:c.id,message:c.message,parent_ids:c.parent_ids}));assert.equal(commits.length,1);assert.equal(commits[0].parent_ids.length,0);assert.equal(commits[0].message.trim(),commitMessage);
 result.ordinary_control_passed=true;result.stage='complete';
}catch(e){result.error_type=e.name;result.error=e.name==='AssertionError'?String(e.message).slice(0,600):'Instrument step failed; inspect stage and visible controls.';process.exitCode=1;
 if(page){try{result.failure_path=new URL(page.url()).pathname;result.failure_fields=await page.locator('input:not([type=hidden]):not([type=password]),textarea,button,select,label,[role=option],[role=listbox]').evaluateAll(ns=>ns.filter(n=>n.getClientRects().length).map(n=>({tag:n.tagName,name:n.name,id:n.id,type:n.type,role:n.getAttribute('role'),placeholder:n.getAttribute('placeholder'),value:['INPUT','TEXTAREA','SELECT'].includes(n.tagName)?n.value:undefined,text:['BUTTON','SELECT','LABEL'].includes(n.tagName)||n.getAttribute('role')==='option'?n.innerText.trim():null})));}catch{}}
}finally{if(browser)await browser.close();result.browser_cleanup_confirmed=true;await save();}
