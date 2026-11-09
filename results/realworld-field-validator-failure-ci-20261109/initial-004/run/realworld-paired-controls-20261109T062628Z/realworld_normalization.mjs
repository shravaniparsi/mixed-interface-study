import {isDeepStrictEqual} from 'node:util';
export const exact=isDeepStrictEqual;
export function tags(values){
  if(!Array.isArray(values)||values.some(v=>typeof v!=='string'))throw new Error('Unsupported tag input');
  // Match Python's Unicode code-point ordering, not JS UTF-16 ordering.
  const compare=(a,b)=>{const x=Array.from(a,c=>c.codePointAt(0)),y=Array.from(b,c=>c.codePointAt(0));for(let i=0;i<Math.min(x.length,y.length);i++){if(x[i]!==y[i])return x[i]-y[i];}return x.length-y.length;};
  return [...new Set(values)].sort(compare);
}
export function articleExpected(original,changes){
  if(Object.keys(changes).some(k=>!['title','description','body','tagList'].includes(k)))throw new Error('Unsupported article field');
  const output={};
  for(const key of ['title','description','body']){
    const value=Object.hasOwn(changes,key)?changes[key]:original[key];
    if(typeof value!=='string'||!value)throw new Error('Unsupported accepted article field: '+key);
    output[key]=value;
  }
  output.tagList=tags(Object.hasOwn(changes,'tagList')?changes.tagList:(Object.hasOwn(original,'tagList')?original.tagList:[]));
  output.author='pilotresearch';return output;
}
export function profileExpected(before,patch){
  if(Object.keys(patch).some(k=>!['username','email','bio','image'].includes(k)))throw new Error('Unsupported profile field');
  const result={...before};
  for(const [k,v]of Object.entries(patch)){
    if(['username','email'].includes(k)){if(v!==before[k])throw new Error('Identity changes outside scope');}
    else{if(v!==null&&typeof v!=='string')throw new Error('Unsupported profile value');result[k]=v===null||v===''?null:v;}
  }
  return result;
}
