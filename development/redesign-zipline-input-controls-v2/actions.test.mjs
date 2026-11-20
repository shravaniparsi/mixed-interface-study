import test from 'node:test';
import assert from 'node:assert/strict';
import {configure} from './actions.mjs';
for(const rendered of ['Markdown content','Markdown content *','Markdown content  *  '])test('original label '+JSON.stringify(rendered),async()=>{
 let visible=false,value;
 const control={waitFor:async()=>{visible=true;},count:async()=>visible?1:0,isEnabled:async()=>true,fill:async x=>{value=x;},inputValue:async()=>value};
 const modal={waitFor:async()=>{},getByLabel:regex=>{assert(regex.test(rendered));assert(!regex.test('Other '+rendered));return control;},getByRole:()=>({click:async()=>{}})};
 await configure({getByRole:()=>modal},{getByRole:()=>({click:async()=>{}})},[['Markdown content','literal']]);assert.equal(value,'literal');
});
