import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {session} from './browser.mjs';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH);
const [inputPath,outputPath]=process.argv.slice(2);
const input=JSON.parse(await fs.readFile(inputPath,'utf8'));
const credentials=JSON.parse(await fs.readFile(input.credentials,'utf8'));
console.log('browser-stage launch');
const browser=await chromium.launch({headless:true,timeout:30000,args:['--no-sandbox']});
console.log('browser-stage launched');
let s;const diagnostics=new Proxy({}, {set(object,key,value){object[key]=value;if(key==='stage')console.log('browser-stage '+value);return true;}});
try {
 s=await session(browser,'http://127.0.0.1:1337',credentials,diagnostics);
 const body=input.action==='create'?await s.create(input.input):await s.edit(input.key,input.field,input.value);
 await s.close();await fs.writeFile(outputPath,JSON.stringify({status:'native_action_completed',actor:s.actor,body,receipts:s.receipts}));
} catch(error){
 if(s){diagnostics.url=s.page.url();diagnostics.dom=await Promise.race([s.page.content().catch(()=>null),new Promise(resolve=>setTimeout(()=>resolve(null),3000))]);}
 await fs.writeFile(outputPath,JSON.stringify({status:'native_action_failed',error:String(error),...diagnostics}));throw error;
} finally {await Promise.race([browser.close(),new Promise(resolve=>setTimeout(resolve,5000))]);}
