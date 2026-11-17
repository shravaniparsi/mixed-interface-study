'use strict';
const fs=require('fs'),assert=require('assert');
const {analyze,project}=require('./extract_angular_model_projection_v1.cjs');
const ts=require(process.argv[2]);assert.equal(ts.version,'6.0.3');
const source=fs.readFileSync(process.argv[3],'utf8');
const fields=['firstName','lastName','address','city','telephone'];
const extract=s=>analyze(ts,s,'ownerSchema',fields);
const result=extract(source);assert.equal(result.status,'source_model_projection');
assert.equal(result.input_expression,'this.owner()');assert.equal(result.projection.length,5);
assert.equal(project(result,{}).model.address,'');
assert.equal(project(result,{address:undefined}).model.address,'');
assert.equal(project(result,{address:null}).model.address,null);
assert.equal(project(result,{address:'Street 1'}).model.address,'Street 1');
assert.equal(project(result,{address:false}).model.address,false);
assert.equal(project(result,null).status,'unknown');
const object={};Object.defineProperty(object,'address',{get(){throw Error('must not invoke getter');}});
assert.equal(project(result,object).status,'unknown');
const input={address:'Street 1'};project(result,input);assert.deepEqual(input,{address:'Street 1'});
const mutations=[
 ["address = ''","address = getDefault()"],
 ["address = ''","address: renamed = ''"],
 ['return {firstName, lastName, address, city, telephone};','return {firstName, lastName, address: address.trim(), city, telephone};'],
 ['return {firstName, lastName, address, city, telephone};','address = "changed"; return {firstName, lastName, address, city, telephone};'],
 ['= this.owner();','= this.owner("extra");'],
 ['linkedSignal<OwnerFormModel>(() => {','linkedSignal<OwnerFormModel>((context) => {'],
 ["address = ''","address = null"],
 ['return {firstName, lastName, address, city, telephone};','return {...this.owner()};'],
];
for(const [from,to]of mutations){assert(source.includes(from));assert.equal(extract(source.replace(from,to)).status,'unresolved',to);}
console.log('Projection source and development rejection checks passed; no API binding qualification.');
