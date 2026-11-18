process.env.TZ = 'UTC'; // Registered runtime timezone, isolated test process.
import test from 'node:test';
import assert from 'node:assert/strict';
import {loadSeatsurfingApiState} from '../scripts/extension/load_seatsurfing_api_state_v1.mjs';
import {runSeatsurfingApiContinuation} from '../scripts/extension/run_seatsurfing_api_continuation_v1.mjs';
const id='00000000-0000-4000-8000-000000000001';
function fixture(permission=30) {
  const calls=[],location='/location/'+id;
  const values={'/user/me':{id:'actor',permissions:{groups:permission}},'/setting/':[{name:'feature_groups',value:'1'}],
    [location]:{id,name:'Persisted area',description:'Persisted description',announcement:'Persisted notice',maxConcurrentBookings:0,timezone:'',enabled:true,mapScale:1,mapType:'',allowedBookerGroupIds:[],bookableDays:[],blockedFrom:'',blockedUntil:''},
    '/group/':[],[location+'/space/']:[],[location+'/map']:{width:0,height:0,data:''},'/space-attribute/':[],[location+'/attribute']:[], '/setting/timezones':['UTC']};
  const fetchImpl=async(url,options)=>{const path=new URL(url).pathname;calls.push({path,...options});assert.equal(options.redirect,'manual');assert.equal(options.headers.authorization,'Bearer synthetic');assert.ok(Object.hasOwn(values,path));return new Response(JSON.stringify(values[path]),{status:200,headers:{'content-type':'application/json'}});};
  return {id,credentials:{accessToken:'synthetic',accessTokenExpiryMs:Date.now()+600000},fetchImpl,calls,values};
}
test('independent GETs retain persisted inputs with explicit API provenance',async()=>{
  const x=fixture(),r=await loadSeatsurfingApiState(x);assert.equal(r.outcome,'source_inputs_loaded');assert.equal(r.acquisition,'independent_api_gets');assert.equal(r.nativeRequestTraceFabricated,false);assert.equal(r.materialization.readback.name,'Persisted area');assert.equal(x.calls.length,9);assert.ok(x.calls.every(c=>c.method==='GET'));assert.equal(r.runtimeQualified,false);
});
test('group read follows original permission condition',async()=>{const x=fixture(0),r=await loadSeatsurfingApiState(x);assert.equal(r.outcome,'source_inputs_loaded');assert.equal(x.calls.some(c=>c.path==='/group/'),false);assert.deepEqual(r.materialization.groups,[]);});
test('rejected first read stops without retry or writes',async()=>{let count=0;const x=fixture();x.fetchImpl=async()=>{count++;return new Response('{}',{status:403});};const r=await loadSeatsurfingApiState(x);assert.equal(r.outcome,'loading_unavailable');assert.equal(count,1);assert.equal(r.envelopes[0].status,403);});
test('insufficient original credential lifetime dispatches nothing',async()=>{const x=fixture();x.credentials.accessTokenExpiryMs=Date.now()+1000;await assert.rejects(()=>loadSeatsurfingApiState(x));assert.equal(x.calls.length,0);});
test('oversized response cannot supply source inputs',async()=>{const x=fixture();x.fetchImpl=async()=>new Response(' '.repeat(524289));const r=await loadSeatsurfingApiState(x);assert.equal(r.outcome,'loading_unavailable');assert.match(r.envelopes[0].error.message,/bound/);});
test('timeout retains pending read and cannot trigger later requests',async()=>{
  const x=fixture();let release,count=0;x.fetchImpl=()=>{count++;return new Promise(resolve=>{release=resolve;});};
  const r=await loadSeatsurfingApiState({...x,timeoutMs:20});assert.equal(r.outcome,'observation_deadline');assert.equal(r.envelopes[0].outcome,'pending');
  release(new Response(JSON.stringify(x.values['/user/me'])));await new Promise(resolve=>setTimeout(resolve,20));assert.equal(count,1);assert.equal(r.envelopes[0].outcome,'pending');
});
test('continuation updates from independently loaded persisted values',async()=>{
  const x=fixture(),read=x.fetchImpl,writes=[];
  x.fetchImpl=async(url,options)=>{if(options.method==='GET')return read(url,options);writes.push({url,...options});return new Response(null,{status:204});};
  const r=await runSeatsurfingApiContinuation({...x,edit:{path:'/description',value:'Edit description'}});
  assert.equal(r.outcome,'continuation_observed');assert.equal(writes.length,1);assert.equal(JSON.parse(writes[0].body).name,'Persisted area');assert.equal(JSON.parse(writes[0].body).description,'Edit description');assert.equal(r.applicationPersistenceQualified,false);
});
test('failed loading never dispatches the continuation',async()=>{const x=fixture();const methods=[];x.fetchImpl=async(url,options)=>{methods.push(options.method);return new Response('{}',{status:500});};const r=await runSeatsurfingApiContinuation({...x,edit:{path:'/description',value:'Edit description'}});assert.equal(r.outcome,'loading_unavailable');assert.deepEqual(methods,['GET']);});

test('wrong runtime timezone is rejected before any read or write',async()=>{
  const x=fixture();process.env.TZ='America/Los_Angeles';
  try { await assert.rejects(()=>runSeatsurfingApiContinuation({...x,edit:{path:'/description',value:'Edit description'}}),/UTC runtime/);assert.equal(x.calls.length,0); }
  finally {process.env.TZ='UTC';}
});
