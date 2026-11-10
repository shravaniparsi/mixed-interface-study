import assert from 'node:assert/strict';
import {decodeGeneralUpdate as decode} from './memos_general_wire_v1.mjs';
const str = s => Buffer.from(s);
const field = (tag,b) => Buffer.concat([Buffer.from([tag,b.length]),b]);
const name = field(10,str('users/actor/settings/GENERAL'));
const request = flag => field(10,Buffer.concat([name,field(18,flag)]));
const mask = field(18,field(10,str('save_media_metadata')));
const bytes = Buffer.concat([request(Buffer.from([32,1])),mask]);
assert.deepEqual(decode(bytes,'application/proto'), {
 userSetting:{name:'users/actor/settings/GENERAL',generalSetting:{locale:'',memoVisibility:'',theme:'',saveMediaMetadata:true}},
 updateMask:{paths:['save_media_metadata']}
});
assert.equal(decode(Buffer.concat([request(Buffer.alloc(0)),mask]),'application/proto').userSetting.generalSetting.saveMediaMetadata,false);
assert.throws(() => decode(Buffer.concat([request(Buffer.from([32,1,40,0])),mask]),'application/proto'));
assert.throws(() => decode(bytes,'application/connect+proto'));
assert.throws(() => decode(bytes.subarray(0,-1),'application/proto'));
assert.throws(() => decode(Buffer.concat([bytes,request(Buffer.alloc(0))]),'application/proto'));
assert.throws(() => decode(Buffer.concat([request(Buffer.from([32,2])),mask]),'application/proto'));
console.log('GENERAL decoder fixtures passed; live transport qualification remains required');
