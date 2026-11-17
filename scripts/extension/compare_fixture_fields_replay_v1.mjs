import fs from 'node:fs';
import crypto from 'node:crypto';
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const out='results/development-fixture-field-replay-v1';
if(fs.existsSync(out))throw Error('Closed field comparison');
fs.mkdirSync(out);
const raw=fs.readFileSync('results/development-test-serialization-v1/measurement.json'),fixtures=JSON.parse(raw);
const result={kind:'controlled_fixture_field_original_replay',input_sha256:hash(raw),rows:fixtures.rows.flatMap(r=>['login','email','password'].map(field=>({id:r.id+':'+field,body_sha256:r.body_sha256,field,status:'not_run'}))),errors:[],independent_evaluation_cases:0,full_frontend_state_reconstructed:false};
try{
 if(process.version!=='v22.22.3')throw Error('Node version');
 const runtime='/private/tmp/reactive14-runtime-v1';
 const module=runtime+'/shared-comparison-v1/original-slices.mjs';
 const prior=JSON.parse(fs.readFileSync('results/development-shared-comparison-v1/measurement.json'));
 if(hash(fs.readFileSync(module))!==prior.emitted_sha256)throw Error('Original slice mismatch');
 result.emitted_sha256=prior.emitted_sha256;
 await import(runtime+'/node_modules/@angular/compiler/fesm2020/compiler.mjs');
 const forms=await import(runtime+'/node_modules/@angular/forms/fesm2020/forms.mjs');
 if(forms.VERSION.full!=='14.2.0')throw Error('Angular version');
 result.angular=forms.VERSION.full;result.node=process.version;
 const {Replay}=await import(module);
 for(let i=0;i<result.rows.length;i++){
  const row=result.rows[i],fixture=fixtures.rows[Math.floor(i/3)];
  try{
   if(!Object.hasOwn(fixture.body,row.field)||typeof fixture.body[row.field]!=='string'){Object.assign(row,{status:'measured',verdict:'unknown',reason:'no_observed_string'});continue;}
   const control=new Replay().registerForm.controls[row.field];
   control.setValue(fixture.body[row.field]);
   Object.assign(row,{status:'measured',verdict:control.status==='VALID'?'satisfied':control.status==='INVALID'?'violated':'unknown',control_status:control.status,validation_errors:control.errors});
  }catch(e){Object.assign(row,{status:'error',verdict:'code_error',error:String(e)});}
 }
}catch(e){result.errors.push(String(e));}
fs.writeFileSync(out+'/measurement.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({rows:result.rows.length,errors:result.errors,verdicts:result.rows.map(r=>r.verdict)}));
if(result.errors.length||result.rows.some(r=>r.status!=='measured'))process.exitCode=1;
