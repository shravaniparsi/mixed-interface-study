import fs from 'node:fs';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),runtime='/private/tmp/angular-runtime-qualification-v2';
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const base={id:7,firstName:'Ana',lastName:'Test',address:'Street 1',city:'Rome',telephone:'1234567890'};
const rows=['ordinary','omitted','null'].map(mode=>{const response={...base};if(mode==='omitted')delete response.address;if(mode==='null')response.address=null;return {mode,response,status:'not_run'};});
const result={kind:'exposed_resource_reconstruction',rows,errors:[],compiled:[],node:process.version};
const save=()=>fs.writeFileSync(process.argv[2],JSON.stringify(result,null,2)+'\n');
const timer=setTimeout(()=>{result.errors.push({phase:'timeout'});save();process.exit(2);},60000);
try{
 const manifest=JSON.parse(fs.readFileSync('manifests/petclinic-resource-reconstruction-sources-v1.json'));
 const parser='/private/tmp/petclinic-angular-semantics-v1/typescript.cjs';
 if(hash(fs.readFileSync(parser))!==manifest.compiler_sha256)throw Error('compiler integrity');
 const ts=require(parser);result.typescript=ts.version;
 const work=runtime+'/resource-reconstruction-v1';fs.mkdirSync(work);
 const imports={'@angular/core':'@angular/core','@angular/common/http':'@angular/common/http','@angular/forms/signals':'@angular/forms/signals','rxjs':'rxjs','rxjs/operators':'rxjs/operators','../../environments/environment':'./environment.mjs','../error.service':'./error.service.mjs','../utils/form-utils':'./form-utils.mjs'};
 const compile=(name,text)=>{
   const output=ts.transpileModule(text,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022,experimentalDecorators:true},reportDiagnostics:true});
   if(output.diagnostics?.some(x=>x.category===ts.DiagnosticCategory.Error))throw Error('transpile error '+name);
   const parsed=ts.createSourceFile(name,output.outputText,ts.ScriptTarget.ES2022,true,ts.ScriptKind.JS);let code=output.outputText;const replacements=[];
   for(const statement of parsed.statements){if(!ts.isImportDeclaration(statement))continue;const specifier=statement.moduleSpecifier.text;if(!Object.hasOwn(imports,specifier))throw Error('Unapproved import '+specifier);replacements.push([statement.moduleSpecifier.getStart(parsed),statement.moduleSpecifier.end,JSON.stringify(imports[specifier])]);}
   for(const [a,b,text]of replacements.reverse())code=code.slice(0,a)+text+code.slice(b);
   fs.writeFileSync(work+'/'+name,code);result.compiled.push({name,sha256:hash(code)});
 };
 let component;
 for(const source of manifest.sources){const raw=fs.readFileSync(source.local_path);if(hash(raw)!==source.sha256)throw Error('source integrity '+source.name);if(source.name==='component')component=raw.toString();else compile(source.name,raw.toString());}
 const ast=ts.createSourceFile('component.ts',component,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS);
 const klass=ast.statements.filter(ts.isClassDeclaration);if(klass.length!==1)throw Error('class ambiguity');
 const names=['ownerService','ownerResource','emptyOwner','owner','ownerModel'];
 const properties=names.map(name=>{const members=klass[0].members.filter(n=>ts.isPropertyDeclaration(n)&&n.name.getText(ast)===name);if(members.length!==1)throw Error('property ambiguity '+name);return members[0].getText(ast);});
 imports['@angular/core/rxjs-interop']='@angular/core/rxjs-interop';imports['./owner.service.mjs']='./owner.service.mjs';imports['./resource-utils.mjs']='./resource-utils.mjs';
 compile('harness.mjs',"import {computed,inject,linkedSignal,signal} from '@angular/core';\nimport {rxResource} from '@angular/core/rxjs-interop';\nimport {OwnerService} from './owner.service.mjs';\nimport {valueOrDefault} from './resource-utils.mjs';\nexport class Harness { id=signal('7');\n"+properties.join('\n')+'\n}');
 await import(runtime+'/node_modules/@angular/compiler/fesm2022/compiler.mjs');
 const core=await import(runtime+'/node_modules/@angular/core/fesm2022/core.mjs');
 const http=await import(runtime+'/node_modules/@angular/common/fesm2022/http.mjs');
 const testing=await import(runtime+'/node_modules/@angular/common/fesm2022/http-testing.mjs');
 const forms=await import(runtime+'/node_modules/@angular/forms/fesm2022/signals.mjs');
 const {OwnerService}=await import(work+'/owner.service.mjs'),{HttpErrorHandler}=await import(work+'/error.service.mjs'),{ownerSchema}=await import(work+'/owner-form.mjs'),{Harness}=await import(work+'/harness.mjs');
 const {project}=require('./extract_angular_model_projection_v1.cjs');const projection=JSON.parse(fs.readFileSync('manifests/petclinic-model-projection-v1.json')).projection;
 result.angular=core.VERSION.full;
 const turn=()=>new Promise(resolve=>setTimeout(resolve,0));
 for(const row of rows){let injector,controller;row.phase='initialize';
  try{
   injector=core.createEnvironmentInjector([{provide:core.ɵINJECTOR_SCOPE,useValue:'root'},core.ErrorHandler,core.provideZonelessChangeDetection(),http.provideHttpClient(http.withNoXsrfProtection()),testing.provideHttpClientTesting(),OwnerService,HttpErrorHandler],core.Injector.NULL);
   const harness=core.runInInjectionContext(injector,()=>new Harness());const app=injector.get(core.ApplicationRef);controller=injector.get(testing.HttpTestingController);
   row.before={resource_status:harness.ownerResource.status(),has_value:harness.ownerResource.hasValue(),model:harness.ownerModel()};row.phase='request';let requests=[];
   for(let i=0;i<20&&!requests.length;i++){app.tick();await turn();requests=controller.match(()=>true);}
   if(requests.length!==1)throw Error('Expected one intercepted request, got '+requests.length);
   const request=requests[0];row.request={method:request.request.method,url:request.request.urlWithParams};
   if(row.request.method!=='GET'||row.request.url!=='http://localhost:9966/petclinic/api/owners/7')throw Error('Unexpected request');
   request.flush(row.response);row.phase='resource';
   for(let i=0;i<20&&!harness.ownerResource.hasValue();i++){app.tick();await turn();}
   if(!harness.ownerResource.hasValue())throw Error('Resource did not yield value');
   app.tick();row.resource_value=harness.ownerResource.value();row.model=harness.ownerModel();row.projected=project(projection,row.resource_value);
   row.projection_matches=row.projected.status==='projected'&&JSON.stringify(row.model)===JSON.stringify(row.projected.model);row.status='reconstructed';
   row.validation={status:'not_run'};
   try{const tree=forms.form(harness.ownerModel,ownerSchema,{injector});app.tick();row.validation={status:'measured',valid:tree().valid(),error_kinds:tree().errorSummary().map(e=>e.kind)};}catch(error){row.validation={status:'error',error:String(error),stack:error.stack};}
  }catch(error){row.status='error';row.error=String(error);row.stack=error.stack;}
  finally{try{controller?.verify();}catch(error){result.errors.push({phase:'pending_requests',mode:row.mode,error:String(error)});}try{injector?.destroy();}catch(error){result.errors.push({phase:'cleanup',mode:row.mode,error:String(error)});}}
 }
}catch(error){result.errors.push({phase:'setup_import',error:String(error),stack:error.stack});}
finally{clearTimeout(timer);save();}
if(result.errors.length||rows.some(r=>r.status!=='reconstructed'||!r.projection_matches||r.validation?.status==='error'))process.exitCode=1;
