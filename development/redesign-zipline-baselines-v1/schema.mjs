import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
const [runtime,inputFile,outFile]=process.argv.slice(2);
const input=JSON.parse(readFileSync(inputFile));
const require=createRequire(path.join(runtime,'package.json'));
const {validatorCompiler}=require('fastify-type-provider-zod');
const captured=[];
const server=Object.fromEntries(['get','post','patch','delete'].map(method=>[method,(url,options,handler)=>captured.push({method,url,schema:options.schema})]));
for(const file of ['build/server/routes/api/user/urls/index.js','build/server/routes/api/user/urls/[id]/index.js']){
 const original=await import(pathToFileURL(path.join(runtime,file)));await original.default(server,{});
}
const post=captured.find(x=>x.method==='post'&&x.url==='/api/user/urls');
const patch=captured.find(x=>x.method==='patch'&&x.url==='/api/user/urls/:id');assert(post&&patch);
function check(name,route,httpPart,value){const output=validatorCompiler({schema:route.schema[httpPart],method:route.method.toUpperCase(),url:route.url,httpPart})(value);return {name,method:route.method.toUpperCase(),path:route.url,httpPart,input:value,accepted:!output.error,...(output.error?{errors:JSON.parse(JSON.stringify(output.error))}:{value:output.value})};}
const rows=[check('ordinary_create',post,'body',input.api),check('ordinary_headers',post,'headers',{}),check('ordinary_edit',patch,'body',{maxViews:null,destination:input.edit_destination}),check('schema_only_null_destination',post,'body',{...input.api,destination:null}),check('schema_only_trim_vanity',post,'body',{...input.api,vanity:'  schema-calibration  '})];
assert(rows[0].accepted&&rows[1].accepted&&rows[2].accepted&&!rows[3].accepted&&rows[4].accepted);assert.equal(rows[4].value.vanity,'schema-calibration');
writeFileSync(outFile,JSON.stringify({status:'qualified',source:'original compiled route registration and installed validatorCompiler',handlers_invoked:false,live_altered_producers:0,rows},null,2)+'\n');
