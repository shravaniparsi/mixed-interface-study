/** Read-only observer for streamed Fetch Request bodies omitted by Chromium postData. */
export async function installWriteObserver(page,target,method){
 await page.addInitScript(({target,method})=>{
  const original=window.fetch.bind(window);window.__studyWrites=[];window.__studyWritePromises=[];
  window.fetch=function(input,init){
   const url=new URL(input instanceof Request?input.url:String(input),location.href),verb=init?.method??(input instanceof Request?input.method:'GET');
   if(url.origin!==location.origin||url.pathname!==target||verb.toUpperCase()!==method)return original(input,init);
   // Clone only the selected business write, never authentication or unrelated traffic.
   const request=input instanceof Request?new Request(input.clone(),init):new Request(input,init);
   const record={method:verb.toUpperCase(),path:url.pathname,content_type:request.headers.get('content-type'),body:null,status:null};window.__studyWrites.push(record);
   const bodyRead=request.text().then(body=>{record.body=body}).catch(error=>{record.read_error=String(error)});window.__studyWritePromises.push(bodyRead);
   const response=original(input,init);response.then(r=>{record.status=r.status},error=>{record.fetch_error=String(error)});return response;
  };
 },{target,method});
}
export async function collectWriteObserver(page){return page.evaluate(async()=>{await Promise.all(window.__studyWritePromises??[]);return window.__studyWrites??[]})}
