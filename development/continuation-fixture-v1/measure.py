"""Attach existing persistence/frame measurements to authored fixture evidence."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.write_observations_v2 import measure
from mixed_interface.write_contract import check
p=Path(sys.argv[1]); data=json.loads(p.read_text()); rows=[]
for row in data['cases']:
    o=row['observation']
    def snapshot(k):
        return {'state':'observed','projection':o[k]} if isinstance(o.get(k),dict) else {'state':'not_planned' if 'before' not in o and o.get('page_status')!=200 else 'missing'}
    before,after=snapshot('before'),snapshot('after')
    m=measure(o.get('submit_status'),before,after,{'state':'not_planned'},
              {'description':'Edited description'}, {'record':{'state':'response','status':200} if isinstance(o.get('after'),dict) else {'state':'missing'}})
    frame=None
    if o.get('submit_status')==200 and before['state']==after['state']=='observed':
        frame=check({'id':row['id'],'before':o['before'],'after':o['after'],
                     'contract':{'assignments':{'description':'Edited description'},
                                 'derived_assignments':{'version':o['before']['version']+1}}})
        assert frame['contract_violation']==(row['id']=='extra_write')
    rows.append({'id':row['id'],'persistence':m,'declared_write_contract':frame})
assert len(rows)==9
(p.parent/'baseline-measurements.json').write_text(json.dumps({'scope':'authored fixture only; no inferred contracts', 'rows':rows},indent=2)+'\n')
