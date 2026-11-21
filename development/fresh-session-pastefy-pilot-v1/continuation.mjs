// Observe positive blocking and write outcomes without turning timeouts into defects.
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {session} from '../fresh-session-pastefy-v1/browser.mjs';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH);
const [inputPath,outputPath]=process.argv.slice(2),input=JSON.parse(await fs.readFile(inputPath,'utf8'));
const credentials=JSON.parse(await fs.readFile(input.credentials,'utf8'));
const diagnostics={},pageErrors=[];let browser,s;
const report={status:'unavailable',diagnostics,pageErrors};
try {
 browser=await chromium.launch({headless:true,timeout:30000,args:['--no-sandbox']});
 s=await session(browser,'http://127.0.0.1:1337',credentials,diagnostics,{configureContext:async(context,page)=>{page.on('pageerror',e=>pageErrors.push(String(e)));}});
 report.actor=s.actor;
 const form=await s.prepareEdit(input.key,input.field,input.value);await s.page.waitForTimeout(350);
 const button=form.locator('button[type="submit"]');report.control={disabled:await button.isDisabled(),invalid:await form.locator(':invalid').count()};
 if(report.control.disabled||report.control.invalid)report.status=pageErrors.length?'client_runtime_error':'positive_client_blocking';
 else {report.body=await s.commitEdit(input.key);report.status='native_action_completed';}
} catch(error){report.error=String(error);report.status=pageErrors.length?'client_runtime_error':'unavailable';}
finally {
 if(s){report.receipts=s.receipts;report.url=s.page.url();}
 if(browser)await Promise.race([browser.close(),new Promise(resolve=>setTimeout(resolve,5000))]);
 await fs.writeFile(outputPath,JSON.stringify(report));
}
