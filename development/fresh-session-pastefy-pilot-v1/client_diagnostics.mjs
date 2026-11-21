// Read-only observations; no script injection or application-state modification.
export function observeConsole(page, report, diagnostics) {
 report.consoleErrors=[];
 page.on('console', message=>{
  if(message.type()!=='error')return;
  if(report.consoleErrors.length>=100){report.consoleErrorsTruncated=true;return;}
  report.consoleErrors.push({text:message.text(),location:message.location(),stage:diagnostics.stage});
 });
}
export async function observeDocument(page, report) {
 let timer;
 try {
  report.document=await Promise.race([
   (async()=>{const html=await page.content();return {url:page.url(),html:html.length<=2000000?html:null,htmlOmitted:html.length>2000000,forms:await page.locator('form').count(),titleInputs:await page.locator('input[placeholder="file.js"]').count()};})(),
   new Promise(resolve=>{timer=setTimeout(()=>resolve({unavailable:'document_observation_deadline'}),3000);})
  ]);
 } catch(error){report.document={unavailable:String(error)};}
 finally{clearTimeout(timer);}
}
