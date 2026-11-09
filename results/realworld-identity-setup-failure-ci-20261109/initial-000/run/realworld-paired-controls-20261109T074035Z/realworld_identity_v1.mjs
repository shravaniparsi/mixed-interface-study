// Preparation contract for username-changing profile continuations.
// This does not determine whether a registered username ought to be accepted.
import {isDeepStrictEqual as exact} from 'node:util';

const fields=['username','email','bio','image'];
const requireValue=(condition,message)=>{if(!condition)throw new Error(message);};
function principal(value){
  requireValue(value && ['username','email'].every(k=>typeof value[k]==='string' && value[k].length>0),'Incomplete bound principal');
}
function userState(value){
  principal(value);
  requireValue(fields.every(k=>Object.hasOwn(value,k)),'Incomplete current user');
  requireValue(['bio','image'].every(k=>value[k]===null || typeof value[k]==='string'),'Invalid nullable profile field');
  return Object.fromEntries(fields.map(k=>[k,value[k]]));
}
export function profileIdentityExpected(before,patch){
  const result=userState(before);
  requireValue(patch && typeof patch==='object' && !Array.isArray(patch),'Invalid profile patch');
  requireValue(Object.keys(patch).every(k=>fields.includes(k)),'Unsupported profile field');
  for(const [key,value] of Object.entries(patch)){
    if(key==='email')requireValue(value===before.email,'Email changes require a separate authentication contract');
    else if(key==='username'){
      requireValue(typeof value==='string' && value.length>0,'Unsupported accepted username');
      result.username=value;
    }else{
      requireValue(value===null || typeof value==='string','Invalid nullable profile field');
      result[key]=value===null || value===''?null:value;
    }
  }
  return result;
}
export const authorPath=username=>{
  requireValue(typeof username==='string' && username.length>0,'Missing author binding');
  return '/api/articles?author='+encodeURIComponent(username);
};
function slugs(expectedSlugs){
  requireValue(Array.isArray(expectedSlugs) && expectedSlugs.length>0 && expectedSlugs.every(s=>typeof s==='string' && s.length>0)
    && new Set(expectedSlugs).size===expectedSlugs.length,'Invalid fixture article bindings');
  return [...expectedSlugs].sort();
}
export function projectIdentitySnapshot(reads,boundPrincipal,expectedSlugs){
  principal(boundPrincipal);const expected=slugs(expectedSlugs);
  const at=path=>{
    const matches=reads.filter(r=>r.path===path);
    requireValue(matches.length===1 && matches[0].status===200,'Missing, duplicate or unreadable probe: '+path);
    return matches[0].data;
  };
  const user=userState(at('/api/user')?.user);
  requireValue(user.username===boundPrincipal.username && user.email===boundPrincipal.email,'Current principal differs from explicit binding');
  const collection=at(authorPath(boundPrincipal.username));
  requireValue(Array.isArray(collection?.articles) && Number.isSafeInteger(collection.articlesCount)
    && collection.articlesCount===collection.articles.length,'Partial article collection');
  requireValue(exact(collection.articles.map(a=>a?.slug).sort(),expected),'Fixture articles missing, duplicated or foreign');
  const tags=at('/api/tags')?.tags;
  requireValue(Array.isArray(tags) && tags.every(t=>typeof t==='string'),'Invalid tags');
  const articles=collection.articles.map(article=>{
    requireValue(article?.author?.username===boundPrincipal.username,'Article author differs from bound principal');
    requireValue(['title','description','body'].every(k=>typeof article[k]==='string')
      && Array.isArray(article.tagList) && article.tagList.every(t=>typeof t==='string'),'Incomplete article state');
    const comments=at('/api/articles/'+encodeURIComponent(article.slug)+'/comments')?.comments;
    requireValue(Array.isArray(comments) && comments.every(c=>Number.isSafeInteger(c.id) && c.id>0
      && typeof c.body==='string' && typeof c.author?.username==='string')
      && new Set(comments.map(c=>c.id)).size===comments.length,'Invalid comment collection');
    return {article:{...article,tagList:[...new Set(article.tagList)].sort()},comments:[...comments].sort((a,b)=>a.id-b.id)};
  }).sort((a,b)=>a.article.slug<b.article.slug?-1:a.article.slug>b.article.slug?1:0);
  requireValue(reads.length===3+expected.length,'Unregistered snapshot probes');
  return {user,articles,tags:[...new Set(tags)].sort()};
}
export async function identitySnapshot(read,boundPrincipal,expectedSlugs){
  // Validate caller bindings before any request, then retain all attempted probes.
  principal(boundPrincipal);const expected=slugs(expectedSlugs);const reads=[];
  try{
    async function get(path){const response=await read('GET',path);reads.push({path,status:response.status,data:response.data,response_sequence:response.response_sequence});return response;}
    await get('/api/user');await get(authorPath(boundPrincipal.username));await get('/api/tags');
    // Probe fixture references even when the author query unexpectedly returns zero.
    for(const slug of expected)await get('/api/articles/'+encodeURIComponent(slug)+'/comments');
    return {readable:true,reads,data:projectIdentitySnapshot(reads,boundPrincipal,expected)};
  }catch(error){return {readable:false,reads,error:error.message};}
}
