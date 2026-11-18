import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash, generateKeyPairSync, sign } from 'node:crypto';
import { verifySeatsurfingActor } from '../scripts/extension/verify_seatsurfing_actor_v1.mjs';
const { privateKey, publicKey } = generateKeyPairSync('rsa', { modulusLength: 2048 });
const key = publicKey.export({ type: 'spki', format: 'pem' });
const ids = Array.from({length: 5}, (_, i) => `00000000-0000-4000-8000-00000000000${i}`);
const sha = raw => createHash('sha256').update(raw).digest('hex');
function fixture() {
  const nowMs = Date.now();
  const claims = { userID: ids[0], sid: ids[1], jti: ids[4], email: 'fixture@example.invalid', iss: 'synthetic-installation', aud: ['synthetic-installation'], iat: Math.floor(nowMs/1000)-1, nbf: Math.floor(nowMs/1000)-1, exp: Math.floor(nowMs/1000)+600 };
  const data = [JSON.stringify({ alg:'RS512', typ:'JWT' }), JSON.stringify(claims)].map(x => Buffer.from(x).toString('base64url')).join('.');
  const accessToken = data + '.' + sign('RSA-SHA512', Buffer.from(data), privateKey).toString('base64url');
  const self = { id: ids[0], email: claims.email, organizationId: ids[2], organization: {id:ids[2]}, accountType:0, requirePassword:true, passwordPending:false, roleIds:[ids[4]], permissions:{locations:3}, totpEnabled:false, hasPasskeys:false, authProviderId:'' };
  const body = JSON.stringify(self);
  return {accessToken, refreshToken:ids[3], publicKey:key, organizationId:ids[2], nowMs,
    events:[{kind:'request',id:1,method:'GET',url:'http://127.0.0.1:8080/user/me'}, {kind:'request_headers',id:1,headers:{authorization:'Bearer '+accessToken}}, {kind:'response',id:1,status:200,bodyCaptured:true,body,bodySha256:sha(body)}, {kind:'finished',id:1}],
    database:{user:{id:ids[0],email:claims.email,organization_id:ids[2],account_type:0,disabled:false}, session:{id:ids[1],user_id:ids[0]}, refreshToken:{id:ids[3],user_id:ids[0],session_id:ids[1],used_at:null}, banInactive:true,observedAtMs:nowMs,sessionExpiresAtMs:nowMs+600000,refreshExpiresAtMs:nowMs+600000, assignments:[{user_id:ids[0],role_id:ids[4],scope_type:'',scope_id:''}],roles:[{id:ids[4],organization_id:ids[2],system:true}]}};
}
function changeSelf(x, edit) { const row=x.events.find(e=>e.kind==='response');const value=JSON.parse(row.body);edit(value);row.body=JSON.stringify(value);row.bodySha256=sha(row.body); }
test('signed identity agrees across native response and database but does not qualify full state',()=>{
  const x=fixture(), result=verifySeatsurfingActor(x);assert.equal(result.identityConsistent,true);assert.equal(result.runtimeQualified,false);assert.equal(result.databaseAcquisitionProvenanceVerified,false);
  assert.equal(verifySeatsurfingActor({...x,expectedContinuity:result.continuity}).identityConsistent,true);
});
test('tampered JWT is rejected',()=>{const x=fixture();const parts=x.accessToken.split('.');const signature=Buffer.from(parts[2],'base64url');signature[0]^=1;parts[2]=signature.toString('base64url');x.accessToken=parts.join('.');assert.throws(()=>verifySeatsurfingActor(x),/signature/);});
test('wrong token in native request is rejected',()=>{const x=fixture();x.events[1].headers.authorization='Bearer different';assert.throws(()=>verifySeatsurfingActor(x));});
test('response from another user is rejected',()=>{const x=fixture();changeSelf(x,v=>{v.id=ids[4];});assert.throws(()=>verifySeatsurfingActor(x));});
test('used refresh token is rejected',()=>{const x=fixture();x.database.refreshToken.used_at='synthetic-used';assert.throws(()=>verifySeatsurfingActor(x));});
test('session belonging to another user is rejected',()=>{const x=fixture();x.database.session.user_id=ids[4];assert.throws(()=>verifySeatsurfingActor(x));});
test('missing administrator assignment is rejected',()=>{const x=fixture();x.database.roles[0].system=false;assert.throws(()=>verifySeatsurfingActor(x),/system role/);});
test('stale database evidence is rejected',()=>{const x=fixture();x.database.observedAtMs-=60000;assert.throws(()=>verifySeatsurfingActor(x),/Stale/);});
test('changed resolved permissions across branches are rejected',()=>{const x=fixture();const before=verifySeatsurfingActor(x).continuity;changeSelf(x,v=>{v.permissions.locations=1;});assert.throws(()=>verifySeatsurfingActor({...x,expectedContinuity:before}),/across branches/);});
test('missing response capture is rejected',()=>{const x=fixture();x.events=x.events.filter(e=>e.kind!=='response');assert.throws(()=>verifySeatsurfingActor(x),/Missing or duplicate/);});

test('offline verifier binds exact input file and privately reports signature failure', async () => {
  const { mkdtemp, writeFile, readFile, rm, stat } = await import('node:fs/promises');
  const { tmpdir } = await import('node:os');
  const { join } = await import('node:path');
  const { spawnSync } = await import('node:child_process');
  const directory = await mkdtemp(join(tmpdir(), 'seatsurfing-actor-offline-'));
  try {
    for (const tampered of [false, true]) {
      const x = fixture(); x.publicKey = key.toString();
      if (tampered) x.database.session.user_id = ids[4];
      const input = join(directory, tampered ? 'bad-input.json' : 'input.json');
      const output = join(directory, tampered ? 'bad-output.json' : 'output.json');
      const raw = JSON.stringify(x); await writeFile(input, raw, { mode: 0o600 });
      const run = spawnSync(process.execPath, [new URL('../scripts/extension/verify_seatsurfing_actor_file_v1.mjs', import.meta.url).pathname, input, output], { timeout: 15000 });
      assert.equal(run.status, tampered ? 1 : 0); assert.equal(run.stdout.length + run.stderr.length, 0);
      const result = JSON.parse(await readFile(output, 'utf8'));
      assert.equal(result.inputSha256, sha(raw)); assert.equal(result.status, tampered ? 'actor_verification_failed' : 'actor_identity_verified');
      assert.equal((await stat(output)).mode & 0o777, 0o600);
    }
  } finally { await rm(directory, { recursive: true }); }
});
