import fs from 'node:fs';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),runtime='/private/tmp/reactive14-runtime-v1';
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const outputPath='results/development-shared-comparison-v1/measurement.json';
if(fs.existsSync(outputPath))throw Error('Closed output exists');
fs.mkdirSync('results/development-shared-comparison-v1');
const scheduleRaw=fs.readFileSync('manifests/development-shared-comparison-schedule-v1.json');
if(hash(scheduleRaw)!=='ddf8390024d80e3e59784e7f972f1ed2b526bec7280f38e5bd6951a639476ee5')throw Error('frozen shared schedule mismatch');
const schedule=JSON.parse(scheduleRaw);
const output={kind:'shared_input_source_replay_and_manual_conditional',schedule_sha256:hash(scheduleRaw),node:process.version,rows:schedule.rows.map(r=>({id:r.id,status:'not_run'})),errors:[],independent_evaluation_cases:0};
const save=()=>fs.writeFileSync(outputPath,JSON.stringify(output,null,2)+'\n');
const timer=setTimeout(()=>{output.errors.push({phase:'timeout'});save();process.exit(2);},60000);
const start=performance.now();
try{
 const evidence=JSON.parse(fs.readFileSync('manifests/development-form-source-screen-v1.json')).rows.find(r=>r.index===1);
 const partition=JSON.parse(fs.readFileSync('manifests/project-family-partition-v1.json'));
 if(!partition.rows.some(r=>r.full_name===evidence.full_name&&r.partition==='development'))throw Error('not development');
 const source=fs.readFileSync('/private/tmp/development-form-source-screen-v1/1.txt','utf8');if(hash(source)!==evidence.sha256)throw Error('source mismatch');output.source_sha256=hash(source);
 const parser='/private/tmp/petclinic-angular-semantics-v1/typescript.cjs';
 const parserEvidence=JSON.parse(fs.readFileSync('/private/tmp/petclinic-angular-semantics-v1/typescript-evidence.json'));
 if(hash(fs.readFileSync(parser))!==parserEvidence.compiler_sha256)throw Error('compiler mismatch');output.compiler_sha256=parserEvidence.compiler_sha256;
 const ts=require(parser);if(ts.version!=='6.0.3')throw Error('parser version');output.typescript=ts.version;
 if(process.version!=='v22.22.3')throw Error('Node version');
 const file=ts.createSourceFile('component.ts',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS);if(file.parseDiagnostics.length)throw Error('parse diagnostics');
 const classes=file.statements.filter(ts.isClassDeclaration);if(classes.length!==1)throw Error('ambiguous class');
 const props=classes[0].members.filter(n=>ts.isPropertyDeclaration(n)&&n.name.getText(file)==='registerForm');
 const methods=classes[0].members.filter(n=>ts.isMethodDeclaration(n)&&n.name.getText(file)==='register');
 if(props.length!==1||methods.length!==1||!props[0].initializer)throw Error('ambiguous source slices');
 const initializer=props[0].initializer.getText(file),method=methods[0].getText(file);
 const prior=JSON.parse(fs.readFileSync('manifests/development-confirmation-reconstruction-v1.json'));
 if(hash(method)!==prior.method_sha256)throw Error('manual conditional source binding mismatch');
 const guards=methods[0].body.statements.filter(ts.isIfStatement);
 if(guards.length!==1||guards[0].expression.getText(file)!=='password !== confirmPassword')throw Error('conditional shape unsupported');
 output.manual_conditional_source_bound=true;
 output.initializer_sha256=hash(initializer);output.method_sha256=hash(method);
 const input="import {FormGroup,FormControl,Validators} from '@angular/forms';\nexport class Replay { registerForm="+initializer+';\n'+method+'\n}';
 const emitted=ts.transpileModule(input,{compilerOptions:{module:ts.ModuleKind.ES2022,target:ts.ScriptTarget.ES2022},reportDiagnostics:true});if(emitted.diagnostics?.some(d=>d.category===ts.DiagnosticCategory.Error))throw Error('transpile diagnostics');
 const work=runtime+'/shared-comparison-v1';fs.mkdirSync(work);fs.writeFileSync(work+'/original-slices.mjs',emitted.outputText);output.emitted_sha256=hash(emitted.outputText);
 await import(runtime+'/node_modules/@angular/compiler/fesm2020/compiler.mjs');
 const forms=await import(runtime+'/node_modules/@angular/forms/fesm2020/forms.mjs');if(forms.VERSION.full!=='14.2.0')throw Error('Angular version');output.angular=forms.VERSION.full;
 const {Replay}=await import(work+'/original-slices.mjs');
 output.shared_setup_seconds=(performance.now()-start)/1000;
 for(let i=0;i<schedule.rows.length;i++){
  const spec=schedule.rows[i],row=output.rows[i],shared=spec.shared;
  row.shared_input_sha256=shared.shared_input_sha256;
  try{
   const keys=['form.snapshot','translation.language'];
   if(JSON.stringify(shared.declared_requirements)!==JSON.stringify(keys))throw Error('requirements changed');
   if(shared.observation.target!=='submit_decision'||shared.observation.context.lifecycle!=='direct_original_method_after_fresh_reset')throw Error('target changed');
   const facts=shared.resolved;
   let reason=null;
   if(shared.unresolved.length||!shared.evidence_complete_for_declared_requirements)reason='missing_shared_context';
   else if(keys.some(k=>facts[k]?.status!=='known'))reason='unsupported_fact_state';
   const form=reason?null:facts['form.snapshot'].value;
   const language=reason?null:facts['translation.language'].value;
   if(!reason&&(!form||Object.keys(form).sort().join(',')!=='confirmPassword,email,login,password'||Object.values(form).some(v=>typeof v!=='string')||typeof language!=='string'))reason='outside_qualified_reset_domain';
   if(reason){row.status='measured';row.C={shared_input_sha256:shared.shared_input_sha256,verdict:'unknown',reason};row.D={shared_input_sha256:shared.shared_input_sha256,verdict:'unknown',reason};continue;}
   const cStart=performance.now();
   row.C={shared_input_sha256:shared.shared_input_sha256,verdict:form.password!==form.confirmPassword?'would_not_emit':'would_emit',method:'manual_source_bound_guard',elapsed_seconds:(performance.now()-cStart)/1000};
   const dStart=performance.now();
   const instance=new Replay(),calls=[];instance.registerForm.reset(structuredClone(form));
   instance.translateService={currentLang:language};instance.registerService={save(payload){calls.push(structuredClone(payload));return {subscribe(){}};}};
   instance.register();
   if(calls.length>1)throw Error('unexpected save count');
   row.D={shared_input_sha256:shared.shared_input_sha256,verdict:calls.length===1?'would_emit':'would_not_emit',method:'original_initializer_and_method',captured_payloads:calls,form_status:instance.registerForm.status,elapsed_seconds:(performance.now()-dStart)/1000};
   row.status='measured';
  }catch(error){Object.assign(row,{status:'error',error:String(error),stack:error.stack});}
 }
}catch(error){output.errors.push({phase:'setup',error:String(error),stack:error.stack});}
finally{clearTimeout(timer);output.elapsed_seconds=(performance.now()-start)/1000;save();}
if(output.errors.length||output.rows.some(r=>r.status!=='measured'))process.exitCode=1;
