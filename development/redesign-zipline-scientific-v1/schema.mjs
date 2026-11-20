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
const rows=input.map(row=>check(row.name,row.method==='POST'?post:patch,row.httpPart,row.value));
writeFileSync(outFile,JSON.stringify({status:'observed',handlers_invoked:false,rows},null,2)+'\n');
