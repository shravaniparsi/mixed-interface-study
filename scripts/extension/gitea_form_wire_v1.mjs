/** Decode text-only native forms while retaining duplicate fields and exact raw body. */
export async function formEntries(body,contentType){
 if(typeof body!=='string'||!['application/x-www-form-urlencoded','multipart/form-data'].includes(contentType.split(';')[0]))throw new Error('Unsupported native form transport');
 const parsed=await new Response(body,{headers:{'Content-Type':contentType}}).formData(),entries=[...parsed.entries()];
 if(entries.some(([,value])=>typeof value!=='string'))throw new Error('Unexpected native file field');
 return entries;
}
