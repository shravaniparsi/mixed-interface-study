#!/usr/bin/env python3
"""One fresh-process real MCP observation; no browser or persistence mocks."""
import argparse, copy, json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
from fast_dash import FastDash, depends_on
from fast_dash.mcp import enable_mcp

def main():
 p=argparse.ArgumentParser();p.add_argument('--case',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 countries={'USA':['California','Texas','New York'],'India':['Maharashtra','Karnataka','Delhi']}
 def pick_state(country: str = list(countries), state: str = depends_on('country',lambda c:countries[c]), label: str = 'original') -> str:
  return f'{label}: {state}, {country}'
 record={'case':a.case,'status':'incomplete','calls':[]}
 try:
  app=FastDash(callback_fn=pick_state,mcp_server=True)
  enable_mcp(app);client=app.app.server.test_client()
  def rpc(method,params=None):
   request={'jsonrpc':'2.0','id':len(record['calls'])+1,'method':method,'params':params or {}}
   r=client.post('/mcp',data=json.dumps(request),headers={'Content-Type':'application/json'})
   body=r.get_json();record['calls'].append({'request':request,'http_status':r.status_code,'response':body})
   assert r.status_code==200 and isinstance(body,dict) and 'error' not in body,body
   return body['result']
  def call(name,args=None):
   r=rpc('tools/call',{'name':name,'arguments':args or {}})
   if 'structuredContent' in r:
    return r['structuredContent'].get('result',r['structuredContent'])
   return r
  def snapshot():return copy.deepcopy(app._mcp_state.inputs)
  rpc('initialize');record['tool_catalog']=rpc('tools/list')
  record['setup_parent']=call('set_input',{'component_id':'country','value':'India'})
  assert record['setup_parent']['ok'] is True
  record['setup_child']=call('set_input',{'component_id':'state','value':'Karnataka'})
  assert record['setup_child']['ok'] is True
  if a.case=='already_clear':
   record['setup_clear']=call('set_input',{'component_id':'state','value':None})
   assert record['setup_clear']['ok'] is True
  record['before']=snapshot();record['describe_before']=call('describe_app')
  inputs={
   'parent_change':{'component_id':'country','value':'USA'},
   'label_edit':{'component_id':'label','value':'edited'},
   'explicit_clear':{'component_id':'state','value':None},
   'already_clear':{'component_id':'country','value':'USA'},
  }
  record['input']=inputs[a.case];record['operation_response']=call('set_input',record['input'])
  record['after']=snapshot();record['describe_after']=call('describe_app')
  # Use a new request client against the same application, not a copied fixture.
  client=app.app.server.test_client();rpc('initialize')
  record['fresh_client_readback']=call('describe_app')
  record['before_invoke']=snapshot();record['invoke_response']=call('invoke')
  record['after_invoke']=snapshot();record['history_response']=call('get_invocation',{'index':0})
  record['status']='observed'
 except BaseException as e:record.update(error_type=type(e).__name__,error=str(e))
 finally:
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(record,indent=2)+'\n')
 return 0 if record['status']=='observed' else 1
if __name__=='__main__':raise SystemExit(main())
