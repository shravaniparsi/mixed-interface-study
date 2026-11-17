'use strict';
const fs=require('fs'),crypto=require('crypto'),assert=require('assert');
const {inventory}=require('./inventory_reactive_forms_v1.cjs');
const ts=require(process.argv[2]);assert.equal(ts.version,'6.0.3');
const partition=JSON.parse(fs.readFileSync('manifests/project-family-partition-v1.json'));
const allowed=new Set(partition.rows.filter(r=>r.partition==='development').map(r=>r.full_name));
const sources=JSON.parse(fs.readFileSync('manifests/development-form-source-screen-v1.json'));
const rows=[];
for(const item of sources.rows.filter(r=>r.path.endsWith('.ts'))){
 assert(allowed.has(item.full_name));assert.equal(item.status,'verified');
 const source=fs.readFileSync('/private/tmp/development-form-source-screen-v1/'+item.index+'.txt','utf8');
 assert.equal(crypto.createHash('sha256').update(source).digest('hex'),item.sha256);
 rows.push({full_name:item.full_name,path:item.path,commit:item.commit,source_index:item.index,...inventory(ts,source)});
}
assert.equal(rows.length,6);
console.log(JSON.stringify({kind:'exposed_development_reactive_syntax_inventory',parser_version:ts.version,rows,framework_runtime_executions:0,complete_api_rules:0,independent_evaluation_cases:0},null,2));
