"""Finite runtime gates. The independent verifier separately reconstructs raw traces."""
import re

def without_updated(v):return {k:x for k,x in v.items() if k!='updated'}
def color_display(value):
    if not isinstance(value,str):return None
    v=value.removeprefix('#')
    if re.fullmatch('[0-9a-fA-F]{3}',v):return '#'+''.join(c*2 for c in v).lower()
    if re.fullmatch('[0-9a-fA-F]{6}',v):return '#'+v.lower()
    return None

def classify(o,s):
    r=dict(outcome='unresolved',contract=[],consistency=[],representation_signal=False,documented_normalization=False)
    if o.get('producer_status')!=201:
        unchanged=o.get('after_failed_producer')==o.get('initial_raw') and ('fixture_initial' not in o or o.get('fixture_final')==o['fixture_initial'])
        if o.get('status')=='observed' and o.get('browser_cleanup_confirmed') and o.get('producer_status') in [400,409,422] and unchanged:r['outcome']='producer_rejected'
        return r
    p=o.get('prefix');f=o.get('final');task=s['id']=='task'
    if not isinstance(p,dict):return r
    title=p.get('title');limit=1000 if task else 250
    if not isinstance(title,str) or not 1<=len(title)<=limit:r['contract'].append('title:length')
    if s['id']=='project':
        v=p.get('identifier')
        if not isinstance(v,str) or len(v)>10:r['contract'].append('identifier:length')
        if not isinstance(v,str) or len(v)>10:r['consistency'].append('identifier:native_maxlength')
    color=p.get('hex_color')
    if not isinstance(color,str) or (color!='' and color_display(color) is None):r['contract'].append('hex_color:optional_hex')
    if not task and (not isinstance(color,str) or (color!='' and color_display(color) is None)):r['consistency'].append('hex_color:native_color')
    if task and (not isinstance(title,str) or not title.strip()):r['consistency'].append('title:trimmed_nonempty')
    if o['channel']=='ui':
        loaded=next((x for x in o.get('forms',[]) if x['label']=='loaded'),None)
        if loaded:
            r['representation_signal']=loaded['title']!=(title.strip() if task and isinstance(title,str) else title) or loaded['description_text']!='Ordinary description'
            if not task:r['representation_signal']|=not ((loaded['color_empty'] and color=='') or (not loaded['color_empty'] and loaded['color']==color_display(color)))
            if s['id']=='project':r['representation_signal']|=loaded['identifier']!=p.get('identifier')
    if o['channel']=='ui' and (len(o.get('native_requests',[]))>1 or len(o.get('fetch_requests',[]))>1):return r
    if o.get('status')!='observed' or not o.get('browser_cleanup_confirmed') or not isinstance(f,dict):return r
    if 'fixture_prefix' in o and without_updated(o.get('fixture_final',{}))!=without_updated(o['fixture_prefix']):r['outcome']='preservation_or_edit_discrepancy';return r
    expected={**p,('description' if task else 'title'):s['edit_value']}
    if o.get('continuation_status')==200:
        if without_updated(f)==without_updated(expected):r['outcome']='clean'
        elif task and o['channel']=='ui' and isinstance(title,str) and title!=title.strip() and without_updated(f)==without_updated({**expected,'title':title.strip()}):r.update(outcome='documented_normalization',documented_normalization=True)
        else:r['outcome']='preservation_or_edit_discrepancy'
    elif o.get('continuation_status') in [400,409,422] and f==p:r['outcome']='continuation_rejected'
    elif o['channel']=='ui' and o.get('save_control',{}).get('disabled') and not o.get('native_requests') and o.get('no_request_window_ms')==1500 and f==p:r['outcome']='blocked_native_control'
    return r

def ordinary_gate(o,s):
    r=classify(o,s)
    return r['outcome']=='clean' and not r['contract'] and not r['consistency'] and not r['representation_signal']
