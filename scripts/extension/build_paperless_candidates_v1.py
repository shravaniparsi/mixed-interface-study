#!/usr/bin/env python3
"""Finite, prospective Paperless inputs; no execution authorization."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];SEED='production-extension-v1:paperless:20261110'
def build():
    controls=json.loads((ROOT/'manifests/paperless-extension-controls-v1.json').read_text());pool=[];valid=[];flows=[]
    for original in controls['workflows']:
        w=dict(original);w.update(edit_field='name',edit_value='Renamed ordinary '+w['id'],edit_selector='[formcontrolname="name"] input');flows.append(w)
        def add(field,variant,value=None,omit=False,family='length',prediction='unknown',extra=None):
            payload=dict(w['payload']);payload.pop(field,None) if omit else payload.update({field:value});payload.update(extra or {})
            pool.append({'id':w['id']+'-'+field+'-'+variant,'workflow':w['id'],'field':field,'variant':variant,'family':family,'payload':payload,'contract_prediction':prediction,'validation_layer':'browser_enum_and_shared_API' if field=='matching_algorithm' else 'shared_API_endpoint'})
        for field,maximum in [('match',256)]+([('color',7)] if w['id']=='tag' else []):
            add(field,'omitted',omit=True,prediction='compatible');add(field,'null',None,prediction='violation');add(field,'empty','',prediction='compatible' if field=='match' else 'violation')
            for delta in [-1,0,1]:
                value='x'*(maximum+delta) if field=='match' else '#'+('a'*(maximum+delta-1))
                add(field,'length-'+str(maximum+delta),value,prediction='violation' if delta>0 or (field=='color' and delta<0) else 'compatible')
        if w['id']=='tag':add('color','invalid-hex','#gggggg',family='format',prediction='violation')
        add('matching_algorithm','omitted',omit=True,family='enum',prediction='compatible');add('matching_algorithm','null',None,family='enum',prediction='violation')
        for value in [-1,0,6,7]:add('matching_algorithm','value-'+str(value),value,family='enum',prediction='compatible' if value in (0,6) else 'violation')
        add('match','invalid-regex','[',family='cross_field',prediction='violation',extra={'matching_algorithm':4})
        add('match','valid-regex','^ordinary.*$',family='cross_field',prediction='compatible',extra={'matching_algorithm':4})
        for i,extra in enumerate([{}, {'matching_algorithm':0}, {'matching_algorithm':6}, {'matching_algorithm':4,'match':'^ordinary.*$'}]):
            valid.append({'id':w['id']+'-valid-'+str(i+1),'workflow':w['id'],'payload':{**w['payload'],**extra},'contract_prediction':'compatible'})
    selected=[];remainder=[]
    for w in flows:
        families={}
        for c in pool:
            if c['workflow']==w['id']:families.setdefault(c['family'],[]).append(c)
        for cs in families.values():cs.sort(key=lambda c:hashlib.sha256((SEED+':'+c['id']).encode()).hexdigest())
        ordered=[]
        while any(families.values()):
            for family in sorted(families):
                if families[family]:ordered.append(families[family].pop(0))
        selected.extend(ordered[:12]);remainder.extend(ordered[12:])
    return {'kind':'paperless_candidate_inventory_v1','source_commit':controls['source_commit'],'seed':SEED,'execution_authorized':False,'workflows':flows,'continuation_rationale':'Rename is present for all matching algorithms. Pattern and case-insensitive inputs are intentionally hidden for algorithms 0 and 6; their absence is not a native failure. The unchanged hidden fields must still be preserved in persisted readback.','qualification_required':'Ordinary controls, field measurement and negative adapter probes, then the exact finite executor valid-control gate.','constraints':{'match':{'max_length':256,'optional':True,'null_allowed':False,'layer':'shared_API_endpoint'},'matching_algorithm':{'options':[0,1,2,3,4,5,6],'omitted_default':1,'layer':'browser_enum_and_shared_API'},'regex':{'when':'matching_algorithm=4 and match supplied','rule':'Pattern must pass validate_regex_pattern','layer':'shared_API_endpoint'},'tag.color':{'max_length':7,'null_allowed':False,'empty_allowed':False,'layer':'shared_API_endpoint','pattern':'#[0-9a-fA-F]{6}','authority':'TagSerializer.validate_color plus model maximum length'}},'provenance':{'model':'src/documents/models.py: MatchingModel and Tag','serializer':'src/documents/serialisers.py: MatchingModelSerializer.validate_match, TagSerializer.validate_color and model fields','native_visibility':'src-ui/src/app/components/common/edit-dialog/edit-dialog.component.ts: patternRequired','native_enum':'src-ui/src/app/data/matching-model.ts','native_submission':'src-ui/src/app/services/rest/abstract-paperless-service.ts: update uses PUT','api_version':'src/paperless/settings/__init__.py DEFAULT_VERSION=10; native Accept header uses environment.apiVersion'},'unsupported_or_excluded':{'name':'Unrelated continuation edit; not varied as producer boundary.','tag.parent':'Tree-reference fixtures and native identity-to-label measurement are outside this finite inventory. Parent remains null and must be preserved.','owner_permissions':'Matched ordinary actor setup, not an authorization-bypass study.','browser_text_limits':'Inspected text component does not declare required/maxlength. API/model limits are not relabeled as browser constraints.'},'selected_boundary_cases':selected,'unselected_boundary_cases':remainder,'valid_controls':valid,'counts':{'generated_boundary':len(pool),'selected_boundary':len(selected),'unselected_boundary':len(remainder),'valid_controls':len(valid)}}
if __name__=='__main__':
    p=ROOT/'manifests/paperless-candidate-inventory-v1.json';text=json.dumps(build(),indent=2)+'\n'
    if p.exists() and p.read_text()!=text:raise SystemExit('Registered inventory differs; use a versioned amendment')
    p.write_text(text);print(json.dumps(build()['counts']))
