"""Runtime gates; offline verifier independently reconstructs evidence."""
import re

def preserve(v):return {k:x for k,x in v.items() if k!='updated_at'}
def classify(o,s):
    r=dict(outcome='unresolved',consistency=[],representation_signal=False)
    if s['id']=='issue':
        if o.get('status')=='ordinary_control_passed' and o.get('browser_cleanup_confirmed'):r['outcome']='clean'
        return r
    if o.get('producer_status')!=201:
        if o.get('status')=='observed' and o.get('browser_cleanup_confirmed') and o.get('producer_status') in [400,409,422] and o.get('after_failed_producer')==[]:r['outcome']='producer_rejected'
        return r
    p=o.get('prefix');f=o.get('final')
    if not isinstance(p,dict):return r
    title=p.get('title' if s['id']=='milestone' else 'name')
    if not isinstance(title,str) or not 1<=len(title)<=50:r['consistency'].append('title:required_max50')
    if s['id']=='label':
        color=p.get('color');color_ok=isinstance(color,str) and re.fullmatch(r'#?(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})',color)
        if not color_ok:r['consistency'].append('color:native_hex')
        if p.get('exclusive') and (not isinstance(title,str) or not re.search(r'.*[^/]/[^/].*',title)):r['consistency'].append('exclusive:scoped_name')
    if o['channel']=='ui' and o.get('forms'):
        loaded=o['forms'][0];r['representation_signal']=loaded['title']!=title or loaded['description']!=p['description']
        if s['id']=='label':r['representation_signal']|=loaded['color'].lstrip('#').lower()!=p['color'].lstrip('#').lower() or loaded['exclusive']!=p['exclusive'] or loaded['is_archived']!=p['is_archived']
        else:r['representation_signal']|=loaded['deadline']!='2027-01-15'
    if o.get('status')!='observed' or not o.get('browser_cleanup_confirmed') or not isinstance(f,dict):return r
    if o['channel']=='ui' and (len(o.get('native_requests',[]))>1 or len(o.get('native_attempts',[]))>1):return r
    if o.get('continuation_status') in [200,302,303]:
        r['outcome']='clean' if preserve(f)==preserve({**p,'description':s['edit_value']}) else 'preservation_or_edit_discrepancy'
    elif o.get('continuation_status') in [400,409,422] and f==p:r['outcome']='continuation_rejected'
    elif o['channel']=='ui' and o.get('save_control',{}).get('form_valid') is False and not o.get('native_attempts') and not o.get('native_requests') and o.get('no_request_window_ms')==1500 and f==p:r['outcome']='blocked_native_control'
    return r

def ordinary_gate(o,s):
    r=classify(o,s);return r['outcome']=='clean' and not r['consistency'] and not r['representation_signal']
