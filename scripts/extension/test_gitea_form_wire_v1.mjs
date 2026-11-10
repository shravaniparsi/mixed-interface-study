import assert from 'node:assert/strict';
import {formEntries} from './gitea_form_wire_v1.mjs';
assert.deepEqual(await formEntries('title=ordinary&content=edited+text&x=1&x=2','application/x-www-form-urlencoded'),[['title','ordinary'],['content','edited text'],['x','1'],['x','2']]);
const form=new FormData();form.append('title','area/ordinary');form.append('exclusive','on');form.append('description','edited');const request=new Request('http://localhost/',{method:'POST',body:form});assert.deepEqual(await formEntries(await request.text(),request.headers.get('content-type')),[['title','area/ordinary'],['exclusive','on'],['description','edited']]);
await assert.rejects(()=>formEntries('{}','application/json'),/Unsupported/);console.log('URL-encoded and multipart native forms verified.');
