import fs from 'node:fs';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),runtime='/private/tmp/reactive14-runtime-v1';
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const outputPath='results/development-confirmation-reconstruction-v1/measurement.json';
if(fs.existsSync(outputPath))throw Error('Closed output exists');
fs.mkdirSync('results/development-confirmation-reconstruction-v1');
const scheduleRaw=fs.readFileSync('manifests/development-confirmation-schedule-v1.json');
const schedule=JSON.parse(scheduleRaw);
const output={kind:'original_source_confirmation_reconstruction',schedule_sha256:hash(scheduleRaw),node:process.version,rows:schedule.rows.map(r=>({id:r.id,status:'not_run'})),errors:[],independent_evaluation_cases:0};
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
 output.initializer_sha256=hash(initializer);output.method_sha256=hash(method);
 const input="import {FormGroup,FormControl,Validators} from '@angular/forms';\nexport class Replay { registerForm="+initializer+';\n'+method+'\n}';
 const emitted=ts.transpileModule(input,{compilerOptions:{module:ts.ModuleKind.ES2022,target:ts.ScriptTarget.ES2022},reportDiagnostics:true});if(emitted.diagnostics?.some(d=>d.category===ts.DiagnosticCategory.Error))throw Error('transpile diagnostics');
 const work=runtime+'/confirmation-reconstruction-v1';fs.mkdirSync(work);fs.writeFileSync(work+'/original-slices.mjs',emitted.outputText);output.emitted_sha256=hash(emitted.outputText);
 await import(runtime+'/node_modules/@angular/compiler/fesm2020/compiler.mjs');
 const forms=await import(runtime+'/node_modules/@angular/forms/fesm2020/forms.mjs');if(forms.VERSION.full!=='14.2.0')throw Error('Angular version');output.angular=forms.VERSION.full;
 const {Replay}=await import(work+'/original-slices.mjs');
 for(let i=0;i<schedule.rows.length;i++){
  const spec=schedule.rows[i],row=output.rows[i];
  try{
   const instance=new Replay(),calls=[];instance.registerForm.reset(spec.form);
   instance.translateService={currentLang:spec.language};instance.registerService={save(payload){calls.push(structuredClone(payload));return {subscribe(){}};}};
   const raw=instance.registerForm.getRawValue();
   row.candidate_api_projection={login:raw.login,email:raw.email,password:raw.password,langKey:spec.language};
   row.form_status=instance.registerForm.status;
   row.controls=Object.fromEntries(Object.entries(instance.registerForm.controls).map(([name,c])=>[name,{value:c.value,status:c.status,errors:c.errors}]));
   instance.register();
   Object.assign(row,{status:'measured',save_calls:calls.length,captured_payloads:calls,doNotMatch:instance.doNotMatch});
  }catch(error){Object.assign(row,{status:'error',error:String(error),stack:error.stack});}
 }
}catch(error){output.errors.push({phase:'setup',error:String(error),stack:error.stack});}
finally{clearTimeout(timer);output.elapsed_seconds=(performance.now()-start)/1000;save();}
if(output.errors.length||output.rows.some(r=>r.status!=='measured'))process.exitCode=1;
