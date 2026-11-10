"""Shared native-option consistency checker, separate from persisted API contract."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DOMAINS=json.loads((ROOT/'manifests/memos-preference-domains-v1.json').read_text())
def extract(snapshot):
    rows={f['field']:f for f in snapshot['fields']}
    if set(rows)!={'locale','theme','memoVisibility'}:raise ValueError('Incomplete binding')
    result={}
    for field,row in rows.items():
        if row['count']!=1:raise ValueError('Ambiguous control')
        values=[]
        for option in row['options']:
            label=option['text']
            if field=='locale':
                matches=[v for v in DOMAINS[field] if label.endswith(v)]
                # The pinned locale picker renders a code after the native name.
                if not matches:raise ValueError('Unmapped locale label')
                longest=max(map(len,matches));matches=[v for v in matches if len(v)==longest]
            else:matches=[v for v,text in DOMAINS[field].items() if label==text]
            if len(matches)!=1:raise ValueError('Ambiguous option mapping')
            values.append(matches[0])
        if len(values)!=len(set(values)) or set(values)!=set(DOMAINS[field]):raise ValueError('Source/DOM inventory mismatch')
        result[field]=sorted(values)
    return result

def check_preferences(record,options):
    contract=[];consistency=[]
    for key in ['locale','theme','memoVisibility']:
        if not isinstance(record.get(key),str):contract.append(key+':string')
        if record.get(key) not in options[key]:consistency.append(key+':native_option')
    if record.get('memoVisibility') not in DOMAINS['memoVisibility']:contract.append('memoVisibility:server_enum')
    if type(record.get('saveMediaMetadata')) is not bool:contract.append('saveMediaMetadata:boolean')
    return {'api_contract_signals':contract,'shared_constraint_consistency_signals':consistency}
