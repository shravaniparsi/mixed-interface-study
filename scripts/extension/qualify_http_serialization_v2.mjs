import fs from 'node:fs';import crypto from 'node:crypto';import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),root='/private/tmp/reactive14-runtime-v1',hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const routes=[['register','RegisterService','save','POST','api/register'],['create','UserManagementService','create','POST','api/admin/users'],['update','UserManagementService','update','PUT','api/admin/users']];
const output={kind:'exposed_original_service_serializer_package_entries',node:process.version,rows:routes.flatMap(([route])=>['present','undefined','null'].map(mode=>({route,mode,status:'not_run'}))),errors:[],compiled:[],sources:[]};const save=()=>fs.writeFileSync(process.argv[2],JSON.stringify(output,null,2)+'\n');const timer=setTimeout(()=>{output.errors.push({phase:'timeout'});save();process.exit(2);},60000);
let injector;
try{
 const parser='/private/tmp/petclinic-angular-semantics-v1/typescript.cjs',pe=JSON.parse(fs.readFileSync('/private/tmp/petclinic-angular-semantics-v1/typescript-evidence.json'));if(hash(fs.readFileSync(parser))!==pe.compiler_sha256)throw Error('compiler hash');const ts=require(parser);output.typescript=ts.version;output.compiler_sha256=pe.compiler_sha256;
 const setup=JSON.parse(fs.readFileSync('manifests/development-http-setup-source-v1.json'));const checked=(p,e)=>{const raw=fs.readFileSync(p,'utf8');if(hash(raw)!==e.sha256)throw Error('source hash');output.sources.push({path:e.path,sha256:e.sha256});return raw;};
 const config=checked('/private/tmp/development-http-setup-source-v1/1.txt',setup.rows[0]),settings=JSON.parse(checked('/private/tmp/development-http-setup-source-v1/2.txt',setup.rows[1]));if(settings.compilerOptions.target!=='es2020'||settings.compilerOptions.module!=='es2020')throw Error('unexpected target');
 const work=root+'/http-serialization-v2';fs.mkdirSync(work);
 const emit=(name,source)=>{const result=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.ES2020,experimentalDecorators:true,useDefineForClassFields:false},reportDiagnostics:true});if(result.diagnostics?.some(d=>d.category===ts.DiagnosticCategory.Error))throw Error('transpile error');fs.writeFileSync(work+'/'+name,result.outputText);output.compiled.push({name,sha256:hash(result.outputText)});};
 emit('config.mjs',config);
 const evidence=JSON.parse(fs.readFileSync('manifests/development-service-source-screen-v1.json'));
 for(const [index,selected] of [[1,['save']],[2,['create','update']]]){
  const e=evidence.rows.find(r=>r.index===index),source=checked('/private/tmp/development-service-boundary-v1/'+index+'.ts',e),file=ts.createSourceFile('service.ts',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS),classes=file.statements.filter(ts.isClassDeclaration);if(file.parseDiagnostics.length||classes.length!==1)throw Error('parse/class ambiguity');const klass=classes[0];
  const members=klass.members.filter(n=>ts.isConstructorDeclaration(n)||ts.isPropertyDeclaration(n)||(ts.isMethodDeclaration(n)&&selected.includes(n.name.getText(file))));if(members.filter(ts.isMethodDeclaration).length!==selected.length)throw Error('method selection');emit(klass.name.text+'.mjs','export class '+klass.name.text+'{\n'+members.map(n=>n.getText(file)).join('\n')+'\n}');
 }
 const bridge="import '@angular/compiler'; import * as core from '@angular/core'; import * as http from '@angular/common/http'; import * as testing from '@angular/common/http/testing'; export {core,http,testing};";fs.writeFileSync(work+'/package-bridge.mjs',bridge);output.compiled.push({name:'package-bridge.mjs',sha256:hash(bridge)});const {core,http,testing}=await import(work+'/package-bridge.mjs');output.angular=core.VERSION.full;
 injector=core.createEnvironmentInjector([core.importProvidersFrom(testing.HttpClientTestingModule)],core.Injector.NULL);const backend=injector.get(http.HttpBackend),controller=injector.get(testing.HttpTestingController);if(backend!==controller||typeof backend.handle!=='function')throw Error('testing backend identity mismatch');
 const client=new http.HttpClient(backend),{ApplicationConfigService}=await import(work+'/config.mjs'),configuration=new ApplicationConfigService();const services={};for(const name of ['RegisterService','UserManagementService']){const mod=await import(work+'/'+name+'.mjs');services[name]=new mod[name](client,configuration);}
 for(const row of output.rows){let subscription;try{
  const [,name,method,verb,url]=routes.find(r=>r[0]===row.route);const input={login:'ana',email:row.mode==='undefined'?undefined:row.mode==='null'?null:'ana@example.com'};
  row.before={keys:Object.keys(input),email_type:input.email===null?'null':typeof input.email};let values=0,completed=false,error=null;
  subscription=services[name][method](input).subscribe({next:()=>values++,complete:()=>completed=true,error:e=>error=String(e)});
  const pending=controller.expectOne({method:verb,url});const request=pending.request;
  Object.assign(row,{http_method:request.method,url:request.urlWithParams,body_identity:request.body===input,body_keys:Object.keys(request.body),email_own:Object.hasOwn(request.body,'email'),email_type:request.body.email===null?'null':typeof request.body.email,serialized_body:request.serializeBody(),detected_content_type:request.detectContentTypeHeader()});
  pending.flush({});controller.verify();row.after={keys:Object.keys(input),email_type:input.email===null?'null':typeof input.email};Object.assign(row,{values,completed,observable_error:error,status:'measured'});
 }catch(error){Object.assign(row,{status:'error',error:String(error),stack:error.stack});}finally{subscription?.unsubscribe();}}
 try{controller.verify();}catch(error){output.errors.push({phase:'pending_requests',error:String(error)});}
}catch(error){output.errors.push({phase:'setup_import',error:String(error),stack:error.stack});}
finally{try{injector?.destroy();}catch(error){output.errors.push({phase:'cleanup',error:String(error)});}clearTimeout(timer);save();}
if(output.errors.length||output.rows.some(r=>r.status!=='measured'))process.exitCode=1;
