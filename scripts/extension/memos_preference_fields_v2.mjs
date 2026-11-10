/** Pinned SettingListItem structure and actual option popups; no private React state. */
import assert from 'node:assert/strict';
export async function readPreferenceFields(page, onField = async () => {}) {
  const fields=[];
  for(const [field,label,role] of [['locale','Language','button'],['theme','Theme','combobox'],['memoVisibility','Default memo visibility','combobox']]){
    const text=page.getByText(label,{exact:true});assert.equal(await text.count(),1,'Unique preference label '+field);
    // SettingList.tsx: label -> text block -> description column -> containing row.
    const row=text.locator('xpath=../../..'),control=row.getByRole(role);assert.equal(await control.count(),1,'Unique preference control '+field);
    const trigger=await control.innerText();await control.click();
    const options=page.getByRole('option');await options.first().waitFor();
    const inventory=await options.evaluateAll(elements=>elements.map(e=>({text:e.textContent.trim(),selected:e.getAttribute('aria-selected'),data_value:e.getAttribute('data-value')})));
    fields.push({field,label,role,count:1,trigger,options:inventory});
    await onField(fields[fields.length-1]);
    await control.click();await options.first().waitFor({state:'hidden'});
  }
  return {fields,document:await page.evaluate(()=>({language:document.documentElement.lang,direction:document.documentElement.dir,theme:document.documentElement.getAttribute('data-theme')}))};
}
export function requireOrdinaryPreferenceFields(snapshot){
  const [locale,theme,visibility]=snapshot.fields;assert.deepEqual(snapshot.fields.map(f=>f.field),['locale','theme','memoVisibility']);
  assert.ok(locale.trigger.includes('English'));assert.ok(locale.options.some(o=>o.selected==='true' && o.text.endsWith('en')));
  assert.ok(theme.trigger.includes('Paper'));assert.deepEqual(theme.options.map(o=>o.text).sort(),['Sync with system','Light','Dark','Paper'].sort());assert.deepEqual(theme.options.filter(o=>o.selected==='true').map(o=>o.text),['Paper']);
  assert.ok(visibility.trigger.includes('Protected'));assert.deepEqual(visibility.options.map(o=>o.text).sort(),['Private','Protected','Public'].sort());assert.deepEqual(visibility.options.filter(o=>o.selected==='true').map(o=>o.text),['Protected']);
}
