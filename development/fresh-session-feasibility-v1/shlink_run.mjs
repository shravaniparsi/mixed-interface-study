/** Fixed ordinary Shlink feasibility schedule. Raw evidence remains private until export. */
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync,writeFileSync,mkdirSync,existsSync,copyFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {ShlinkBrowser} from './shlink_browser.mjs';
const dir=path.dirname(fileURLToPath(import.meta.url)),base=process.env.SHLINK_BASE;
assert(base&&path.isAbsolute(base));const out=path.join(base,'evidence');mkdirSync(out,{recursive:true,mode:0o700});
const matrix=JSON.parse(readFileSync(path.join(dir,'../../manifests/fresh-session-ordinary-matrix-v1.json'))).systems.find(s=>s.id==='shlink');assert(matrix&&matrix.branches.length===12);
const save=(name,value)=>writeFileSync(path.join(out,name+'.json'),JSON.stringify(value,null,2)+'\n',{mode:0o600});
const load=name=>JSON.parse(readFileSync(path.join(out,name+'.json')));
const result={status:'in_progress',development_only:true,scientific_cases:0,stage:'deployment',cleanup_complete:false};
const branches=[],cycles=[],apiTrace=[];let browser,adapter,apiKey,apiKeyHash;
function deploy(action,label){
 const args=[path.join(dir,'shlink_deploy.py'),base,action,...(label?[label]:[])];
 execFileSync(process.env.PYTHON_BIN||'python3',args,{timeout:action==='prepare'?180000:action==='cleanup'?100000:150000,maxBuffer:1024*1024});
}
function observe(label){deploy('observe',label);return load(label);}
function record(state,shortCode){
 const table=state.database.tables.short_urls,names=table.columns.map(c=>c[1]);
 const rows=table.rows.map(row=>Object.fromEntries(names.map((name,i)=>[name,row[i].type==='blob'?Buffer.from(row[i].value,'base64').toString('hex'):row[i].value])));
 const matches=rows.filter(row=>row.short_code===shortCode&&row.domain_id===null);assert.equal(matches.length,1);return matches[0];
}
async function api(label,method,route,body){
 const response=await fetch('http://127.0.0.1:58080/rest/v3'+route,{method,headers:{'X-Api-Key':apiKey,...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(10000)});
 const text=await response.text();const row={label,method,path:'/rest/v3'+route,body:body??null,status:response.status,response:text,api_key_sha256:apiKeyHash};apiTrace.push(row);save('api-trace',apiTrace);assert(response.ok(),text);return JSON.parse(text);
}
async function fresh(prefix){
 assert(!adapter);adapter=new ShlinkBrowser({browser,uiOrigin:'http://127.0.0.1:58081',apiOrigin:'http://127.0.0.1:58080',apiKey,serverName:'Study Shlink',write:(name,value)=>save(prefix+'-'+name,value)});
 await adapter.openFresh();return adapter;
}
async function close(){if(adapter){const current=adapter;adapter=null;await current.close();}}
async function restore(label){
 await close();deploy('restore');copyFileSync(path.join(out,'last-restored-root.json'),path.join(out,label+'-restored.json'));
 await fresh(label);const form=await adapter.form({shortCode:result.short_code,expected:matrix.api});
 await adapter.settle();observe(label+'-loaded');return form;
}
async function edit(form,label,changes){
 const control=await adapter.save(form,{label,shortCode:result.short_code,changes});
 const readback=await api(label+'-readback','GET','/short-urls/'+encodeURIComponent(result.short_code));save(label+'-api-readback',readback);
 await adapter.settle();observe(label+'-after');return control;
}
try{
 assert.equal(process.version,'v24.11.1');deploy('prepare');
 const deployment=JSON.parse(readFileSync(path.join(base,'deployment.json')));apiKey=deployment.api_key;apiKeyHash=createHash('sha256').update(apiKey).digest('hex');save('actor-key',{sha256:apiKeyHash});
 writeFileSync(path.join(base,'redaction-values.json'),JSON.stringify([apiKey]),{mode:0o600});
 const {chromium}=createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE_PATH);browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 result.stage='native_create';await fresh('native');let form=await adapter.form();observe('native-before');
 const native=await adapter.save(form,{label:'create',changes:{'/longUrl':matrix.native.longUrl,'/title':matrix.native.title}});
 const nativeState=observe('native-after'),nativeRecord=record(nativeState,native.created.shortCode);result.native_record_id=nativeRecord.id;result.native_short_code=nativeRecord.short_code;result.actor_id=nativeRecord.author_api_key_id;
 save('native-api-readback',await api('native-readback','GET','/short-urls/'+encodeURIComponent(native.created.shortCode)));await close();
 result.stage='api_create';observe('api-before');const created=await api('api-create','POST','/short-urls',matrix.api);save('api-create-response',created);
 const readback=await api('api-created-readback','GET','/short-urls/'+encodeURIComponent(created.shortCode));save('api-created-readback',readback);
 const createdState=observe('api-after'),createdRecord=record(createdState,created.shortCode);assert.equal(createdRecord.author_api_key_id,result.actor_id);assert.notEqual(createdRecord.id,result.native_record_id);
 result.record_id=createdRecord.id;result.short_code=createdRecord.short_code;result.api_key_sha256=apiKeyHash;save('result',result);
 deploy('checkpoint');copyFileSync(path.join(base,'root-state.json'),path.join(out,'root-state.json'));
 for(const [i,field] of matrix.fields.entries()){
  const label='cycle-'+i;result.stage=label;save('result',result);form=await restore(label);
  await edit(form,label+'-replace',{[field.pointer]:field.replacement});
  const expected={...matrix.api,[field.pointer.slice(1)]:field.replacement};form=await adapter.form({shortCode:result.short_code,expected});await adapter.settle();observe(label+'-reset-before');
  await edit(form,label+'-reset',{[field.pointer]:field.ordinary});await close();cycles.push({label,field:field.pointer});save('control-cycles',cycles);
 }
 for(const branch of matrix.branches){
  const label=branch.id;result.stage=label;save('result',result);form=await restore(label);
  const target=matrix.fields.find(f=>f.pointer===branch.target),other=matrix.fields.find(f=>f.pointer===branch.unrelated);
  const changes={...(branch.arm==='noop_repair'?{[target.pointer]:target.ordinary}:{}),[other.pointer]:other.replacement};
  await edit(form,label,changes);await close();branches.push({id:label});save('branches',branches);
 }
 assert.equal(cycles.length,2);assert.equal(branches.length,12);result.status='controls_completed';result.stage='complete';
}catch(error){result.status='controls_incomplete';result.error=String(error);result.stack=error.stack;}
finally{
 try{await close();}catch(error){result.status='controls_incomplete';result.capture_error=String(error);}
 if(browser)try{await browser.close();}catch(error){result.status='controls_incomplete';result.browser_cleanup_error=String(error);}
 if(existsSync(path.join(base,'deployment.json')))try{deploy('cleanup');result.cleanup_complete=true;}catch(error){result.status='controls_incomplete';result.cleanup_error=String(error);}
 save('result',result);save('api-trace',apiTrace);console.log(JSON.stringify({status:result.status,stage:result.stage,error:result.error}));
}
process.exitCode=result.status==='controls_completed'?0:1;
