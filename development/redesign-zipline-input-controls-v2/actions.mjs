import assert from 'node:assert/strict';
let observe=()=>{};
export function setObserver(callback){observe=callback;}
async function control(scope,label){
 // Preserve the exact source label, allowing only a presentation asterisk and whitespace.
 const escaped=label.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
 const locator=scope.getByLabel(new RegExp('^'+escaped+'\\s*\\*?\\s*$'));
 try{await locator.waitFor({state:'visible',timeout:10000});assert.equal(await locator.count(),1,label);assert(await locator.isEnabled(),label);return locator;}
 catch(error){observe({label,error:String(error),controls:await scope.locator('input,textarea,select,label').evaluateAll(xs=>xs.map(x=>({tag:x.tagName,type:x.getAttribute('type'),id:x.id,htmlFor:x.getAttribute('for'),ariaLabel:x.getAttribute('aria-label'),ariaLabelledBy:x.getAttribute('aria-labelledby'),labelText:x.tagName==='LABEL'?x.textContent:null}))).catch(()=>[])});throw error;}
}
export async function configure(page,outer,values){
 await outer.getByRole('button',{name:'Configure components',exact:true}).click();
 const modal=page.getByRole('dialog',{name:'Discord Components V2',exact:true});await modal.waitFor();
 for(const [label,value] of values){const input=await control(modal,label);await input.fill(value);assert.equal(await input.inputValue(),value,label);observe({label,status:'filled_expected_value'});}
 await modal.getByRole('button',{name:'Close',exact:true}).click();await modal.waitFor({state:'hidden'});
}
export async function setField(page,editor,field,value){
 if(field.pointer.startsWith('/discordComponentEmbed/'))return configure(page,editor,[[field.label,value]]);
 const input=await control(editor,field.label);await input.fill(value);assert.equal(await input.inputValue(),value,field.label);observe({label:field.label,status:'filled_expected_value'});
}
export {put} from '../redesign-zipline-inputs-v1/actions.mjs';
