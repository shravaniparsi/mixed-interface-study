import {observeConsole,observeDocument} from './client_diagnostics.mjs';
// Original-client request-production prediction only. All writes blocked before navigation.
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {session} from '../fresh-session-pastefy-v1/browser.mjs';
import {installWriteGuard} from './write_guard.mjs';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH);
const [inputPath,outputPath]=process.argv.slice(2);
const input=JSON.parse(await fs.readFile(inputPath,'utf8'));
const credentials=JSON.parse(await fs.readFile(input.credentials,'utf8'));
const origin='http://127.0.0.1:1337',writes=[],diagnostics={},pageErrors=[];
let browser,s;
const report={target:'native_request_production_before_transmission',prediction:'unknown',writes,diagnostics,pageErrors,requires_independent_no_persistence_check:true};
try {
 browser=await chromium.launch({headless:true,timeout:30000,args:['--no-sandbox']});
 s=await session(browser,origin,credentials,diagnostics,{configureContext:(context,page)=>{
   observeConsole(page,report,diagnostics);page.on('pageerror',error=>pageErrors.push(String(error)));
   return installWriteGuard(context,writes);
 }});
 report.actor=s.actor;
 const form=await s.prepareEdit(input.key,input.field,input.value);
 const button=form.locator('button[type="submit"]');
 // Let original debounced title logic settle before observing the native control.
 await s.page.waitForTimeout(350);
 report.control={disabled:await button.isDisabled(),invalid:await form.locator(':invalid').count()};
 if(report.control.disabled||report.control.invalid){
  report.prediction='client_blocks_submission';report.blockingEvidence=report.control;
 } else {
  await button.click({timeout:15000});
  const until=Date.now()+5000;
  while(!writes.length && Date.now()<until)await s.page.waitForTimeout(50);
  const expected=writes.filter(w=>w.origin===origin&&w.method==='PUT'&&w.path==='/api/v2/paste/'+input.key);
  if(writes.length===1&&expected.length===1){report.prediction='native_request_emitted';report.request=JSON.parse(expected[0].request);}
 }
 if(pageErrors.length&&report.prediction!=='native_request_emitted')report.prediction='unknown_client_runtime_error';
} catch(error){report.error=String(error);report.prediction='unknown';}
finally {
 if(s){report.url=s.page.url();report.receipts=s.receipts;await observeDocument(s.page,report);}
 // Closing aborts pending reads; no write can have escaped the context-wide guard.
 if(browser)await Promise.race([browser.close(),new Promise(resolve=>setTimeout(resolve,5000))]);
 await fs.writeFile(outputPath,JSON.stringify(report));
}
