/** Read-only native-form and MR branch qualification; no scientific cases. */
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {parseArgs} from 'node:util';
import {createHash} from 'node:crypto';
const {values:a}=parseArgs({options:{credentials:{type:'string'},out:{type:'string'}}});
const credentials=JSON.parse(await readFile(a.credentials,'utf8'));
const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);
const base='http://127.0.0.1:8023';
const result={kind:'benchmark_gitlab_browser_inspection_v1',scientific_cases_executed:0,business_object_writes:0,forms:[],branch_comparisons:[],blocked_requests:[]};
await mkdir(a.out,{recursive:true});
const save=()=>writeFile(a.out+'/browser-inspection.json',JSON.stringify(result,null,2)+'\n');
const sha=s=>createHash('sha256').update(s).digest('hex');
let browser;
try {
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']});
 const context=await browser.newContext({locale:'en-US',timezoneId:'UTC'});
 let loginPermitted=true;
 await context.route('**/*',async route=>{
  const req=route.request(),u=new URL(req.url());
  const local=u.protocol==='http:'&&['localhost','127.0.0.1'].includes(u.hostname)&&u.port==='8023';
  const allowed=local&&(['GET','HEAD'].includes(req.method())||(loginPermitted&&req.method()==='POST'&&u.pathname==='/users/sign_in'));
  if(allowed) return route.continue();
  result.blocked_requests.push({method:req.method(),path:u.pathname,external:!local});return route.abort();
 });
 const page=await context.newPage();page.setDefaultTimeout(20000);
 await page.goto(base+'/users/sign_in');
 await page.getByTestId('username-field').fill(credentials.username);
 await page.getByTestId('password-field').fill(credentials.password);
 await Promise.all([page.waitForURL(u=>u.pathname!='/users/sign_in'),page.getByTestId('sign-in-button').click()]);
 loginPermitted=false;
 async function api(path){
  const r=await context.request.get(base+path,{timeout:20000});
  if(r.status()!==200)throw new Error('API_GET_'+r.status()+'_'+path.split('?')[0]);
  return r.json();
 }
 const actor=await api('/api/v4/user');
 if(actor.username!==credentials.username)throw new Error('ActorMismatch');
 result.actor={id:actor.id,username:actor.username};
 async function inspect(name,path){
  const response=await page.goto(base+path,{waitUntil:'domcontentloaded'});
  await page.locator('body').waitFor();
  let networkIdle=true;try{await page.waitForLoadState('networkidle',{timeout:10000});}catch{networkIdle=false;}
  const record={name,path,network_idle_observed:networkIdle,status:response?.status(),final_path:new URL(page.url()).pathname};
  record.fields=await page.locator('input:not([type=hidden]):not([type=password]),textarea,select,button').evaluateAll(nodes=>nodes.map(n=>({tag:n.tagName.toLowerCase(),name:n.getAttribute('name'),id:n.id,type:n.getAttribute('type'),testid:n.getAttribute('data-testid'),label:n.labels?[...n.labels].map(l=>l.innerText.trim()).join(' '):null,text:n.tagName==='BUTTON'?n.innerText.trim():null,required:n.required||false,disabled:n.disabled||false,maxlength:n.getAttribute('maxlength'),pattern:n.getAttribute('pattern'),checked:['checkbox','radio'].includes(n.type)?n.checked:null,options:n.tagName==='SELECT'?[...n.options].map(o=>({value:o.value,text:o.text,selected:o.selected})):undefined})).filter(n=>n.name||n.id||n.text||n.label));
  record.links=await page.locator('a').evaluateAll(nodes=>nodes.map(n=>({text:n.innerText.trim(),path:n.getAttribute('href')})).filter(n=>/blank project|create project|new issue|merge request|invite member/i.test(n.text)).slice(0,40));
  result.forms.push(record);await save();
 }
 for(const [name,path] of [['project_new','/projects/new'],['issue_new','/byteblaze/empathy-prompts/-/issues/new'],['mr_new','/a11yproject/a11yproject.com/-/merge_requests/new'],['existing_project_members','/byteblaze/empathy-prompts/-/project_members']]){
  try{await inspect(name,path);}catch(e){result.forms.push({name,path,error_type:e.name});await save();}
 }
 const previous=JSON.parse(await readFile('manifests/benchmark-gitlab-auth-v2.json','utf8'));
 const branches=previous.mr_branch_candidates.filter(b=>!b.default).map(b=>b.name).sort();
 for(const branch of branches){
  const row={branch};
  try{
   const data=await api('/api/v4/projects/174/repository/compare?'+new URLSearchParams({from:'main',to:branch,straight:'true'}));
   row.compare_timeout=data.compare_timeout??null;row.compare_same_ref=data.compare_same_ref??null;
   row.commit_count=data.commits?.length??null;
   row.commits=(data.commits??[]).map(c=>({id:c.id,title:c.title,message:c.message?.slice(0,3000)}));
   row.diffs=(data.diffs??[]).map(d=>{
    const lines=(d.diff??'').split('\n'),matches=[];
    for(let i=0;i<lines.length;i++)if(/template[\s_-]*(?:strings?|literals?)|interpolat/i.test(lines[i]))matches.push({line_index:i,context:lines.slice(Math.max(0,i-2),i+3)});
    return {old_path:d.old_path,new_path:d.new_path,diff_sha256:sha(d.diff??''),diff_characters:(d.diff??'').length,collapsed:d.collapsed??null,too_large:d.too_large??null,matches:matches.slice(0,30),matches_truncated:matches.length>30};
   });
   row.scope='Lexical clues and commit messages only; lack of a hit does not prove absence of semantic support.';
  }catch(e){row.error_type=e.name;row.error=e.message.startsWith('API_GET_')?e.message:'request_failed';}
  result.branch_comparisons.push(row);await save();
 }
 result.inspection_completed=true;
}catch(e){result.error_type=e.name;result.inspection_completed=false;process.exitCode=1;}
finally{if(browser)await browser.close();await save();}
