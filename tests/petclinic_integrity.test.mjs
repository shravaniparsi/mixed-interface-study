import test from 'node:test';
import assert from 'node:assert/strict';
import {guard,enforce,command,expectedPayload,formFields,entityFields,graphSnapshot,compareRejection} from '../scripts/petclinic_integrity.mjs';
const owner={id:1,firstName:'Alice',lastName:'Research',address:'A',city:'C',telephone:'5550100001',pets:[]};
const pet={id:2,ownerId:1,name:'Cat',birthDate:'2024-01-10',type:{id:1,name:'cat'},visits:[]};
const visit={id:3,petId:2,date:'2026-11-06',description:'Check'};
const graph=()=>[{...owner,pets:[{...pet,visits:[visit]}]}];
const snapshot=data=>graphSnapshot({status:200,body:data});
test('command comparison rejects wrong target, omitted fields, nulls and extra fields',()=>{
 const wanted=command('PUT','/pets/2',expectedPayload('pets',pet,{name:'New'}));
 for(const changed of [{...wanted,path:'/pets/3'},{...wanted,payload:null},{...wanted,payload:{...wanted.payload,ownerId:9}}])assert.throws(()=>enforce(guard('command',wanted,changed)),{name:'OperationNotComparable'});
});
test('visit payload must follow returned petId and preserve full bound pet',()=>{
 assert.throws(()=>expectedPayload('visits',visit,{date:'2026-11-07'},{...pet,id:8}));
 const payload=expectedPayload('visits',visit,{date:'2026-11-07'},pet);assert.deepEqual(payload.pet,pet);assert.equal(payload.description,visit.description);
});
test('pet binding retains owner and type while allowing later setup visit',()=>{
 assert.deepEqual(entityFields('pets',pet),entityFields('pets',{...pet,visits:[visit]}));
 assert.equal(guard('binding',entityFields('pets',pet),entityFields('pets',{...pet,ownerId:2})).passed,false);
});
test('native form expectations include birth date and owner display',()=>{
 assert.deepEqual(formFields('pets',pet,owner),{name:'Cat',birthDate:'2024/01/10',typeId:'1',owner_name:'Alice Research'});
 assert.deepEqual(formFields('visits',visit,owner),{date:'2026/11/06',description:'Check'});
});
test('same resource counts cannot hide changed values or relationships after rejection',()=>{
 const before=snapshot(graph());const changed=graph();changed[0].pets[0].visits[0]={...visit,description:'changed'};
 assert.equal(compareRejection(before,snapshot(changed)),'changed');assert.equal(compareRejection(before,snapshot(graph())),'unchanged');
});
test('unreadable, duplicate and broken-link graphs cannot count as unchanged',()=>{
 const data=graph();data[0].pets[0].ownerId=88;
 for(const after of [graphSnapshot({status:500,body:[]}),snapshot(data),snapshot([...graph(),...graph()])])assert.equal(compareRejection(snapshot(graph()),after),'unreadable');
 assert.equal(compareRejection(null,null),'unobserved');
});
test('snapshot is detached from subsequent mutation',()=>{
 const g=graph();const s=snapshot(g);g[0].address='changed';assert.equal(s.data[0].address,'A');
});
