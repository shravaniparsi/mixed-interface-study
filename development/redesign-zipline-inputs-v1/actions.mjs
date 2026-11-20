import assert from 'node:assert/strict';
export async function configure(page,outer,values){
 await outer.getByRole('button',{name:'Configure components',exact:true}).click();
 const modal=page.getByRole('dialog',{name:'Discord Components V2',exact:true});await modal.waitFor();
 for(const [label,value] of values) {const control=modal.getByLabel(label,{exact:true});assert.equal(await control.count(),1);assert(await control.isEnabled());await control.fill(value);assert.equal(await control.inputValue(),value);}
 await modal.getByRole('button',{name:'Close',exact:true}).click();await modal.waitFor({state:'hidden'});
}
export async function setField(page,editor,field,value){
 if(field.pointer.startsWith('/discordComponentEmbed/'))return configure(page,editor,[[field.label,value]]);
 const control=editor.getByLabel(field.label,{exact:true});assert.equal(await control.count(),1);assert(await control.isEnabled());await control.fill(value);assert.equal(await control.inputValue(),value);
}
export function put(root,pointer,value){const parts=pointer.slice(1).split('/');let parent=root;for(const key of parts.slice(0,-1)){assert(parent!==null&&typeof parent==='object');parent=parent[key];}parent[parts.at(-1)]=value;return root;}
