'use strict';
const fs=require('node:fs'),crypto=require('node:crypto');
const {extractGuard,evaluateGuard}=require('./extract_submission_guard_v1.cjs');
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const out='results/development-guard-acquisition-v1/measurement.json';
if(fs.existsSync(out))throw Error('Closed acquisition exists');
fs.mkdirSync('results/development-guard-acquisition-v1',{recursive:true});
const result={kind:'exposed_development_static_guard_acquisition',independent_evaluation_cases:0,errors:[],rows:[]};
try{
 const parser='/private/tmp/petclinic-angular-semantics-v1/typescript.cjs';
 const parserEvidence=JSON.parse(fs.readFileSync('/private/tmp/petclinic-angular-semantics-v1/typescript-evidence.json'));
 if(hash(fs.readFileSync(parser))!==parserEvidence.compiler_sha256)throw Error('Parser hash mismatch');
 const ts=require(parser);if(ts.version!=='6.0.3'||process.version!=='v22.22.3')throw Error('Runtime version mismatch');
 result.typescript=ts.version;result.node=process.version;result.compiler_sha256=parserEvidence.compiler_sha256;
 const src=fs.readFileSync('/private/tmp/development-form-source-screen-v1/1.txt','utf8');
 const evidence=JSON.parse(fs.readFileSync('manifests/development-form-source-screen-v1.json')).rows.find(r=>r.index===1);
 if(hash(src)!==evidence.sha256)throw Error('Source mismatch');
 const scheduleRaw=fs.readFileSync('manifests/development-shared-comparison-schedule-v1.json');
 if(hash(scheduleRaw)!=='ddf8390024d80e3e59784e7f972f1ed2b526bec7280f38e5bd6951a639476ee5')throw Error('Schedule changed');
 const schedule=JSON.parse(scheduleRaw);
 const refRaw=fs.readFileSync('results/development-shared-comparison-v1/measurement.json'),ref=JSON.parse(refRaw);
 result.schedule_sha256=hash(scheduleRaw);result.reference_sha256=hash(refRaw);
 const start=performance.now();
 result.rule=extractGuard(ts,src,{method:'register',form:'registerForm',service:'registerService',sink:'save'});
 result.acquisition_seconds=(performance.now()-start)/1000;
 for(const row of schedule.rows){
  const s=row.shared;
  let verdict='unknown';
  if(s.evidence_complete_for_declared_requirements&&!s.unresolved.length&&s.resolved['form.snapshot']?.status==='known'&&s.resolved['translation.language']?.status==='known'){
   const decision=evaluateGuard(result.rule,s.resolved['form.snapshot'].value);
   verdict={sink_branch:'would_emit',non_sink_branch:'would_not_emit',unknown:'unknown'}[decision];
  }
  const d=ref.rows.find(r=>r.id===row.id);
  if(!d||d.shared_input_sha256!==s.shared_input_sha256)throw Error('Reference input mismatch');
  result.rows.push({id:row.id,shared_input_sha256:s.shared_input_sha256,verdict,archived_replay_verdict:d.D.verdict,agrees:verdict===d.D.verdict});
 }
}catch(error){result.errors.push(String(error));process.exitCode=1;}
fs.writeFileSync(out,JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));
