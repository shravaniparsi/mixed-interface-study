import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {session} from './browser.mjs';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH);
const [inputPath,outputPath]=process.argv.slice(2);
const input=JSON.parse(await fs.readFile(inputPath,'utf8'));
const credentials=JSON.parse(await fs.readFile(input.credentials,'utf8'));
const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
let s;
try {
 s=await session(browser,'http://127.0.0.1:1337',credentials);
 const body=input.action==='create'?await s.create(input.input):await s.edit(input.key,input.field,input.value);
 await s.close();await fs.writeFile(outputPath,JSON.stringify({status:'native_action_completed',actor:s.actor,body,receipts:s.receipts}));
} finally {await browser.close();}
