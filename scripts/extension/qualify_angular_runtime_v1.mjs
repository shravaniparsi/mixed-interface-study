import fs from 'node:fs';
const root='/private/tmp/angular-runtime-qualification-v2';
const cases=[['missing',{}],['undefined',{name:undefined}],['null',{name:null}],['empty',{name:''}],['space',{name:' '}],['letter',{name:'A'}],['astral',{name:'😀'}],['three',{name:'ABC'}]];
const rows=[];
for(const validator of ['required','minLength','maxLength']) for(const inactive of [false,true]) for(const [input,model] of cases) rows.push({validator,inactive,input,status:'not_run'});
const output={kind:'framework_development_qualification',node:process.version,rows,errors:[]};
const save=()=>fs.writeFileSync(process.argv[2],JSON.stringify(output,null,2)+'\n');
const timer=setTimeout(()=>{output.errors.push({phase:'timeout',message:'60 second deadline'});save();process.exit(2);},60000);
try {
  await import(root+'/node_modules/@angular/compiler/fesm2022/compiler.mjs');
  const core=await import(root+'/node_modules/@angular/core/fesm2022/core.mjs');
  const forms=await import(root+'/node_modules/@angular/forms/fesm2022/signals.mjs');
  output.angular=core.VERSION.full;
  for(const row of rows){
    let injector;
    try {
      injector=core.createEnvironmentInjector([{provide:core.ɵINJECTOR_SCOPE,useValue:'root'},core.ErrorHandler,core.provideZonelessChangeDetection()],core.Injector.NULL);
      const model=core.signal({...cases.find(c=>c[0]===row.input)[1]});
      const schema=forms.schema(path=>{
        if(row.validator==='required') forms.required(path.name);
        else forms[row.validator](path.name,2);
        if(row.inactive) forms.disabled(path.name);
      });
      const tree=forms.form(model,schema,{injector});
      injector.get(core.ApplicationRef).tick();
      const state=tree.name();
      Object.assign(row,{status:'measured',disabled:state.disabled(),valid:state.valid(),error_kinds:state.errors().map(e=>e.kind)});
    }catch(error){Object.assign(row,{status:'error',error:String(error),stack:error.stack});}
    finally{try{injector?.destroy();}catch(error){output.errors.push({phase:'cleanup',validator:row.validator,input:row.input,message:String(error),stack:error.stack});}}
  }
}catch(error){output.errors.push({phase:'imports',message:String(error),stack:error.stack});}
finally{clearTimeout(timer);save();}
if(output.errors.length||rows.some(r=>r.status!=='measured'))process.exitCode=1;
