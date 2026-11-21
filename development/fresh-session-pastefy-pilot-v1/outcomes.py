"""Classify recorded outcomes. Timeouts never imply validation blocking or a defect."""
import copy,hashlib,json
from client_error_evidence import console_exceptions
from state_frame import frame,row_for,typed,timestamp,TABLE

def accepted(receipt):
 b=receipt.get('body');return 200<=receipt.get('status',0)<300 and isinstance(b,dict) and b.get('success') is True

def producer(case,record,before,after):
 receipt=record.get('producer')
 if receipt is None:return dict(outcome='unavailable',qualified=False)
 result=dict(http_status=receipt['status'],http_accepted=accepted(receipt),qualified=False)
 if not result['http_accepted']:
  result.update(outcome='producer_rejected' if 400<=receipt['status']<500 or isinstance(receipt.get('body'),dict) and receipt['body'].get('success') is False else 'producer_error_or_unconfirmed',persistent_state_unchanged=before==after)
  return result
 key=record.get('key')
 if not key:return dict(**result,outcome='success_without_record_identity')
 try:
  row=row_for(after['database'],key);title=row['title']['value'];content=row['content']['value'];owner=record['actor']['user_id']
  if not (title is None or isinstance(title,str)) or not (content is None or isinstance(content,str)):raise ValueError('unsupported_text_state')
  target=case['target'];expected_text={f:case['input'].get(f,'' if f=='title' else None) for f in ['title','content']};observed=dict(title=title,content=content)
  expected_text[target]=observed[target]
  encoded=None if content is None else content.encode()
  expected={k:typed(v) for k,v in dict(folder=None,expire_at=None,title=expected_text['title'],content=expected_text['content'],user_id=owner,forked_from=None,encrypted=0,type='PASTE',visibility='UNLISTED',storage_type='DATABASE',version=1,indexed_in_elastic=0,length=0 if encoded is None else len(encoded),hash=None if encoded is None else hashlib.sha256(encoded).hexdigest(),key=key,id=row['id']['value'],created_at=row['created_at']['value'],updated_at=row['updated_at']['value']).items()}
  old=before['database'];new=after['database'];db=copy.deepcopy(old);t=db['tables'][TABLE]
  valid=not t['rows'] and row['id']['type']=='integer' and row['id']['value']>0 and timestamp(row['updated_at'])>=timestamp(row['created_at'])
  t['rows']=[[expected[c[1]] for c in t['columns']]]
  if 'sequences' in db:
   valid=valid and db['sequences'][TABLE]==row['id']['value'];db['sequences'][TABLE]=row['id']['value']+1
  valid=valid and db==new and before['files']==after['files'] and row==expected
  readback=record.get('producer_readback',{});body=readback.get('body',{});body=body if isinstance(body,dict) else {}
  agrees=readback.get('status')==200 and readback.get('path')=='/api/v2/paste/'+key and body.get('exists') is True and body.get('id')==key and body.get('user_id')==owner and all(body.get(f)==v for f,v in observed.items())
  requested=case['input'].get(target,'' if target=='title' else None)
  result.update(outcome='accepted_readable' if valid and agrees else 'accepted_unqualified_state_or_readback',qualified=bool(valid and agrees),creation_frame_valid=bool(valid),readback_agrees=bool(agrees),readback_field_presence={f:f in body for f in observed},persisted_text=observed,target_normalized=observed[target]!=requested)
 except (KeyError,ValueError,TypeError) as error:result.update(outcome='accepted_unqualified_state_or_readback',diagnostic=str(error))
 return result

def continuation(before,after,native,key,owner,edit,readback):
 writes=[r for r in native.get('receipts',[]) if r['method'] not in ['GET','HEAD','OPTIONS']]
 state_unchanged=before==after
 if not writes:
  if native.get('status')=='positive_client_blocking' and not native.get('pageErrors') and not console_exceptions(native) and (native.get('control',{}).get('disabled') is True or native.get('control',{}).get('invalid',0)>0) and state_unchanged:return dict(outcome='positive_client_blocking',available=True)
  exceptions=console_exceptions(native)
  if (native.get('pageErrors') or exceptions) and state_unchanged:return dict(outcome='client_runtime_error',available=True,errors=native.get('pageErrors',[]),console_exceptions=exceptions)
  return dict(outcome='unavailable',available=False,persistent_state_unchanged=state_unchanged)
 if len(writes)!=1 or writes[0]['method']!='PUT' or writes[0]['path']!='/api/v2/paste/'+key:return dict(outcome='unexpected_native_writes',available=False)
 write=writes[0]
 try:body=json.loads(write['body'])
 except (KeyError,TypeError,ValueError):body=None
 if not (200<=write['status']<300 and isinstance(body,dict) and body.get('success') is True):
  return dict(outcome='server_rejected' if (400<=write['status']<500 or isinstance(body,dict) and body.get('success') is False) and state_unchanged else 'server_error_or_unaccounted_state',available=bool(state_unchanged and (400<=write['status']<500 or isinstance(body,dict) and body.get('success') is False)))
 try:
  result=frame(before,after,key,owner,{edit['field']:edit['value']});row=row_for(after['database'],key);rb=readback.get('body');rb=rb if isinstance(rb,dict) else {}
  agrees=readback.get('method')=='GET' and readback.get('path')=='/api/v2/paste/'+key and readback.get('status')==200 and rb.get('id')==key and rb.get('user_id')==owner and rb.get('exists') is True and all(rb.get(f)==row[f]['value'] for f in ['title','content'])
  return dict(outcome='exact_intended_edit' if result['status']=='exact_expected_write' and agrees else 'unintended_persistent_changes' if result['status']!='exact_expected_write' else 'unverified_readback',available=bool(agrees),frame=result,readback_agrees=bool(agrees))
 except (KeyError,TypeError,ValueError) as error:return dict(outcome='unavailable',available=False,diagnostic=str(error))
