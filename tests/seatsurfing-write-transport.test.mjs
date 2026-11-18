import test from 'node:test';
import assert from 'node:assert/strict';
import { bindApiTransport } from '../scripts/extension/seatsurfing_api_transport_v1.mjs';
import { verifyWriteTransport } from '../scripts/extension/verify_seatsurfing_write_transport_v1.mjs';
function diagnostic(request, status, sequence = 1) {
  const url = new URL(request.url), headers = { host: url.host, ...request.headers };
  return { sequence, method: request.method, url: request.url, rawHeaders: request.method + ' ' + url.pathname + ' HTTP/1.1\r\n' + Object.entries(headers).map(([k,v]) => k + ': ' + v + '\r\n').join(''), bodySent: true, sentAt: 1, completedAt: 2, status };
}
function fixture() {
  const environment = { CORS_ORIGINS: '', PUBLIC_SCHEME: 'http', RATE_LIMIT: '250', RATE_LIMIT_PERIOD: '1-M' };
  const examples = [['GET','/read',undefined,200],['POST','/create','{"synthetic":"ordinary"}',201],['PUT','/update','{"synthetic":"café"}',204]];
  const calibration = { status: 'synthetic_receiver_transport_calibrated', nodeVersion: 'v24.18.1', undiciVersion: 'synthetic-fixture', applicationRequestsExecuted: 0, received: [], transport: { failure: null, rows: [] }, gaps: [] };
  for (const [index, [method,path,body,status]] of examples.entries()) {
    const headers = { authorization: 'Bearer synthetic-calibration', ...(body === undefined ? {} : { 'content-type': 'application/json' }) };
    const request = { method, url: 'http://127.0.0.1:1234' + path, headers, ...(body === undefined ? {} : { body }) };
    calibration.transport.rows.push(diagnostic(request,status,index+1));
    calibration.received.push({ method,path,body:body??'',headers:{host:'127.0.0.1:1234',...headers,...(body===undefined?{}:{'content-length':String(Buffer.byteLength(body))})} });
    calibration.gaps.push({method,path,unobservedHeaderNames:body===undefined?[]:['content-length']});
  }
  const headers = { authorization:'Bearer token','content-type':'application/json' };
  const create = { method:'POST',url:'http://127.0.0.1:8080/location/',headers,body:'{}' };
  const envelope = {request:create,response:{status:201}};
  const producerApi = {status:'api_operation_observed',operation:'ordinary_create',result:{envelope},transport:{failure:null,rows:[diagnostic(create,201)]}};
  producerApi.transmittedRequests=bindApiTransport(producerApi.transport,[envelope]);
  const put={method:'PUT',url:'http://127.0.0.1:8080/location/12345678-1234-1234-1234-123456789abc',headers,body:'{}',status:204};
  const continuationApi={status:'api_operation_observed',operation:'ordinary_continue',result:{loaded:{envelopes:[]},execution:{envelopes:[put]}},transport:{failure:null,rows:[diagnostic(put,204)]}};
  continuationApi.transmittedRequests=bindApiTransport(continuationApi.transport,[put]);
  const nativeHeaders={host:'127.0.0.1:8080',...headers,'user-agent':'synthetic-browser'};
  const matched=[{request:put,headers:nativeHeaders}];
  const budget={status:'observed_requests_below_original_rate_limit',whole_process_authenticated_requests:10,original_limit:250,original_period:'1-M'};
  return {calibration,environment,rateBudgets:{status:'ordinary_fixture_stopped_rate_budget_verified',budgets:{warm:budget,native:budget,api:budget}},
    comparisons:{status:'both_native_write_plans_match_independent_api',apiTransportBound:true,warm:{native:{matched}},restoredNative:{native:{matched}}},
    producerNative:{request:{...create,headers:nativeHeaders}},producerApi,continuationApi};
}
test('pinned synthetic calibration and both branches feed a scoped transport verdict',()=>{
  const result=verifyWriteTransport(fixture());assert.equal(result.status,'observed_write_transport_checks_pass');assert.equal(result.applicationQualified,false);assert.equal(result.allClientInventoryRequired,true);
});
test('wrong calibration version or receiver-only header rejects qualification',()=>{
  const x=fixture();x.calibration.nodeVersion='v22.22.3';assert.throws(()=>verifyWriteTransport(x));
  const y=fixture();y.calibration.received[0].headers.cookie='hidden';assert.throws(()=>verifyWriteTransport(y));
});
test('altered saved diagnostics and exceeded request count reject qualification',()=>{
  const x=fixture();x.producerApi.transmittedRequests[0].headers.host='other';assert.throws(()=>verifyWriteTransport(x));
  const y=fixture();y.rateBudgets.budgets.warm.whole_process_authenticated_requests=201;assert.throws(()=>verifyWriteTransport(y));
});
test('unknown native header cannot be silently waived by ordinary success',()=>{
  const x=fixture();x.comparisons.warm.native.matched[0].headers['x-unknown']='value';assert.throws(()=>verifyWriteTransport(x),/Unmapped/);
});
test('offline transport entry point binds its exact private synthetic input',async()=>{
  const {mkdtemp,writeFile,readFile,rm}=await import('node:fs/promises');const {tmpdir}=await import('node:os');const {join}=await import('node:path');const {spawnSync}=await import('node:child_process');const {createHash}=await import('node:crypto');
  const dir=await mkdtemp(join(tmpdir(),'seatsurfing-transport-gate-'));
  try {const input=join(dir,'input.json'),output=join(dir,'output.json'),raw=JSON.stringify(fixture());await writeFile(input,raw,{mode:0o600});
    const run=spawnSync(process.execPath,[new URL('../scripts/extension/verify_seatsurfing_write_transport_file_v1.mjs',import.meta.url).pathname,input,output],{timeout:20000});
    assert.equal(run.status,0);assert.equal(run.stdout.length+run.stderr.length,0);const value=JSON.parse(await readFile(output,'utf8'));
    assert.equal(value.inputSha256,createHash('sha256').update(raw).digest('hex'));assert.equal(value.status,'write_transport_evidence_verified');
  } finally {await rm(dir,{recursive:true});}
});
