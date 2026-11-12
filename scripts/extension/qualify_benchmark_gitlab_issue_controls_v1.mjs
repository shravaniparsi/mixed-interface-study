/** Ordinary triple qualification, one fresh-container branch per invocation. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {parseArgs} from 'node:util';
const {values:a}=parseArgs({options:{credentials:{type:'string'},out:{type:'string'},branch:{type:'string'}}});
assert.ok(['native_native','api_native','api_api'].includes(a.branch));
const credentials=JSON.parse(await readFile(a.credentials,'utf8'));
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
const base='http://127.0.0.1:8023',project=183,title='Integrating LLMs for better prompts',description='Continuation control',due='2033-04-01',assignee=2264;
const result={kind:'benchmark_gitlab_issue_control_v1',branch:a.branch,scientific_cases_executed:0,ordinary_control_passed:false,stage:'start',api_requests:[],native_writes:[],blocked_external_requests:0};
await mkdir(a.out,{recursive:true});const save=()=>writeFile(a.out+'/issue-control.json',JSON.stringify(result,null,2)+'\n');
let browser,page;
const business=x=>({project_id:x.project_id,title:x.title,description:x.description,confidential:x.confidential,issue_type:x.issue_type,state:x.state,labels:x.labels,milestone_id:x.milestone?.id??null,assignee_ids:(x.assignees??[]).map(u=>u.id).sort((a,b)=>a-b),due_date:x.due_date});
try{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']});
 const context=await browser.newContext({locale:'en-US',timezoneId:'UTC'});
 await context.route('**/*',async route=>{const u=new URL(route.request().url());if(u.protocol==='http:'&&['localhost','127.0.0.1'].includes(u.hostname)&&u.port==='8023')return route.continue();result.blocked_external_requests++;return route.abort();});
 page=await context.newPage();page.setDefaultTimeout(20000);
 page.on('response',r=>{const q=r.request(),u=new URL(q.url());if(!['GET','HEAD'].includes(q.method())&&u.pathname!='/users/sign_in')result.native_writes.push({method:q.method(),path:u.pathname,status:r.status()});});
 await page.goto(base+'/users/sign_in');await page.getByTestId('username-field').fill(credentials.username);await page.getByTestId('password-field').fill(credentials.password);
 await Promise.all([page.waitForURL(u=>u.pathname!='/users/sign_in'),page.getByTestId('sign-in-button').click()]);
 const csrf=await page.locator('meta[name="csrf-token"]').getAttribute('content');assert.ok(csrf);
 async function api(method,path,body,expected=200){
  const r=await context.request.fetch(base+path,{method,data:body,headers:{'X-CSRF-Token':csrf},timeout:30000});
  result.api_requests.push({method,path,body,status:r.status()});await save();assert.equal(r.status(),expected,method+' '+path);
  return r.json();
 }
 const actor=await api('GET','/api/v4/user');assert.equal(actor.id,2330);result.actor={id:actor.id,username:actor.username};
 result.stage='fixture_setup';
 const existing=await api('GET','/api/v4/projects/183/issues?search='+encodeURIComponent(title)+'&in=title&per_page=100');
 assert.ok(existing.length<100&&!existing.some(i=>i.title===title),'Existing target issue; reset precondition failed');
 const memberResponse=await context.request.get(base+'/api/v4/projects/183/members/all/2264');
 result.assignee_membership_initial_status=memberResponse.status();
 if(memberResponse.status()===404){await api('POST','/api/v4/projects/183/members',{user_id:2264,access_level:30},201);result.assignee_membership_setup='added_developer';}
 else {assert.equal(memberResponse.status(),200);const m=await memberResponse.json();assert.ok(m.access_level>=20);result.assignee_membership_setup='already_authorized';}
 if(a.branch==='native_native'){
  try{
   const patch=await api('GET','/api/v4/projects/174/repository/commits/2b3ec149575466e9994d7b7709fcac6b317d5954/diff?per_page=100');
   await writeFile(a.out+'/mr-candidate-commit-diff.json',JSON.stringify({commit:'2b3ec149575466e9994d7b7709fcac6b317d5954',diffs:patch,may_be_truncated:patch.length===100},null,2)+'\n');
  }catch(e){result.mr_commit_inspection_error_type=e.name;await save();}
 }
 result.stage='producer';await save();let iid;
 if(a.branch==='native_native'){
  await page.goto(base+'/byteblaze/empathy-prompts/-/issues/new');
  await page.locator('#issue_title').fill(title);await page.locator('#issue_description').fill(description);await page.locator('#issue_confidential').uncheck();
  await Promise.all([page.waitForURL(u=>/\/issues\/\d+$/.test(u.pathname)),page.getByRole('button',{name:'Create issue',exact:true}).click()]);
  iid=Number(new URL(page.url()).pathname.split('/').at(-1));
 }else{const created=await api('POST','/api/v4/projects/183/issues',{title,description,confidential:false},201);iid=created.iid;}
 assert.ok(Number.isInteger(iid)&&iid>0);result.issue_iid=iid;
 const before=business(await api('GET',`/api/v4/projects/183/issues/${iid}`));result.producer_state=before;
 assert.equal(before.title,title);assert.equal(before.description,description);assert.equal(before.confidential,false);assert.deepEqual(before.assignee_ids,[]);assert.equal(before.due_date,null);
 result.stage='continuation';await save();
 if(a.branch==='api_api'){
  await api('PUT',`/api/v4/projects/183/issues/${iid}`,{assignee_ids:[assignee],due_date:due});
 }else{
  await page.goto(base+`/byteblaze/empathy-prompts/-/issues/${iid}/edit`);
  await page.locator('#issuable-due-date').fill(due);await page.locator('#issuable-due-date').press('Tab');
  await page.getByRole('button',{name:'Unassigned',exact:true}).click();
  const search=page.locator('input[placeholder*="Search users"]:visible');assert.equal(await search.count(),1);await search.fill('Roshanjossey');
  const candidate=page.locator('.dropdown-menu:visible a').filter({hasText:'Roshanjossey'});await candidate.waitFor({state:'visible'});assert.equal(await candidate.count(),1);await candidate.click();
  await Promise.all([page.waitForURL(u=>u.pathname.endsWith('/issues/'+iid)),page.getByRole('button',{name:'Save changes',exact:true}).click()]);
 }
 const after=business(await api('GET',`/api/v4/projects/183/issues/${iid}`));result.final_state=after;
 assert.deepEqual(after,{...before,assignee_ids:[assignee],due_date:due});
 result.ordinary_control_passed=true;result.stage='complete';
}catch(e){result.error_type=e.name;result.error=e.name==='AssertionError'?String(e.message).slice(0,600):'Instrument step failed; inspect retained stage and form inventory.';process.exitCode=1;
 if(page){try{result.failure_path=new URL(page.url()).pathname;result.failure_fields=await page.locator('input:not([type=hidden]):not([type=password]),textarea,button').evaluateAll(ns=>ns.filter(n=>n.getClientRects().length).map(n=>({tag:n.tagName,name:n.name,id:n.id,type:n.type,placeholder:n.getAttribute('placeholder'),text:n.tagName==='BUTTON'?n.innerText.trim():null})));}catch{}}
}finally{if(browser)await browser.close();await save();}
