"""Runtime outcome gates; independent artifact reconstruction remains separate."""
from memos_preference_constraints_v1 import check_preferences,DOMAINS

def classify(o):
    result={'outcome':'unresolved','contract':[],'consistency':[],'measurement_error':False}
    if o.get('status')!='observed' or not o.get('browser_cleanup_confirmed'):return result
    if o.get('prefix_status')=='rejected':result['outcome']='producer_rejected';return result
    if o.get('prefix_status')!='accepted':return result
    prefix=o['prefix'];memo=o['workflow']=='memo'
    if memo:
        if not isinstance(prefix.get('content'),str):result['contract'].append('content:string')
        elif not prefix['content'].strip():result['consistency'].append('content:trimmed_nonempty_without_attachments')
    else:
        signals=check_preferences(prefix,DOMAINS);result['contract']=signals['api_contract_signals'];result['consistency']=signals['shared_constraint_consistency_signals']
    expected={**prefix,('visibility' if memo else 'saveMediaMetadata'):('PROTECTED' if memo else True)}
    final=o.get('final')
    if o['channel']=='api':
        if o.get('continuation_status')==200:result['outcome']='clean' if final==expected else 'preservation_or_edit_discrepancy'
        elif o.get('continuation_status') in [400,409,422] and final==prefix:result['outcome']='continuation_rejected'
    else:
        requests=o.get('native_requests',[])
        if any('decode_error' in r for r in requests):result['measurement_error']=True;return result
        if o.get('native_disabled') and not requests and final==prefix:result['outcome']='blocked_native_control'
        elif len(requests)==1 and requests[0]['status']==200:result['outcome']='clean' if final==expected else 'preservation_or_edit_discrepancy'
        elif len(requests)==1 and requests[0]['status'] in [400,409,422] and final==prefix:result['outcome']='continuation_rejected'
    return result

def ordinary_gate(o):
    r=classify(o)
    if r['outcome']!='clean' or r['contract'] or r['consistency'] or r['measurement_error']:return False
    if o['channel']=='api':return True
    forms=o['forms']
    if [f['label'] for f in forms]!=['loaded','before_submit','fresh_final']:return False
    if o['workflow']=='memo':
        return all(f['text_content']=='Ordinary memo' and not f['disabled'] for f in forms)
    for f in forms:
        fields=f['preference_fields']['fields'];selected=lambda row:[x['text'] for x in row['options'] if x['selected']=='true']
        if len(fields)!=3 or selected(fields[0])!=['Englishen'] or selected(fields[1])!=['Paper'] or selected(fields[2])!=['Protected']:return False
    return [f['checked'] for f in forms]==['false','false','true']
