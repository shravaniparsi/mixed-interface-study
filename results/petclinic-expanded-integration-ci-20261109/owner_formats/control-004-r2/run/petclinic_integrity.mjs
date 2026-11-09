import {isDeepStrictEqual} from 'node:util';

export function guard(name, expected, observed) {
  return {name, expected, observed, passed:isDeepStrictEqual(expected, observed)};
}
export function enforce(record) {
  if (!record.passed) { const e=new Error('Operation not comparable: '+record.name);e.name='OperationNotComparable';throw e; }
}
export function command(method,path,payload=null) {return {method,path,payload};}
export function validId(id) {return Number.isSafeInteger(id)&&id>0;}
export function ownerFields(o) {return Object.fromEntries(['firstName','lastName','address','city','telephone'].map(k=>[k,o[k]]));}
export function entityFields(kind,e) {
  if(kind==='owners')return {id:e.id,...ownerFields(e)};
  if(kind==='pets')return {id:e.id,name:e.name,birthDate:e.birthDate,type:e.type,ownerId:e.ownerId};
  return {id:e.id,date:e.date,description:e.description,petId:e.petId};
}
export function expectedPayload(kind,entity,change,pet) {
  if(kind==='owners')return {...entityFields(kind,entity),...change};
  if(kind==='pets')return {id:entity.id,name:entity.name,birthDate:entity.birthDate,type:entity.type,...change};
  if(!pet||pet.id!==entity.petId)throw new Error('Visit payload pet is not the returned relationship');
  return {id:entity.id,pet,date:entity.date,description:entity.description,...change};
}
export function formFields(kind,entity,owner) {
  if(kind==='owners')return ownerFields(entity);
  if(kind==='pets')return {name:entity.name,birthDate:entity.birthDate.replaceAll('-','/'),typeId:String(entity.type.id),owner_name:owner.firstName+' '+owner.lastName};
  return {date:entity.date.replaceAll('-','/'),description:entity.description};
}
export function graphSnapshot(response) {
  const unreadable=reason=>({readable:false,status:response?.status,reason});
  if(response?.status!==200||!Array.isArray(response.body))return unreadable('Owner graph unavailable');
  const owners=new Set(),pets=new Set(),visits=new Set();
  for(const o of response.body) {
    if(!validId(o.id)||owners.has(o.id)||!Array.isArray(o.pets))return unreadable('Invalid owner graph');owners.add(o.id);
    for(const p of o.pets) {
      if(!validId(p.id)||pets.has(p.id)||p.ownerId!==o.id||!Array.isArray(p.visits))return unreadable('Invalid pet graph');pets.add(p.id);
      for(const v of p.visits) {
        if(!validId(v.id)||visits.has(v.id)||v.petId!==p.id)return unreadable('Invalid visit graph');visits.add(v.id);
      }
    }
  }
  return {readable:true,status:200,data:structuredClone(response.body)};
}
export function compareRejection(before,after) {
  if(!before||!after)return 'unobserved';
  if(!before.readable||!after.readable)return 'unreadable';
  return isDeepStrictEqual(before.data,after.data)?'unchanged':'changed';
}
