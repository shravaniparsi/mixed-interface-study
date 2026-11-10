// Synchronous checkpoint ordering around an asynchronous, independent SQLite reader.
import assert from 'node:assert/strict';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';
import {readFile, mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const execute=promisify(execFile);
export async function databaseCapture({python,database,directory,event}){
  assert.ok(python && database && directory,'Explicit branch database capture configuration required');
  await mkdir(directory,{recursive:false}); // Reject reused output; never replace a failed attempt.
  const names=['capture_identity_database_v2.py','realworld_identity_db_state_v1.py'];
  const sources={};
  for(const name of names)sources[name]=createHash('sha256').update(await readFile(new URL(name,import.meta.url))).digest('hex');
  const record={version:2,sources,snapshots:{}};
  let pending=false;
  async function take(stage){
    assert.ok(['before_prefix','after_prefix','after_continuation'].includes(stage),'Unknown checkpoint');
    assert.ok(!pending && !Object.hasOwn(record.snapshots,stage),'Duplicate or concurrent checkpoint');
    const prior=Object.keys(record.snapshots);
    assert.deepEqual(prior,stage==='before_prefix'?[]:stage==='after_prefix'?['before_prefix']:['before_prefix','after_prefix'],'Checkpoint order differs');
    pending=true;
    event('database_snapshot_started',{stage});
    try{
      const {stdout}=await execute(python,[fileURLToPath(new URL('./capture_identity_database_v2.py',import.meta.url)),
        '--database',database,'--directory',directory,'--stage',stage],{timeout:15000,maxBuffer:2*1024*1024});
      const value=JSON.parse(stdout);
      assert.equal(value.file,stage+'.sqlite3');
      record.snapshots[stage]=value;
      event('database_snapshot_finished',{stage,file:value.file,sha256:value.sha256});
      return value;
    }finally{pending=false;}
  }
  return {record,take};
}
