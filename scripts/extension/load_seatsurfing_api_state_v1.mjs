/** Independent API loading of source-defined editor inputs. PRIVATE evidence.
 * No native trace/readback is accepted as input. Runtime qualification pending.
 */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mapSeatsurfingLoaderResponses } from './reconstruct_seatsurfing_loader_v1.mjs';
export async function loadSeatsurfingApiState({ id, credentials, baseUrl = 'http://127.0.0.1:8080',
  timeoutMs = 30000, fetchImpl = globalThis.fetch }) {
  assert.equal(baseUrl, 'http://127.0.0.1:8080');
  assert.match(id, /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
  assert.ok(Number.isInteger(timeoutMs) && timeoutMs > 0 && timeoutMs <= 30000);
  assert.ok(typeof credentials.accessToken === 'string' && credentials.accessToken.length > 0);
  assert.ok(Number.isFinite(credentials.accessTokenExpiryMs) && credentials.accessTokenExpiryMs > Date.now() + timeoutMs + 120000);
  const envelopes = [], controller = new AbortController();
  let expired = false, timer;
  const timeout = new Promise(resolve => {
    timer = setTimeout(() => { expired = true; controller.abort(); resolve({ outcome:'observation_deadline' }); }, timeoutMs);
  });
  async function get(path) {
    assert.equal(expired, false, 'Loading deadline expired; no further dispatch');
    const row = { sequence:envelopes.length+1, method:'GET', url:baseUrl+path,
      headers:{authorization:'Bearer '+credentials.accessToken}, dispatchedAt:Date.now(), outcome:'pending' };
    envelopes.push(row);
    try {
      const response = await fetchImpl(row.url, { method:'GET', headers:row.headers, redirect:'manual', signal:controller.signal });
      row.status=response.status;row.responseHeaders=Object.fromEntries(response.headers.entries());
      const chunks=[];let bytes=0;
      if(response.body) {
        const reader=response.body.getReader();
        try {
          while(true) {
            const part=await reader.read();if(part.done)break;
            bytes+=part.value.byteLength;
            if(bytes>524288){await reader.cancel();throw new Error('API loader response exceeds observation bound');}
            chunks.push(Buffer.from(part.value));
          }
        } finally {reader.releaseLock();}
      }
      row.responseBody=Buffer.concat(chunks).toString('utf8');
      row.bodySha256=createHash('sha256').update(row.responseBody).digest('hex');
      assert.equal(row.status,200,'Original loader GET did not return 200');
      const value=JSON.parse(row.responseBody);row.outcome='json_observed';return value;
    } catch(error) {
      row.outcome=expired?'observation_deadline':'http_transport_or_observation_failure';
      row.error={name:error.name,message:error.message};throw error;
    } finally {row.completedAt=Date.now();}
  }
  async function load() {
    const self=await get('/user/me');
    assert.ok(self.permissions && typeof self.permissions==='object');
    const settings=await get('/setting/');
    async function location() {
      const readback=await get('/location/'+id);assert.equal(readback.id,id);
      assert.notEqual(readback.mapType,'designed','Designed map branch remains unqualified');
      const groups=(self.permissions.groups??0)>=10?await get('/group/'):[];
      const rawSpaces=await get('/location/'+id+'/space/');
      const map=await get('/location/'+id+'/map');
      const attributes=await get('/space-attribute/');
      const rawValues=await get('/location/'+id+'/attribute');
      return {readback,groups,rawSpaces,map,attributes,rawValues};
    }
    // Original page starts loadData and timezone loading together, with the
    // location chain ordered. Acquisition remains explicitly API evidence.
    const [loaded,timezones]=await Promise.all([location(),get('/setting/timezones')]);
    return {outcome:'source_inputs_loaded',...mapSeatsurfingLoaderResponses({self,settings,...loaded,timezones})};
  }
  try {
    const operation=load().catch(error=>({outcome:expired?'observation_deadline':'loading_unavailable',error:{name:error.name,message:error.message}}));
    const result=await Promise.race([operation,timeout]);
    expired=true;
    return structuredClone({...result,envelopes,acquisition:'independent_api_gets',retryCount:0,
      nativeRequestTraceFabricated:false,fullStateEqualityEstablished:false,runtimeQualified:false});
  } finally {clearTimeout(timer);controller.abort();}
}
