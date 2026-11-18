// Pure proposed scoring helper. Does not execute or authorize experiments.
import {equal,decodedConfig,framePreserved} from '../redesign-gomodel-ordinary-v2/frame.mjs';
export {equal};
function row(s,name){const t=s.tables.guardrail_definitions;const i=t.columns.indexOf('name');const r=t.rows.find(r=>r[i]===name);if(!r)throw Error('missing target');return {t,r,k:t.columns.indexOf('config')};}
function encodedLike(original,value){const text=JSON.stringify(value);return typeof original==='string'?text:{blob_base64:Buffer.from(text).toString('base64')};}
export function configOf(s,name){const x=row(s,name);return decodedConfig(x.r[x.k]);}
export function expectedConfig(before,name,target,unrelated,value,repair){
 if(target===unrelated)throw Error('repair target and unrelated edit must differ');
 const c=structuredClone(configOf(before,name));c[unrelated]=value;
 if(repair.enabled)c[target]=repair.value;
 return c;
}
// Verify all state with the ordinary exact frame helper after reducing the
// prespecified target intervention to a common representation on both sides.
export function fullFrame(before,after,name,target,unrelated,value,repair){try{
 const want=expectedConfig(before,name,target,unrelated,value,repair),got=configOf(after,name);
 if(!equal(want,got))return false;
 const b=structuredClone(before),a=structuredClone(after);
 for(const s of [b,a]){const x=row(s,name),c=decodedConfig(x.r[x.k]);delete c[target];x.r[x.k]=encodedLike(x.r[x.k],c);}
 return framePreserved(b,a,name,unrelated,value);
}catch{return false;}}
export function scoreState(before,after,name,target,unrelated,value,repair){
 try{
 const got=configOf(after,name);const intended=Object.hasOwn(got,unrelated)&&equal(got[unrelated],value);
 if(fullFrame(before,after,name,target,unrelated,value,repair))return {label:'intended_edit_frame_preserved',intended,full_frame:true};
 // Diagnose only target representation changes. This does not waive them.
 const want=expectedConfig(before,name,target,unrelated,value,repair);
 const targetSame=Object.hasOwn(want,target)===Object.hasOwn(got,target)&&equal(want[target],got[target]);
 if(!targetSame&&intended){
  const normalized=structuredClone(after),x=row(normalized,name),c=decodedConfig(x.r[x.k]);
  if(Object.hasOwn(want,target))c[target]=want[target];else delete c[target];x.r[x.k]=encodedLike(x.r[x.k],c);
  if(fullFrame(before,normalized,name,target,unrelated,value,repair))return {label:repair.enabled?'repair_target_not_preserved':'target_changed_during_unrelated_edit',intended,full_frame:false};
 }
 return {label:intended?'other_state_difference':'intended_edit_not_observed',intended,full_frame:false};
 }catch(e){return {label:'state_observation_unavailable',error:String(e),full_frame:false};}
}
