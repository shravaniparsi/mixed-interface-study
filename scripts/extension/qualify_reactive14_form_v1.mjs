import fs from 'node:fs';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),runtime='/private/tmp/reactive14-runtime-v1';
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
const ordinary={login:'ana',email:'ana@example.com',password:'abcd',confirmPassword:'abcd'};
const modes=['ordinary','reset_empty','reset_omitted_password','reset_null_password','disable_password','disable_group'];
const output={kind:'exposed_reactive14_original_initializer',node:process.version,rows:modes.map(mode=>({mode,status:'not_run'})),errors:[]};
const save=()=>fs.writeFileSync(process.argv[2],JSON.stringify(output,null,2)+'\n');
const timer=setTimeout(()=>{output.errors.push({phase:'timeout'});save();process.exit(2);},60000);
try{
 const evidence=JSON.parse(fs.readFileSync('manifests/development-form-source-screen-v1.json')).rows.find(r=>r.index===1);
 const partition=JSON.parse(fs.readFileSync('manifests/project-family-partition-v1.json'));
 if(!partition.rows.some(r=>r.full_name===evidence.full_name&&r.partition==='development'))throw Error('not development');
 const source=fs.readFileSync('/private/tmp/development-form-source-screen-v1/1.txt','utf8');if(hash(source)!==evidence.sha256)throw Error('source hash mismatch');output.source_sha256=hash(source);
 const parser='/private/tmp/petclinic-angular-semantics-v1/typescript.cjs',parserEvidence=JSON.parse(fs.readFileSync('/private/tmp/petclinic-angular-semantics-v1/typescript-evidence.json'));
 if(hash(fs.readFileSync(parser))!==parserEvidence.compiler_sha256)throw Error('compiler hash mismatch');output.compiler_sha256=parserEvidence.compiler_sha256;
 const ts=require(parser);output.typescript=ts.version;
 const file=ts.createSourceFile('component.ts',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS);if(file.parseDiagnostics.length)throw Error('parse diagnostics');
 const klass=file.statements.filter(ts.isClassDeclaration);if(klass.length!==1)throw Error('class ambiguous');
 const properties=klass[0].members.filter(n=>ts.isPropertyDeclaration(n)&&n.name.getText(file)==='registerForm');if(properties.length!==1||!properties[0].initializer)throw Error('initializer ambiguous');
 const initializer=properties[0].initializer.getText(file);output.initializer_sha256=hash(initializer);
 const input="import {FormGroup,FormControl,Validators} from '@angular/forms';\nexport const makeForm=()=> ("+initializer+');';
 const emitted=ts.transpileModule(input,{compilerOptions:{module:ts.ModuleKind.ES2022,target:ts.ScriptTarget.ES2022},reportDiagnostics:true});if(emitted.diagnostics?.some(d=>d.category===ts.DiagnosticCategory.Error))throw Error('transpile diagnostics');
 const work=runtime+'/measurement-v1';fs.mkdirSync(work);fs.writeFileSync(work+'/original-initializer.mjs',emitted.outputText);output.emitted_sha256=hash(emitted.outputText);
 await import(runtime+'/node_modules/@angular/compiler/fesm2020/compiler.mjs');
 const forms=await import(runtime+'/node_modules/@angular/forms/fesm2020/forms.mjs');output.angular=forms.VERSION.full;
 const {makeForm}=await import(work+'/original-initializer.mjs');
 for(const row of output.rows){
  try{
   const form=makeForm();form.reset({...ordinary});
   if(row.mode==='reset_empty')form.reset({});
   if(row.mode==='reset_omitted_password'){const value={...ordinary};delete value.password;form.reset(value);}
   if(row.mode==='reset_null_password')form.reset({...ordinary,password:null});
   if(row.mode==='disable_password'){form.controls.password.setValue('');form.controls.password.disable();}
   if(row.mode==='disable_group'){form.controls.password.setValue('');form.disable();}
   Object.assign(row,{status:'measured',group_status:form.status,valid:form.valid,invalid:form.invalid,value:form.value,raw_value:form.getRawValue(),controls:Object.fromEntries(Object.entries(form.controls).map(([name,c])=>[name,{value:c.value,status:c.status,errors:c.errors,disabled:c.disabled}]))});
  }catch(error){Object.assign(row,{status:'error',error:String(error),stack:error.stack});}
 }
}catch(error){output.errors.push({phase:'setup_import',error:String(error),stack:error.stack});}
finally{clearTimeout(timer);save();}
if(output.errors.length||output.rows.some(r=>r.status!=='measured'))process.exitCode=1;
