/** Inspect the selected MR producer form; never submit a business write. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {parseArgs} from 'node:util';
const {values:a}=parseArgs({options:{credentials:{type:'string'},out:{type:'string'}}});
const credentials=JSON.parse(await readFile(a.credentials,'utf8'));
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
const base='http://127.0.0.1:8023',project=174,source='feature/replace-gulp',target='main';
const result={kind:'benchmark_gitlab_mr_form_inspection_v1',scientific_cases_executed:0,business_writes_permitted:false,forms:[],blocked_requests:[],api_reads:[],stage:'login'};
await mkdir(a.out,{recursive:true});const save=()=>writeFile(a.out+'/mr-form-inspection.json',JSON.stringify(result,null,2)+'\n');
let browser,page,loginPermitted=true;
try{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']});
 const context=await browser.newContext({locale:'en-US',timezoneId:'UTC',serviceWorkers:'block'});
 await context.route('**/*',route=>{const q=route.request(),u=new URL(q.url());const local=u.protocol==='http:'&&['localhost','127.0.0.1'].includes(u.hostname)&&u.port==='8023';
  if(local&&(['GET','HEAD'].includes(q.method())||(loginPermitted&&q.method()==='POST'&&u.pathname==='/users/sign_in')))return route.continue();
  result.blocked_requests.push({method:q.method(),path:u.pathname,external:!local});return route.abort();});
 page=await context.newPage();page.setDefaultTimeout(20000);
 await page.goto(base+'/users/sign_in');await page.getByTestId('username-field').fill(credentials.username);await page.getByTestId('password-field').fill(credentials.password);
 await Promise.all([page.waitForURL(u=>u.pathname!='/users/sign_in'),page.getByTestId('sign-in-button').click()]);loginPermitted=false;
 async function get(path){const r=await context.request.get(base+path,{timeout:30000});result.api_reads.push({path,status:r.status()});assert.equal(r.status(),200);return r.json();}
 const actor=await get('/api/v4/user');assert.equal(actor.id,2330);result.actor={id:actor.id,username:actor.username};
 const p=await get('/api/v4/projects/'+project);assert.equal(p.path_with_namespace,'a11yproject/a11yproject.com');assert.equal(p.default_branch,target);
 result.branch_identities=[];
 for(const branch of [source,target]){const b=await get(`/api/v4/projects/${project}/repository/branches/${encodeURIComponent(branch)}`);result.branch_identities.push({name:b.name,commit:b.commit.id});}
 const matches=await get(`/api/v4/projects/${project}/merge_requests?state=opened&source_branch=${encodeURIComponent(source)}&target_branch=${target}&per_page=100`);
 result.existing_matching_mrs={count:matches.length,truncation_possible:matches.length===100,ids:matches.map(x=>x.iid)};assert.ok(matches.length<100);
 async function inventory(label){
  try{await page.waitForLoadState('networkidle',{timeout:10000});}catch{}
  const fields=await page.locator('input:not([type=hidden]):not([type=password]),textarea,select,button,label,[role=option]').evaluateAll(ns=>ns.filter(n=>n.getClientRects().length).map(n=>({tag:n.tagName,id:n.id,name:n.name,type:n.type,testid:n.getAttribute('data-testid'),role:n.getAttribute('role'),placeholder:n.getAttribute('placeholder'),text:['BUTTON','LABEL','OPTION'].includes(n.tagName)||n.getAttribute('role')==='option'?n.innerText.trim():null,value:['INPUT','TEXTAREA','SELECT'].includes(n.tagName)?n.value:undefined,checked:['checkbox','radio'].includes(n.type)?n.checked:undefined,options:n.tagName==='SELECT'?[...n.options].map(o=>({value:o.value,text:o.text,selected:o.selected})):undefined})));
  result.forms.push({label,path:new URL(page.url()).pathname,fields});await save();
 }
 result.stage='open_bound_form';await save();
 const params=new URLSearchParams({'merge_request[source_branch]':source,'merge_request[target_branch]':target});
 const response=await page.goto(base+'/a11yproject/a11yproject.com/-/merge_requests/new?'+params);result.page_status=response.status();assert.equal(response.status(),200);
 await inventory('bound_creation_form');
 // Opening the native reviewer dropdown changes only UI state. If unavailable, retain that fact.
 const reviewer=page.locator('button:visible').filter({hasText:/reviewer/i});result.reviewer_button_count=await reviewer.count();
 if(result.reviewer_button_count===1){result.stage='open_reviewer_dropdown';await save();await reviewer.click();await inventory('reviewer_dropdown');}
 result.stage='complete';result.inspection_completed=true;
}catch(e){result.error_type=e.name;result.inspection_completed=false;process.exitCode=1;}
finally{if(browser)await browser.close();result.browser_cleanup_confirmed=true;await save();}
