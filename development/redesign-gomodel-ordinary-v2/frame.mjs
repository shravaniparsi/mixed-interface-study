export const canonical=x=>JSON.stringify(x,(_,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
export const equal=(a,b)=>canonical(a)===canonical(b);
function get(snapshot,table,key,value){const t=snapshot.tables[table];if(!t)throw Error('missing '+table);const i=t.columns.indexOf(key);const r=t.rows.find(r=>r[i]===value);if(!r)throw Error('missing '+value);return {t,r,at:k=>{const j=t.columns.indexOf(k);if(j<0)throw Error('missing '+k);return j;}};}
export function decodedConfig(value){return JSON.parse(typeof value==='string'?value:Buffer.from(value.blob_base64,'base64').toString('utf8'));}
function timeOK(a,b){return typeof a===typeof b&&(typeof a==='number'||typeof a==='string')&&b>=a;}
export function framePreserved(before,after,name,field,value){try{
 const normalized=structuredClone(after),b=get(before,'guardrail_definitions','name',name),a=get(normalized,'guardrail_definitions','name',name);
 const bc=decodedConfig(b.r[b.at('config')]),ac=decodedConfig(a.r[a.at('config')]);if(!equal(ac,{...bc,[field]:value}))return false;
 if(!timeOK(b.r[b.at('updated_at')],a.r[a.at('updated_at')]))return false;
 a.r[a.at('config')]=b.r[b.at('config')];a.r[a.at('updated_at')]=b.r[b.at('updated_at')];
 const rb=get(before,'config_revisions','entity','guardrails'),ra=get(normalized,'config_revisions','entity','guardrails');
 if(ra.r[ra.at('revision')]!==rb.r[rb.at('revision')]+1||!timeOK(rb.r[rb.at('updated_at')],ra.r[ra.at('updated_at')]))return false;
 ra.r[ra.at('revision')]=rb.r[rb.at('revision')];ra.r[ra.at('updated_at')]=rb.r[rb.at('updated_at')];
 return equal(before,normalized);
}catch{return false;}}
export function postComparable(snapshot,name){const x=structuredClone(snapshot);for(const [table,key,value]of [['guardrail_definitions','name',name],['config_revisions','entity','guardrails']]){const a=get(x,table,key,value);a.r[a.at('updated_at')]='PERMITTED_UPDATED_AT';}return x;}
