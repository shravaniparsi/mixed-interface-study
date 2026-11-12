/** Ordinary triple qualification, one fresh-container branch per invocation. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {parseArgs} from 'node:util';
const {values:a}=parseArgs({options:{credentials:{type:'string'},out:{type:'string'},branch:{type:'string'},case:{type:'string'}}});
assert.ok(['native_native','api_native','api_api'].includes(a.branch));
const credentials=JSON.parse(await readFile(a.credentials,'utf8'));
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
const registration=JSON.parse(await readFile('manifests/benchmark-gitlab-issue-execution-v1.json','utf8'));
const spec=registration.cases.find(c=>c.id===a.case);assert.ok(spec);
const patch=spec.optional_field_patch;
const base='http://127.0.0.1:8023',project=183,title='Integrating LLMs for better prompts',due='2033-04-01',assignee=2264;
const result={kind:'benchmark_gitlab_issue_case_v1',case_id:a.case,case_role:spec.role,optional_field_patch:patch,branch:a.branch,scientific_cases_executed:0,case_passed:false,stage:'start',api_requests:[],native_writes:[],blocked_external_requests:0};
await mkdir(a.out,{recursive:true});const save=()=>writeFile(a.out+'/issue-case.json',JSON.stringify(result,null,2)+'\n');
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
 result.preflight={returned_count:existing.length,exact_title_count:existing.filter(i=>i.title===title).length,may_be_truncated:existing.length===100};await save();
 assert.ok(existing.length<100&&result.preflight.exact_title_count===0,'Existing target issue; reset precondition failed');
 const memberResponse=await context.request.get(base+'/api/v4/projects/183/members/all/2264');
 result.assignee_membership_initial_status=memberResponse.status();
 if(memberResponse.status()===404){await api('POST','/api/v4/projects/183/members',{user_id:2264,access_level:30},201);result.assignee_membership_setup='added_developer';}
 else {assert.equal(memberResponse.status(),200);const m=await memberResponse.json();assert.ok(m.access_level>=20);result.assignee_membership_setup='already_authorized';}
 result.stage='producer';result.scientific_cases_executed=spec.role==='scientific'?1:0;await save();let iid;
 if(a.branch==='native_native'){
  await page.goto(base+'/byteblaze/empathy-prompts/-/issues/new');
  await page.locator('#issue_title').fill(title);if(Object.hasOwn(patch,'description'))await page.locator('#issue_description').fill(patch.description);await page.locator('#issue_confidential').setChecked(patch.confidential??false);
  result.native_description_realization=Object.hasOwn(patch,'description')?'explicit_text':'leave_blank_native_default';
  await Promise.all([page.waitForURL(u=>/\/issues\/\d+$/.test(u.pathname)),page.getByRole('button',{name:'Create issue',exact:true}).click()]);
  iid=Number(new URL(page.url()).pathname.split('/').at(-1));
 }else{const created=await api('POST','/api/v4/projects/183/issues',{title,...patch},201);iid=created.iid;}
 assert.ok(Number.isInteger(iid)&&iid>0);result.issue_iid=iid;
 const before=business(await api('GET',`/api/v4/projects/183/issues/${iid}`));result.producer_state=before;
 assert.equal(before.title,title);if(patch.description)assert.equal(before.description,patch.description);if(patch.description==='')assert.ok(before.description===''||before.description===null);assert.equal(before.confidential,patch.confidential??false);assert.deepEqual(before.assignee_ids,[]);assert.equal(before.due_date,null);
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
 result.case_passed=true;result.stage='complete';
}catch(e){result.error_type=e.name;result.error=e.name==='AssertionError'?String(e.message).slice(0,600):'Instrument step failed; inspect retained stage and form inventory.';process.exitCode=1;
 if(page){try{result.failure_path=new URL(page.url()).pathname;result.failure_fields=await page.locator('input:not([type=hidden]):not([type=password]),textarea,button').evaluateAll(ns=>ns.filter(n=>n.getClientRects().length).map(n=>({tag:n.tagName,name:n.name,id:n.id,type:n.type,placeholder:n.getAttribute('placeholder'),text:n.tagName==='BUTTON'?n.innerText.trim():null})));}catch{}}
}finally{if(browser)await browser.close();result.browser_cleanup_confirmed=true;await save();}
