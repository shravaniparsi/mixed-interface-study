'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert'),crypto=require('crypto');
const [parserPath,sourceDir,out]=process.argv.slice(2);
assert(parserPath&&sourceDir&&out);assert(!fs.existsSync(out),'Do not overwrite execution');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const repo=path.resolve(__dirname,'../..');
const evidence=JSON.parse(fs.readFileSync(path.join(repo,'manifests/petclinic-submission-mapping-v1.json')));
assert.equal(hash(fs.readFileSync(parserPath)),evidence.parser.compiler_sha256);
const ts=require(parserPath);assert.equal(ts.version,'6.0.3');
const inventory=JSON.parse(fs.readFileSync(path.join(repo,'manifests/petclinic-source-rule-inventory-v1.json')));
const sources={};
for(const name of ['owner-form.ts','owner.service.ts','owner-add.component.ts','owner-edit.component.ts']){
 const data=fs.readFileSync(path.join(sourceDir,name));
 const entry=inventory.sources.find(x=>x.path.endsWith('/'+name));assert.equal(hash(data),entry.sha256);
 sources[name]=data.toString();
}
function transpile(name){
 const result=ts.transpileModule(sources[name],{reportDiagnostics:true,compilerOptions:{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.CommonJS,experimentalDecorators:true}});
 assert(!result.diagnostics?.some(d=>d.category===ts.DiagnosticCategory.Error));return result.outputText;
}
const compiled=Object.fromEntries(Object.keys(sources).map(name=>[name,transpile(name)]));
const ordinary={firstName:'Ana',lastName:'Test',address:'Street1',city:'Rome',telephone:'1234567890'};
const omitted={...ordinary};delete omitted.address;
const inputs=[['present',ordinary],['omitted',omitted],['null',{...ordinary,address:null}]];
function clone(v){return JSON.parse(JSON.stringify(v));}
async function run(route,label,input){
 const loaded={id:7,...clone(input)},before=JSON.stringify(loaded),requests=[],navigations=[],registered=[];
 const signal=value=>{const read=()=>value;read.set=next=>{value=next;};return read;};
 const dependencies=new Map();
 const angular={Component:()=>target=>target,Injectable:()=>target=>target,signal,
   computed:fn=>()=>fn(),linkedSignal:fn=>signal(fn()),input:()=>()=> '7',inject:token=>{assert(dependencies.has(token),'Unexpected injection');return dependencies.get(token);}};
 class HttpClient{} class HttpErrorHandler{} class Router{}
 const observable=value=>({value,pipe(){return this;}});
 dependencies.set(HttpClient,{get:()=>observable(loaded),post:(url,body)=>capture('POST',url,body),put:(url,body)=>capture('PUT',url,body)});
 function capture(method,url,body){requests.push({method,url,body:clone(body),address_present:Object.hasOwnProperty.call(body,'address'),json:JSON.stringify(body)});return observable(body);}
 dependencies.set(HttpErrorHandler,{createHandleError:()=>()=>()=>{throw Error('Unexpected error handler execution');}});
 dependencies.set(Router,{navigate:args=>navigations.push(args)});
 const signals={schema:fn=>({registeredSchema:fn}),required(){},minLength(){},maxLength(){},pattern(){},
   form:(model,schema,config)=>{registered.push({model,schema,action:config.submission.action});return {};}};
 const imports={'@angular/core':angular,'@angular/forms/signals':signals,'@angular/common/http':{HttpClient},
   '@angular/router':{Router},'rxjs':{firstValueFrom:async obs=>obs.value},'rxjs/operators':{catchError:()=>()=>{}},
   '@angular/core/rxjs-interop':{rxResource:opts=>opts.stream({params:opts.params()})},
   '../../environments/environment':{environment:{REST_API_URL:'http://isolated.invalid/api/'}},
   '../error.service':{HttpErrorHandler},'../utils/form-utils':{notBlank(){}},
   '../../utils/resource-utils':{valueOrDefault:(resource,fallback)=>resource.value??fallback,resourceErrorMessage:()=>null}};
 function load(name){const module={exports:{}};vm.runInNewContext(compiled[name],{module,exports:module.exports,require:id=>{assert(Object.hasOwnProperty.call(imports,id),'Unmocked import '+id);return imports[id];}},{timeout:1000,filename:name});return module.exports;}
 const formModule=load('owner-form.ts');imports['../owner-form']=formModule;
 const serviceModule=load('owner.service.ts');imports['../owner.service']=serviceModule;
 dependencies.set(serviceModule.OwnerService,new serviceModule.OwnerService());
 const name=route==='add'?'owner-add.component.ts':'owner-edit.component.ts';
 const Class=load(name)[route==='add'?'OwnerAddComponent':'OwnerEditComponent'];new Class();
 assert.equal(registered.length,1);
 if(route==='add')registered[0].model.set(clone(input));
 const modelBefore=clone(registered[0].model());await registered[0].action();
 return {route,input_label:label,input:clone(input),model_before_submission:modelBefore,requests,navigations,loaded_resource_unchanged:before===JSON.stringify(loaded)};
}
(async()=>{const rows=[];
 for(const route of ['add','edit'])for(const [label,input] of inputs){try{rows.push(await run(route,label,input));}catch(error){rows.push({route,input_label:label,error:{name:error.name,message:error.message}});}}
 fs.writeFileSync(out,JSON.stringify({scope:'mocked dependency submission-body engineering qualification, not Angular/browser/backend execution',node:process.version,typescript:ts.version,source_hashes:Object.fromEntries(Object.entries(sources).map(([name,s])=>[name,hash(s)])),rows},null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({rows:rows.length,errors:rows.filter(r=>r.error).length}));
})().catch(e=>{console.error(e);process.exitCode=1;});
