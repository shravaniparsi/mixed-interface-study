'use strict';
const fs=require('fs'),assert=require('assert'),crypto=require('crypto');
const {analyze}=require('./inventory_reactive_payloads_v1.cjs');const ts=require(process.argv[2]);assert.equal(ts.version,'6.0.3');
const sources=JSON.parse(fs.readFileSync('manifests/development-form-source-screen-v1.json'));
const allowed=new Set(JSON.parse(fs.readFileSync('manifests/project-family-partition-v1.json')).rows.filter(r=>r.partition==='development').map(r=>r.full_name));
const rows=[];
for(const item of sources.rows.filter(r=>r.path.endsWith('.ts'))){assert(allowed.has(item.full_name));const raw=fs.readFileSync('/private/tmp/development-form-source-screen-v1/'+item.index+'.txt','utf8');assert.equal(crypto.createHash('sha256').update(raw).digest('hex'),item.sha256);rows.push({full_name:item.full_name,path:item.path,commit:item.commit,source_index:item.index,...analyze(ts,raw)});}
assert.equal(rows.length,6);console.log(JSON.stringify({kind:'exposed_development_component_payload_inventory',rows,independent_evaluation_cases:0,complete_http_mappings:0},null,2));
