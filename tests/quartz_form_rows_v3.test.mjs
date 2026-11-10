import test from 'node:test';
import assert from 'node:assert/strict';
import {readNativeMapRows,decodeNativeEntries} from '../scripts/quartz_generated_case_v3.mjs';
function editor(rows){
  return {locator(selector){assert.equal(selector,'.data-map-editor .data-map-row');return {
    count:async()=>rows.length,nth:i=>({locator:selector=>({count:async()=>selector==='input'?2:1,
      nth:j=>({inputValue:async()=>selector==='select'?rows[i].type:j===0?rows[i].key:rows[i].value})})})};}};
}
test('read rendered rows without relying on native name attributes',async()=>{
  const rows=[{key:'sample',type:'string',value:'ordinary value'},{key:' padded ',type:'json',value:'{"child":[1,true,null]}'}];
  assert.deepEqual(await readNativeMapRows(editor(rows)),rows);
  assert.deepEqual(decodeNativeEntries(await readNativeMapRows(editor(rows))),{sample:'ordinary value',' padded ':{child:[1,true,null]}});
});
test('empty row list remains empty',async()=>assert.deepEqual(await readNativeMapRows(editor([])),[]));
test('unexpected rendered structure fails closed',async()=>{
  const bad={locator:()=>({count:async()=>1,nth:()=>({locator:()=>({count:async()=>0})})})};
  await assert.rejects(readNativeMapRows(bad),/key and value/);
});
