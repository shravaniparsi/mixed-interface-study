#!/usr/bin/env node
/** Native Quartz Manager positive control. No failure-search or selector tuning. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import {existsSync, createWriteStream} from 'node:fs';
import {mkdir, readFile, writeFile, statfs} from 'node:fs/promises';
import {resolve, join} from 'node:path';
import {parseArgs} from 'node:util';
import net from 'node:net';

const {values} = parseArgs({options: {
  help:{type:'boolean'}, runtime:{type:'string'}, output:{type:'string'},
  java:{type:'string'}, 'playwright-module':{type:'string'}, 'chrome-executable':{type:'string'},
}});
if (values.help) {
  console.log('Usage: node quartz_transfer_control.mjs --runtime DIR --java JAVA --output NEW_DIR --playwright-module MODULE --chrome-executable CHROME\nRequires the pinned official 5.0.1 showcase and UI jars. Runs four independently restarted RAM-store routes on loopback port 19965. Never creates triggers or starts the scheduler.');
  process.exit(0);
}
for (const name of ['runtime','java','output','playwright-module','chrome-executable']) assert.ok(values[name], `--${name} is required`);
const runtime = resolve(values.runtime), out = resolve(values.output);
assert.ok(!existsSync(out), 'Evidence directory already exists; choose a fresh output directory.');
const base = 'http://127.0.0.1:19965';
const showcase = join(runtime, 'quartz-manager-web-showcase-5.0.1.jar');
const uiJar = join(runtime, 'quartz-manager-starter-ui-5.0.1.jar');
const digests = {
  [showcase]:'d043fe19a11c61d9dc3117c3a84ccaa134fe083aee4145e0f0e2bee84a83a826',
  [uiJar]:'5a06dacd7bc06f46800606ddf8a46857a866ba622a372ba85312547507c3e320',
};
const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])])) : value;
const sha = value => createHash('sha256').update(typeof value === 'string' || Buffer.isBuffer(value) ? value : JSON.stringify(canonical(value))).digest('hex');
for (const [file,digest] of Object.entries(digests)) assert.equal(sha(await readFile(file)), digest, 'Pinned release artifact checksum');
const dependencyBytes=await readFile(join(runtime,'declared-dependencies.json'));
assert.equal(sha(dependencyBytes),'acfba9a7323d951fbea0fc39536aa6ead718d5bff1aca5c3d18ea27ef64d8968','Pinned dependency metadata');
const dependencyFiles=JSON.parse(dependencyBytes).map(item=>({file:join(runtime,item.name),sha256:item.sha256}));
for(const item of dependencyFiles)assert.equal(sha(await readFile(item.file)),item.sha256,'Pinned declared dependency checksum');
const disk = await statfs(runtime); assert.ok(disk.bavail*disk.bsize > 400*1024**2, 'Disk floor: 400 MiB');
await new Promise((ok,fail)=>{const probe=net.createServer();probe.once('error',fail);probe.listen(19965,'127.0.0.1',()=>probe.close(ok));});
await mkdir(out,{recursive:true});
await writeFile(join(out,'executed-runner.mjs'),await readFile(new URL(import.meta.url)));
const require = createRequire(import.meta.url);
const {chromium} = require(values['playwright-module']);
const jobPath = '/quartz-manager/jobs/RESEARCH/pilot-job';
const before = 'Description before continuation.';
const after = 'Description after meaningful continuation.';
const command = description => ({jobClass:'it.fabioformosa.quartzmanager.jobs.myjobs.SampleJob',description,durable:true,requestsRecovery:false,jobDataMap:{}});
const expectedJob = description => ({jobKeyDTO:{name:'pilot-job',group:'RESEARCH'},jobClassName:command(description).jobClass,description,durable:true,requestsRecovery:false,jobDataMap:{},triggerKeys:[]});
const allowedMutation = (method,path) => method === 'POST' && path === '/quartz-manager/auth/login' || ['POST','PUT'].includes(method) && path === jobPath;
let browser, child;
const summary = {schema_version:1,kind:'new_application_positive_control',subject:'quartz-manager-standalone',release:'5.0.1',release_commit:'71bc29df2a98490b436094666249b3a2a1207cc4',started_at:new Date().toISOString(),routes:[],native_unit_suite_executed:false,application_source_modified:false,method_or_oracle_policy_tuned:false,interpretation:'One ordinary workflow, one repetition per route: deployment and operation-mapping feasibility only; not held-out failure-detection effectiveness.'};
const sleep = ms => new Promise(r=>setTimeout(r,ms));
function actor(body) { return {username:body?.username,authorities:body?.authorities}; }
function checkActor(body) { const a=actor(body);assert.equal(a.username,'admin');assert.ok(JSON.stringify(a.authorities).includes('ADMIN'));return a; }
async function stopServer() {
  if (!child) return;
  const p=child;child=undefined;
  if(p.exitCode===null) {p.kill('SIGTERM');await Promise.race([new Promise(r=>p.once('exit',r)),sleep(8000)]);}
  if(p.exitCode===null && !p.signalCode) {p.kill('SIGKILL');await new Promise(r=>p.once('exit',r));}
}
async function startServer(route) {
  const log=createWriteStream(join(out,`${route}-server.log`),{flags:'wx'});
  const args=['-Xmx256m','-Duser.timezone=Europe/Rome',`-Dloader.path=${[uiJar,...dependencyFiles.map(x=>x.file)].join(',')}`,'-cp',showcase,'org.springframework.boot.loader.launch.PropertiesLauncher','--server.address=127.0.0.1','--server.port=19965'];
  child=spawn(values.java,args,{cwd:runtime,stdio:['ignore','pipe','pipe']});
  child.stdout.pipe(log); child.stderr.pipe(log);
  child.once('close',()=>log.end());
  let startupError;
  child.once('error',e=>{startupError=e;});
  for(let i=0;i<160;i++) {
    if(startupError) throw startupError;
    if(child.exitCode!==null) throw new Error(`Native server exited ${child.exitCode}; inspect server log.`);
    try {const r=await fetch(base+'/quartz-manager-ui/index.html',{signal:AbortSignal.timeout(1000)});if(r.status===200) return {status:r.status,html_sha256:sha(await r.text()),pid:child.pid};} catch {}
    await sleep(250);
  }
  throw new Error('Native UI not ready in 40 seconds.');
}

async function runRoute(route) {
  const result={route,started_at:new Date().toISOString(),outcome:'running',phase:'startup',trace:[],checks:[],ui_forms:[],blocked_requests:[],page_errors:[],normalization:'JSON object key order only; no stored job, trigger or scheduler fields omitted.'};
  const captures=[];let token;let ctx;let page;let sequence=0;
  const event = value => result.trace.push({sequence:++sequence,phase:result.phase,...value});
  async function api(method,path,body,expected=200) {
    assert.ok(path.startsWith('/quartz-manager/'));assert.ok(method==='GET'||allowedMutation(method,path),'Only fixed safe control writes are permitted.');
    const headers={Accept:'application/json'};if(token)headers.Authorization=token;
    if(body!==undefined)headers['Content-Type']='application/json';
    const res=await fetch(base+path,{method,headers,body:body===undefined?undefined:JSON.stringify(body),redirect:'manual',signal:AbortSignal.timeout(15000)});
    let data;try{data=await res.json();}catch{data=null;}
    event({source:'direct_api',method,path,request:body??null,status:res.status,response:path.endsWith('/whoami')?actor(data):data});
    assert.equal(res.status,expected,`${method} ${path}`);return data;
  }
  async function snapshot(label) {
    const scheduler=await api('GET','/quartz-manager/scheduler');
    const jobs=await api('GET','/quartz-manager/jobs');const triggers=await api('GET','/quartz-manager/triggers');
    assert.ok(['STOPPED','PAUSED'].includes(scheduler.status),`Scheduler must remain inactive, got ${scheduler.status}`);
    assert.equal(scheduler.numberOfJobsExecuted,0);assert.equal(scheduler.jobStoreSupportsPersistence,false);assert.ok(scheduler.jobStoreClass.includes('RAMJobStore'));
    assert.deepEqual(triggers,[]);assert.deepEqual(scheduler.triggerKeys,[]);
    const state={scheduler,jobs,triggers};result[label]=state;result[label+'_sha256']=sha(state);return state;
  }
  async function closeUI() {if(ctx){await ctx.close();ctx=undefined;page=undefined;}await Promise.allSettled(captures);}
  async function openUI() {
    await closeUI();ctx=await browser.newContext({viewport:{width:1440,height:1000},locale:'en-US',timezoneId:'UTC',serviceWorkers:'block'});
    await ctx.route('**/*',async r=>{
      const req=r.request(),u=new URL(req.url());
      const local=u.origin===base;
      if(!local||(!['GET','HEAD','OPTIONS'].includes(req.method())&&!allowedMutation(req.method(),u.pathname))) {result.blocked_requests.push({method:req.method(),url:u.origin+u.pathname});return r.abort('blockedbyclient');}
      return r.continue();
    });
    page=await ctx.newPage();page.setDefaultTimeout(15000);
    page.on('pageerror',e=>result.page_errors.push(String(e)));
    page.on('response',res=>{
      const req=res.request(),u=new URL(res.url());if(!u.pathname.startsWith('/quartz-manager/'))return;
      if(u.pathname.includes('/websocket'))return;
      captures.push((async()=>{
        let body;try{body=await res.json();}catch{body=null;}
        let request=null;if(req.postData()&&!u.pathname.includes('/auth/')){try{request=req.postDataJSON();}catch{request='non-json-body';}}
        event({source:'ui_network',method:req.method(),path:u.pathname,request,status:res.status(),response:u.pathname.includes('/auth/')?(u.pathname.endsWith('/whoami')?actor(body):'[authentication response omitted]'):body});
      })());
    });
    await page.goto(base+'/quartz-manager-ui/index.html');
    await page.getByLabel('Username',{exact:true}).fill('admin');await page.getByLabel('Password',{exact:true}).fill('admin');
    const who=page.waitForResponse(r=>new URL(r.url()).pathname==='/quartz-manager/auth/whoami'&&r.status()===200);
    who.catch(()=>{});
    await page.locator('form').getByRole('button',{name:'Login',exact:true}).click();result.ui_actor=checkActor(await(await who).json());
    await page.getByRole('button',{name:'Jobs',exact:true}).click();
    await page.getByRole('button',{name:'New Job',exact:true}).waitFor({state:'visible'});
  }
  const editor = () => page.locator('aside[aria-label="Stored job editor"].drawer-open');
  async function formState(label) {
    const e=editor();const obj={group:await e.locator('[name="jobGroup"]').inputValue(),name:await e.locator('[name="jobName"]').inputValue(),jobClass:await e.locator('[name="storedJobClass"]').inputValue(),description:await e.locator('[name="jobDescription"]').inputValue(),durable:await e.locator('[name="jobDurable"]').isChecked(),requestsRecovery:await e.locator('[name="jobRecovery"]').isChecked(),jobDataMap:JSON.parse(await e.locator('pre.code-block').innerText())};
    result.ui_forms.push({label,...obj});return obj;
  }
  function assertForm(form,description) {assert.deepEqual(form,{group:'RESEARCH',name:'pilot-job',...command(description)});}
  async function openEdit() {
    await page.getByRole('cell',{name:'RESEARCH.pilot-job',exact:true}).click();
    await page.locator('aside[aria-label="Job detail drawer"].drawer-open').getByRole('button',{name:'Edit Job',exact:true}).click();
    await editor().waitFor({state:'visible'});
  }
  async function submit(method,button,status,description) {
    const pending=page.waitForResponse(r=>new URL(r.url()).pathname===jobPath&&r.request().method()===method);
    pending.catch(()=>{});
    await editor().getByRole('button',{name:button,exact:true}).click();const res=await pending;
    assert.equal(res.status(),status);assert.deepEqual(res.request().postDataJSON(),command(description),'Native UI and direct API commands must match.');
    assert.deepEqual(await res.json(),expectedJob(description));await editor().waitFor({state:'hidden'});
  }
  try {
    result.startup=await startServer(route);
    result.phase='authenticate';
    const login=await fetch(base+'/quartz-manager/auth/login',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded',Accept:'application/json'},body:'username=admin&password=admin',redirect:'manual',signal:AbortSignal.timeout(10000)});
    event({source:'direct_api',method:'POST',path:'/quartz-manager/auth/login',status:login.status,request:'[synthetic credentials omitted]',response:'[authentication response omitted]'});
    assert.equal(login.status,200);token=login.headers.get('authorization');assert.ok(token?.startsWith('Bearer '));
    result.api_actor=checkActor(await api('GET','/quartz-manager/auth/whoami'));
    result.phase='reset-verification';const initial=await snapshot('initial_state');assert.deepEqual(initial.jobs,[]);
    assert.ok((await api('GET','/quartz-manager/job-classes')).includes(command(before).jobClass));
    result.checks.push('empty RAM-store reset; zero triggers; scheduler inactive; zero executions; eligible native job class');
    const [writer,consumer]=route.split('-');result.phase='create';
    if(writer==='ui') {
      await openUI();await page.getByRole('button',{name:'New Job',exact:true}).click();
      const e=editor();await e.locator('[name="jobName"]').fill('pilot-job');await e.locator('[name="jobGroup"]').fill('RESEARCH');
      await e.locator('[name="storedJobClass"]').selectOption(command(before).jobClass);await e.locator('[name="jobDescription"]').fill(before);
      await e.locator('[name="jobDurable"]').setChecked(true);await e.locator('[name="jobRecovery"]').setChecked(false);
      assertForm(await formState('native-create'),before);await submit('POST','Create Job',201,before);
    } else assert.deepEqual(await api('POST',jobPath,command(before),201),expectedJob(before));
    result.created_job=await api('GET',jobPath);assert.deepEqual(result.created_job,expectedJob(before));
    result.checks.push('creation persisted every expected business field');
    result.phase='continuation';
    if(consumer==='ui') {
      await openUI();await openEdit();assertForm(await formState('native-continuation-loaded'),before);
      await editor().locator('[name="jobDescription"]').fill(after);assertForm(await formState('native-continuation-submit'),after);
      await submit('PUT','Save Job',200,after);
    } else {
      const loaded=await api('GET',jobPath);assert.deepEqual(loaded,expectedJob(before));
      assert.deepEqual(await api('PUT',jobPath,command(after)),expectedJob(after));
    }
    result.checks.push('fresh consumer read predecessor fields and persisted meaningful description change');
    result.phase='fresh-final-read';result.final_job=await api('GET',jobPath);assert.deepEqual(result.final_job,expectedJob(after));
    await openUI();await openEdit();assertForm(await formState('fresh-native-final-read'),after);
    await page.screenshot({path:join(out,`${route}-final.png`),fullPage:true});
    await editor().getByRole('button',{name:'Cancel',exact:true}).click();
    const final=await snapshot('final_state');assert.deepEqual(final.jobs,[expectedJob(after)]);
    assert.equal(final.scheduler.numberOfJobsExecuted,0);
    assert.deepEqual(result.api_actor,result.ui_actor);
    assert.deepEqual(result.blocked_requests,[],'No attempted request beyond the safe workload allowlist.');
    result.checks.push('fresh native UI and API final reads agree; same actor; no triggers or job execution');
    result.outcome='pass';
  } catch(e) {
    result.outcome='failed';result.error={name:e.name,message:e.message};
    if(page)await page.screenshot({path:join(out,`${route}-failure.png`),fullPage:true}).catch(()=>{});
    await writeFile(join(out,`${route}.json`),JSON.stringify(result,null,2)+'\n');
  } finally {
    await closeUI();await stopServer();result.ended_at=new Date().toISOString();
    await writeFile(join(out,`${route}.json`),JSON.stringify(result,null,2)+'\n');
  }
  return result;
}
try {
  browser=await chromium.launch({headless:true,executablePath:values['chrome-executable'],args:['--disable-background-networking']});
  summary.browser_version=browser.version();summary.node_version=process.version;
  for(const route of ['ui-ui','api-ui','ui-api','api-api']) {
    const r=await runRoute(route);summary.routes.push({route,outcome:r.outcome,initial_state_sha256:r.initial_state_sha256,final_state_sha256:r.final_state_sha256,error:r.error});
    console.log(JSON.stringify(summary.routes.at(-1)));
    if(r.outcome!=='pass')break;
  }
  summary.outcome=summary.routes.length===4&&summary.routes.every(r=>r.outcome==='pass')?'pass':'incomplete';
  summary.equal_initial_state_hashes=new Set(summary.routes.map(r=>r.initial_state_sha256)).size===1&&summary.routes.every(r=>r.initial_state_sha256);
  summary.equal_final_state_hashes=new Set(summary.routes.map(r=>r.final_state_sha256)).size===1&&summary.routes.every(r=>r.final_state_sha256);
  if(summary.outcome==='pass'){assert.equal(summary.equal_initial_state_hashes,true);assert.equal(summary.equal_final_state_hashes,true);}
} catch(e) {summary.outcome='runner_error';summary.error={name:e.name,message:e.message};}
finally {await browser?.close();await stopServer();summary.ended_at=new Date().toISOString();await writeFile(join(out,'summary.json'),JSON.stringify(summary,null,2)+'\n');}
console.log(JSON.stringify({outcome:summary.outcome,output:out}));
if(summary.outcome!=='pass')process.exitCode=1;
