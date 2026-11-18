import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {equal,framePreserved,postComparable,decodedConfig} from '../../development/redesign-gomodel-ordinary-v2/frame.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const dir=path.resolve(process.argv[2]||path.join(root,'results/redesign-gomodel-ordinary-v2'));
const read=name=>JSON.parse(readFileSync(path.join(dir,name+'.json')));
const input=JSON.parse(readFileSync(path.join(root,'development/redesign-gomodel-ordinary-v2/input.json')));
const checks={},missing=[];
function check(name,files,fn){if(files.some(f=>!existsSync(path.join(dir,f+'.json')))){missing.push(name);return;}checks[name]=Boolean(fn());}
const reported=existsSync(path.join(dir,'result.json'))?read('result'):null;
check('verified_executable',['executable-verification'],()=>read('executable-verification').binary_sha256==='68fe1005d8de716083f4c63be4f8e35b39e6b61d44b32fc883ec9f3680a5e8d3'&&read('executable-verification').status==='verified');
check('loopback_only',['network-interfaces','network-routes'],()=>read('network-interfaces').every(x=>x.ifname==='lo')&&read('network-interfaces').length===1&&read('network-routes').length===0);
check('both_ordinary_records_persisted',['checkpoint-state'],()=>{const t=read('checkpoint-state').tables.guardrail_definitions;if(!t)return false;return [input.native_name,input.api_name].every(name=>{const r=t.rows.find(r=>r[t.columns.indexOf('name')]===name);if(!r)return false;const x=Object.fromEntries(t.columns.map((k,i)=>[k,r[i]]));return x.type===input.type&&x.description===input.description&&x.user_path===input.user_path&&equal(decodedConfig(x.config),input.config);});});
check('restored_full_start_state',['checkpoint-state','restored-precheck-state'],()=>equal(read('checkpoint-state'),read('restored-precheck-state')));
check('restored_actor',['checkpoint-access','restored-precheck-access'],()=>equal(read('checkpoint-access'),read('restored-precheck-access')));
check('restored_browser',['checkpoint-browser','restored-precheck-browser'],()=>equal(read('checkpoint-browser'),read('restored-precheck-browser')));
check('restored_form',['checkpoint-form','restored-precheck-form'],()=>equal(read('checkpoint-form'),read('restored-precheck-form')));
for(const branch of ['warm','restored']){
 check(branch+'_starts_at_checkpoint',['checkpoint-state',branch+'-before'],()=>equal(read('checkpoint-state'),read(branch+'-before')));
 check(branch+'_preserves_full_frame',[branch+'-before',branch+'-after'],()=>framePreserved(read(branch+'-before'),read(branch+'-after'),input.api_name,input.edit_property,input.edit_value));
 check(branch+'_actual_request',['trace'],()=>{const rows=read('trace').filter(x=>x.epoch===branch&&x.channel==='browser-request'&&x.method==='PUT'&&new URL(x.url).pathname==='/admin/guardrails');if(rows.length!==1)return false;return rows[0].headers.authorization==='Bearer '+input.actor_key&&equal(JSON.parse(rows[0].body),{name:input.api_name,type:input.type,description:input.description,user_path:input.user_path,config:{...input.config,[input.edit_property]:input.edit_value}});});
}
check('equivalent_post_states',['warm-after','restored-after'],()=>equal(postComparable(read('warm-after'),input.api_name),postComparable(read('restored-after'),input.api_name)));
check('native_create_actual_request',['native-create-request','trace'],()=>{const rows=read('trace').filter(x=>x.epoch==='native_create'&&x.channel==='browser-request'&&x.method==='PUT'&&new URL(x.url).pathname==='/admin/guardrails');return rows.length===1&&equal(JSON.parse(rows[0].body),{name:input.native_name,type:input.type,description:input.description,user_path:input.user_path,config:input.config});});
check('ordinary_api_create_actual_request',['trace'],()=>{const rows=read('trace').filter(x=>x.epoch==='api_create'&&x.channel==='api'&&x.method==='PUT');return rows.length===1&&rows[0].status>=200&&rows[0].status<300&&equal(rows[0].body,{name:input.api_name,type:input.type,description:input.description,user_path:input.user_path,config:input.config});});
check('maintenance_non_statistics_unchanged',['maintenance-before','maintenance-after'],()=>{const strip=x=>({...x,tables:Object.fromEntries(Object.entries(x.tables).filter(([k])=>!['sqlite_stat1','sqlite_stat4'].includes(k)))});return equal(strip(read('maintenance-before')),strip(read('maintenance-after')));});
check('pid_file_absent',['maintenance-before','maintenance-after','checkpoint-state','restored-precheck-state'],()=>['maintenance-before','maintenance-after','checkpoint-state','restored-precheck-state'].every(f=>!Object.hasOwn(read(f).files,'data/gomodel.pid')));
const complete=reported?.status==='ordinary_lifecycle_checks_passed'&&missing.length===0&&Object.values(checks).every(Boolean);
const summary={status:complete?'ordinary_evidence_checks_passed':'ordinary_qualification_incomplete',reported_status:reported?.status??'missing',reported_stage:reported?.stage??null,checks,missing,scientific_cases:0,scope:'Ordinary lifecycle evidence only; no malformed inputs, repair effects or source-aware baseline accuracy'};
writeFileSync(path.join(dir,'verification.json'),JSON.stringify(summary,null,2)+'\n');console.log(JSON.stringify(summary));
if(reported?.status==='ordinary_lifecycle_checks_passed')assert(complete,'reported success is not supported by all retained checks');
