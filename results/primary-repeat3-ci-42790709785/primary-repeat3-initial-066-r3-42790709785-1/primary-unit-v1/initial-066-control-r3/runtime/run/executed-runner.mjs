#!/usr/bin/env node
/** Explicit pair dispatch; fresh RAM-store per branch. Historical runner unchanged. */
import assert from 'node:assert/strict';
import {spawn,execFile} from 'node:child_process';
import {existsSync,createWriteStream} from 'node:fs';
import {mkdir,readFile,writeFile,statfs} from 'node:fs/promises';
import {resolve,join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {parseArgs,promisify} from 'node:util';
import net from 'node:net';
import {digest,registryFromBytes,selectCases,REGISTRY_SHA256} from './quartz_generated_case.mjs';

const here=dirname(fileURLToPath(import.meta.url));
const delay=ms=>new Promise(r=>setTimeout(r,ms));
export const childExitedCleanly=exit=>exit?.code===0&&!exit.signal&&!exit.exit_unconfirmed&&!exit.spawn_error;
export function orderedCases(registry,mode='controls',order){
  assert.ok(['controls','boundary-pair'].includes(mode),'Only an explicit paired dispatch is supported');
  assert.equal(order?.schema_version,1);assert.equal(order?.scope,'quartz_repeat_pair');assert.equal(order?.registry_sha256,REGISTRY_SHA256);
  const ids=order.case_ids;assert.ok(Array.isArray(ids)&&ids.length===2&&new Set(ids).size===2,'Exactly two distinct registered branches required');
  const byId=new Map(registry.cases.map(c=>[c.case_id,c]));assert.ok(ids.every(id=>typeof id==='string'&&byId.has(id)),'Unknown case ID');
  const cases=ids.map(id=>byId.get(id));
  assert.deepEqual(cases[0].operations[0],cases[1].operations[0],'Producer operations differ');
  const intent=c=>Object.fromEntries(Object.entries(c.operations[1]).filter(([k])=>k!=='interface'));
  assert.deepEqual(intent(cases[0]),intent(cases[1]),'Consumer intentions differ');
  assert.deepEqual(new Set(cases.map(c=>c.operations[1].interface)),new Set(['api','ui']),'Both continuations required');
  for(const key of ['intervention','mutation','expectation','expectation_scope'])assert.deepEqual(cases[0][key],cases[1][key],key+' differs');
  if(mode==='controls')assert.ok(cases.every(c=>c.intervention==='route_only'&&!c.mutation),'Control dispatch cannot contain mutations');
  return cases;
}
export async function portFree(port){return new Promise(resolve=>{const server=net.createServer();server.once('error',()=>resolve(false));server.listen(port,'127.0.0.1',()=>server.close(()=>resolve(true)));});}
export async function stopOwned(child,grace=5000){
  if(!child||!child.pid||child.exitCode!==null||child.signalCode!==null)return {ok:true,already_exited:true};
  const exited=new Promise(r=>child.once('exit',r));child.kill('SIGTERM');let timer;
  const graceful=await Promise.race([exited.then(()=>true),new Promise(r=>{timer=setTimeout(()=>r(false),grace);})]);clearTimeout(timer);
  let confirmed=graceful;
  if(!graceful){child.kill('SIGKILL');confirmed=await Promise.race([exited.then(()=>true),new Promise(r=>{timer=setTimeout(()=>r(false),1000);})]);clearTimeout(timer);}
  return {ok:confirmed,pid:child.pid,graceful,exit_code:child.exitCode,signal:child.signalCode};
}
async function browserCleanup(python,dir,launcherStopped){
  if(!launcherStopped)return {ok:false,reason:'launcher_exit_unconfirmed'};
  try{const {stdout}=await promisify(execFile)(python,[join(here,'quartz_browser_cleanup.py'),'--metadata',join(dir,'browser-pid.json')],{timeout:6000,env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});return JSON.parse(stdout);}
  catch(error){try{return {...JSON.parse(error.stdout),wrapper_exit_code:error.code};}catch{return {ok:false,reason:'cleanup_wrapper_failed',error:String(error)};}}
}
async function runtimeFiles(runtime){
  const jars=[{file:join(runtime,'quartz-manager-web-showcase-5.0.1.jar'),sha256:'d043fe19a11c61d9dc3117c3a84ccaa134fe083aee4145e0f0e2bee84a83a826'},
    {file:join(runtime,'quartz-manager-starter-ui-5.0.1.jar'),sha256:'5a06dacd7bc06f46800606ddf8a46857a866ba622a372ba85312547507c3e320'}];
  const bytes=await readFile(join(runtime,'declared-dependencies.json'));assert.equal(digest(bytes),'acfba9a7323d951fbea0fc39536aa6ead718d5bff1aca5c3d18ea27ef64d8968');
  for(const item of JSON.parse(bytes)){const file=resolve(runtime,item.name);assert.ok(file.startsWith(runtime+'/'));jars.push({file,sha256:item.sha256});}
  for(const jar of jars)assert.equal(digest(await readFile(jar.file)),jar.sha256,'Pinned artifact checksum: '+jar.file);
  return {showcase:jars[0].file,loadPath:jars.slice(1).map(x=>x.file),jars};
}
async function main(){
  const {values:v}=parseArgs({options:{help:{type:'boolean'},runtime:{type:'string'},java:{type:'string'},node:{type:'string'},python:{type:'string',default:'python3'},registry:{type:'string'},output:{type:'string'},mode:{type:'string',default:'controls'},port:{type:'string',default:'19965'},'playwright-module':{type:'string'},'chrome-executable':{type:'string'},'case-timeout-ms':{type:'string',default:'120000'},'case-order-file':{type:'string'},'validation-interrupt-at':{type:'string'}}});
  if(v.help){console.log('node run_quartz_pair_job_v2.mjs --runtime DIR --java JAVA --registry FILE --output NEW_DIR --case-order-file FILE [--mode controls|boundary-pair] [--node NODE] [--playwright-module MODULE] [--chrome-executable BROWSER] [--port 19965] [--case-timeout-ms 120000] [--case-order-file FILE]\nRequires exactly one declared pair. Controls mode refuses mutations. Boundary mode remains outside hosted qualification. Verifies pinned jars/registry, restarts the native RAM-store server per case, captures evidence, and cleans up owned processes. Linux/macOS Java21; no JRE architecture assumption.');return;}
  for(const k of ['runtime','java','registry','output'])assert.ok(v[k],'Missing --'+k);
  if(v['validation-interrupt-at'])assert.ok(v.mode==='controls'&&['before-browser','after-browser'].includes(v['validation-interrupt-at']),'Validation interruption is available only for controls');
  const port=Number(v.port),timeout=Number(v['case-timeout-ms']);assert.ok(Number.isInteger(port)&&port>=1024&&port<=65535);assert.ok(Number.isInteger(timeout)&&timeout>=10000);
  const runtime=resolve(v.runtime),output=resolve(v.output),registryPath=resolve(v.registry);assert.ok(!existsSync(output),'Choose a new output directory; failed attempts are preserved.');
  const disk=await statfs(runtime);assert.ok(disk.bavail*disk.bsize>400*1024**2,'Free disk must exceed 400 MiB');
  const orderBytes=v['case-order-file']?await readFile(resolve(v['case-order-file'])):undefined;
  const registry=registryFromBytes(await readFile(registryPath)),cases=orderedCases(registry,v.mode,orderBytes?JSON.parse(orderBytes):undefined),files=await runtimeFiles(runtime);assert.ok(await portFree(port),'Application port is already occupied');
  await mkdir(output,{recursive:true});
  await writeFile(join(output,'executed-runner.mjs'),await readFile(fileURLToPath(import.meta.url)));await writeFile(join(output,'executed-adapter.mjs'),await readFile(join(here,'quartz_generated_case.mjs')));await writeFile(join(output,'executed-registry.json'),await readFile(registryPath));
  for(const file of ['quartz_browser_cleanup.py','realworld_case_worker.py'])await writeFile(join(output,'executed-'+file),await readFile(join(here,file)));
  if(orderBytes)await writeFile(join(output,'executed-case-order.json'),orderBytes);
  const summary={schema_version:1,kind:'quartz_generated_registry_run',started_at:new Date().toISOString(),mode:v.mode,registry_sha256:REGISTRY_SHA256,registry_manifest_sha256:registry.manifest_sha256,
    adapter_sha256:digest(await readFile(join(here,'quartz_generated_case.mjs'))),runner_sha256:digest(await readFile(fileURLToPath(import.meta.url))),platform:process.platform,node_version:process.version,
    runtime:{java:v.java,node:v.node??process.execPath,python:v.python,host:'127.0.0.1',port,jvm_timezone:'Europe/Rome',heap_mb:256,artifacts:files.jars},validation_interrupt_at:v['validation-interrupt-at']??null,cleanup_helper_sha256:digest(await readFile(join(here,'realworld_case_worker.py'))),case_count:cases.length,cases:[],
    effective_options:{runtime,java:v.java,node:v.node??process.execPath,python:v.python,registry:registryPath,output,mode:v.mode,port,case_timeout_ms:timeout,playwright_module:v['playwright-module']??'playwright',chrome_executable:v['chrome-executable']??null,validation_interrupt_at:v['validation-interrupt-at']??null,case_order_file:v['case-order-file']?resolve(v['case-order-file']):null},
    ordering:{source:orderBytes?'case_order_file':'registry_order',case_ids:cases.map(c=>c.case_id),order_file_sha256:orderBytes?digest(orderBytes):null},
    native_unit_suite_executed:false,application_source_modified:false,freeze_complete:false,defect_adjudication:'not_performed'};
  let interrupted=false,currentJava,currentNode;
  const signalHandler=s=>{interrupted=true;summary.interruption=s;currentNode?.kill('SIGTERM');currentJava?.kill('SIGTERM');};
  const sigterm=()=>signalHandler('SIGTERM'),sigint=()=>signalHandler('SIGINT');process.on('SIGTERM',sigterm);process.on('SIGINT',sigint);
  try{
    for(let i=0;i<cases.length;i++){
      if(interrupted)break;const c=cases[i],route=c.operations.map(x=>x.interface).join('-'),dir=join(output,`${String(i+1).padStart(3,'0')}-${route}`);await mkdir(dir);
      const entry={case_id:c.case_id,route,intervention:c.intervention,started_at:new Date().toISOString(),evidence_directory:dir,phase_cost_ms:{},status:'starting'};
      const beginning=performance.now();let deadline,hard,validationHard,killConfirmationTimer,expired=false,serverLog,caseLog;
      try{
        assert.ok(await portFree(port),'Previous case has not released the application port');
        serverLog=createWriteStream(join(dir,'server.log'),{flags:'wx'});
        const args=['-Xmx256m','-Duser.timezone=Europe/Rome',`-Dloader.path=${files.loadPath.join(',')}`,'-cp',files.showcase,'org.springframework.boot.loader.launch.PropertiesLauncher','--server.address=127.0.0.1',`--server.port=${port}`];
        currentJava=spawn(v.java,args,{cwd:runtime,detached:true,stdio:['ignore','pipe','pipe']});currentJava.stdout.pipe(serverLog,{end:false});currentJava.stderr.pipe(serverLog,{end:false});currentJava.once('close',()=>serverLog.end());let javaError;currentJava.once('error',e=>{javaError=e;});
        entry.server_pid=currentJava.pid;const startup=performance.now(),startupLimit=Math.min(startup+45000,beginning+timeout-1000);let ready=false;
        while(performance.now()<startupLimit&&!interrupted){
          if(javaError)throw javaError;if(currentJava.exitCode!==null)throw new Error('Native server exited during startup: '+currentJava.exitCode);
          try{const r=await fetch(`http://127.0.0.1:${port}/quartz-manager-ui/index.html`,{signal:AbortSignal.timeout(1000)});if(r.status===200){entry.native_index_sha256=digest(await r.text());assert.equal(entry.native_index_sha256,'f885d2a5480d6a62af4a6a5011e95b5d98f5ee884c00a2d7e42b7e7fe5ce2abf');ready=true;break;}}catch(error){if(error.code==='ERR_ASSERTION')throw error;}
          await delay(250);
        }
        entry.phase_cost_ms.startup=performance.now()-startup;if(interrupted)throw new Error('Interrupted during startup');assert.ok(ready,'Native UI startup deadline exceeded');
        const childArgs=[join(here,'quartz_generated_case.mjs'),'--registry',registryPath,'--case-id',c.case_id,'--output',dir,'--base',`http://127.0.0.1:${port}`];
        for(const option of ['playwright-module','chrome-executable','validation-interrupt-at'])if(v[option])childArgs.push('--'+option,v[option]);
        caseLog=createWriteStream(join(dir,'adapter.log'),{flags:'wx'});currentNode=spawn(v.node??process.execPath,childArgs,{detached:true,stdio:['ignore','pipe','pipe','ipc']});currentNode.stdout.pipe(caseLog,{end:false});currentNode.stderr.pipe(caseLog,{end:false});currentNode.once('close',()=>caseLog.end());
        let resolveUnconfirmed;const exitUnconfirmed=new Promise(r=>{resolveUnconfirmed=r;});
        const hardStop=()=>{currentNode?.kill('SIGKILL');killConfirmationTimer=setTimeout(()=>resolveUnconfirmed({exit_unconfirmed:true}),1000);};
        currentNode.on('message',m=>{if(m?.type==='validation_pause'&&m.stage===v['validation-interrupt-at']){entry.validation_pause=m.stage;expired=true;clearTimeout(deadline);clearTimeout(hard);currentNode?.kill('SIGTERM');validationHard=setTimeout(hardStop,1500);}});
        let childError;currentNode.once('error',e=>{childError=e;});const childEnded=new Promise(r=>{currentNode.once('exit',(code,signal)=>r({code,signal}));currentNode.once('error',error=>r({spawn_error:String(error)}));});
        const remaining=Math.max(1,timeout-(performance.now()-beginning));
        deadline=setTimeout(()=>{expired=true;currentNode?.kill('SIGTERM');},remaining);
        hard=setTimeout(hardStop,remaining+7000);
        const childResult=await Promise.race([childEnded,exitUnconfirmed]);clearTimeout(deadline);clearTimeout(hard);clearTimeout(validationHard);clearTimeout(killConfirmationTimer);if(childError)throw childError;
        entry.child_exit=childResult;entry.timed_out=expired;
        try{const r=JSON.parse(await readFile(join(dir,'result.json')));entry.status=r.status;entry.completed=r.completed;entry.accepted_prefix=r.accepted_prefix;entry.reached_continuation=r.reached_continuation;entry.blocked=r.blocked;entry.initial_state_sha256=r.initial_state_sha256;entry.final_state_sha256=r.final_state_sha256??(r.final_state?digest(r.final_state):null);entry.failed_required_checks=r.checks.filter(x=>x.scope==='requirement'&&!x.passed);entry.phase_cost_ms.adapter=r.phase_cost_ms;}catch(e){entry.status='missing_or_invalid_case_result';entry.result_error=String(e);}
        if(childResult.signal||childResult.spawn_error||childResult.exit_unconfirmed||![0,1].includes(childResult.code)){entry.status='child_exit_error';entry.completed=false;}
        if(expired||interrupted){entry.status='interrupted';entry.completed=false;}
      }catch(e){entry.status=interrupted?'interrupted':'runner_error';entry.error={name:e.name,message:e.message};}
      finally{
        clearTimeout(deadline);clearTimeout(hard);clearTimeout(validationHard);clearTimeout(killConfirmationTimer);const cleanupStart=performance.now();entry.node_cleanup=await stopOwned(currentNode);entry.java_cleanup=await stopOwned(currentJava);
        entry.browser_cleanup=await browserCleanup(v.python,dir,entry.node_cleanup.ok);if(entry.node_cleanup.ok)currentNode=undefined;if(entry.java_cleanup.ok)currentJava=undefined;
        for(let t=0;t<40&&!(await portFree(port));t++)await delay(100);
        entry.application_port_released=await portFree(port);entry.browser_process_absent=entry.browser_cleanup.ok;
        entry.phase_cost_ms.teardown=performance.now()-cleanupStart;entry.elapsed_ms=performance.now()-beginning;entry.ended_at=new Date().toISOString();
        if(!entry.application_port_released||!entry.browser_process_absent||!entry.node_cleanup.ok||!entry.java_cleanup.ok){entry.status='cleanup_failed';entry.completed=false;}
        summary.cases.push(entry);await writeFile(join(dir,'run.json'),JSON.stringify(entry,null,2)+'\n');await writeFile(join(output,'summary.json'),JSON.stringify(summary,null,2)+'\n');console.log(JSON.stringify({case_id:c.case_id,status:entry.status,port_released:entry.application_port_released}));
      }
      // Reuse the exact Python source-qualified classifier used by final extraction.
      try{
        const {stdout}=await promisify(execFile)(v.python,[join(here,'quartz_terminal_outcomes.py'),'--branch',join(dir,'result.json'),'--run',join(dir,'run.json'),'--registry',registryPath],{timeout:10000,maxBuffer:1024*1024});
        const classified=JSON.parse(stdout);await writeFile(join(dir,'branch-classification.json'),JSON.stringify(classified,null,2)+'\n');
        if(classified.action!=='continue')break;
      }catch(error){summary.classification_error=String(error);break;}
    }
  }finally{
    await stopOwned(currentNode);await stopOwned(currentJava);process.off('SIGTERM',sigterm);process.off('SIGINT',sigint);
    summary.equal_initial_state_hashes=summary.cases.length===cases.length&&summary.cases.every(c=>c.initial_state_sha256)&&new Set(summary.cases.map(c=>c.initial_state_sha256)).size===1;
    summary.all_controls_pass=summary.cases.length===cases.length&&summary.cases.every(c=>c.status==='pass'&&c.completed&&c.application_port_released&&c.browser_process_absent);
    summary.status=v.mode==='controls'?(summary.all_controls_pass&&summary.equal_initial_state_hashes?'pass':'incomplete'):(summary.cases.length===cases.length&&summary.cases.every(c=>c.completed)?'completed_observations':'incomplete');
    summary.ended_at=new Date().toISOString();await writeFile(join(output,'summary.json'),JSON.stringify(summary,null,2)+'\n');console.log(JSON.stringify({status:summary.status,output}));
  }
  if(summary.status==='incomplete'||summary.classification_error)process.exitCode=1;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(e=>{console.error(e.stack);process.exitCode=1;});
