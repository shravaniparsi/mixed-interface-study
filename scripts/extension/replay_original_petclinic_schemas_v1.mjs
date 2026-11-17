import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const runtime='/private/tmp/angular-runtime-qualification-v2';
const sourceRoot='/private/tmp/petclinic-extraction-source-v1';
const helperRoot='/private/tmp/petclinic-original-schema-v1';
const digest=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const definitions={owner:{file:'owner-form.ts',schema:'ownerSchema',model:{firstName:'Ana',lastName:'Test',address:'Street 1',city:'Rome',telephone:'1234567890'},selected:'address'},pet:{file:'pet-form.ts',schema:'petSchema',model:{name:'Buddy',birthDate:'2020-01-01',typeId:'1'},selected:'birthDate'},visit:{file:'visit-form.ts',schema:'visitSchema',model:{date:'2020-01-01',description:'Checkup'},selected:'description'}};
const rows=[];
for(const [schema,d] of Object.entries(definitions))for(const mode of ['ordinary','all_empty','selected_null','selected_omitted']){
  const model={...d.model};
  if(mode==='all_empty')for(const k of Object.keys(model))model[k]='';
  if(mode==='selected_null')model[d.selected]=null;
  if(mode==='selected_omitted')delete model[d.selected];
  rows.push({schema,mode,model,status:'not_run'});
}
for(const [schema,field,value] of [['owner','address','   '],['owner','firstName','Anne-Marie'],['pet','name','!bad'],['visit','description','   ']])rows.push({schema,mode:'special_'+field,model:{...definitions[schema].model,[field]:value},status:'not_run'});
const output={kind:'exposed_original_schema_replay',rows,errors:[],sources:[],compiled:[],node:process.version};
const save=()=>fs.writeFileSync(process.argv[2],JSON.stringify(output,null,2)+'\n');
const timer=setTimeout(()=>{output.errors.push({phase:'timeout'});save();process.exit(2);},60000);
try{
  const compiler='/private/tmp/petclinic-angular-semantics-v1/typescript.cjs';
  const compilerEvidence=JSON.parse(fs.readFileSync('/private/tmp/petclinic-angular-semantics-v1/typescript-evidence.json'));
  if(digest(fs.readFileSync(compiler))!==compilerEvidence.compiler_sha256)throw Error('Compiler integrity mismatch');
  const ts=require(compiler);output.typescript=ts.version;output.compiler_sha256=compilerEvidence.compiler_sha256;
  const work=runtime+'/original-schema-replay-v1';fs.mkdirSync(work);
  const inventory=JSON.parse(fs.readFileSync('manifests/petclinic-source-rule-inventory-v1.json'));
  const helper=JSON.parse(fs.readFileSync(helperRoot+'/source.json'));
  const inputs=[...Object.values(definitions).map(d=>({file:d.file,source:sourceRoot+'/'+d.file,sha256:inventory.sources.find(s=>s.path.endsWith('/'+d.file)).sha256})),{file:'form-utils.ts',source:helperRoot+'/form-utils.ts',sha256:helper.sha256}];
  for(const item of inputs){
    const raw=fs.readFileSync(item.source);if(digest(raw)!==item.sha256)throw Error('Source integrity mismatch: '+item.file);
    output.sources.push({file:item.file,sha256:item.sha256});
    const result=ts.transpileModule(raw.toString(),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022},reportDiagnostics:true});
    if(result.diagnostics?.some(d=>d.category===ts.DiagnosticCategory.Error))throw Error('Transpilation diagnostics: '+item.file);
    const parsed=ts.createSourceFile(item.file,result.outputText,ts.ScriptTarget.ES2022,true,ts.ScriptKind.JS);
    const rewrites=[];
    for(const statement of parsed.statements){
      if(!ts.isImportDeclaration(statement))continue;
      const module=statement.moduleSpecifier.text;
      if(module==='../utils/form-utils')rewrites.push([statement.moduleSpecifier.getStart(parsed),statement.moduleSpecifier.end,'"./form-utils.mjs"']);
      else if(module!=='@angular/forms/signals')throw Error('Unapproved runtime import: '+module);
    }
    let code=result.outputText;for(const [start,end,replacement] of rewrites.reverse())code=code.slice(0,start)+replacement+code.slice(end);
    const file=item.file.replace(/\.ts$/,'.mjs');fs.writeFileSync(path.join(work,file),code);
    output.compiled.push({file,sha256:digest(code),resolved_relative_imports:rewrites.length});
  }
  await import(runtime+'/node_modules/@angular/compiler/fesm2022/compiler.mjs');
  const core=await import(runtime+'/node_modules/@angular/core/fesm2022/core.mjs');
  const forms=await import(runtime+'/node_modules/@angular/forms/fesm2022/signals.mjs');output.angular=core.VERSION.full;
  const schemas={};for(const [name,d] of Object.entries(definitions))schemas[name]=(await import(work+'/'+d.file.replace(/\.ts$/,'.mjs')))[d.schema];
  output.original_schemas_loaded=Object.keys(schemas);
  for(const row of rows){
    let injector;row.fields=[];row.phase='setup';
    try{
      injector=core.createEnvironmentInjector([{provide:core.ɵINJECTOR_SCOPE,useValue:'root'},core.ErrorHandler,core.provideZonelessChangeDetection()],core.Injector.NULL);
      const tree=forms.form(core.signal({...row.model}),schemas[row.schema],{injector});
      injector.get(core.ApplicationRef).tick();row.phase='field_observation';
      for(const field of Object.keys(definitions[row.schema].model)){
        const handle=tree[field];const record={field,materialized:typeof handle==='function'};row.fields.push(record);
        if(record.materialized){const state=handle();record.disabled=state.disabled();record.hidden=state.hidden();record.readonly=state.readonly();record.error_kinds=state.errors().map(e=>e.kind);}
      }
      row.phase='root_observation';row.root_valid=tree().valid();row.root_error_kinds=tree().errorSummary().map(e=>e.kind);row.status='measured';
    }catch(error){row.status='error';row.error=String(error);row.stack=error.stack;}
    finally{try{injector?.destroy();}catch(error){output.errors.push({phase:'cleanup',schema:row.schema,mode:row.mode,error:String(error),stack:error.stack});}}
  }
}catch(error){output.errors.push({phase:'prepare_import',error:String(error),stack:error.stack});}
finally{clearTimeout(timer);save();}
if(output.errors.length||rows.some(r=>r.status!=='measured'))process.exitCode=1;
