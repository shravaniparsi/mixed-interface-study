#!/usr/bin/env python3
"""Generate a finite source-derived inventory; this does not authorize execution."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SEED='production-extension-v1:linkding:20261110'
def build():
    controls=json.loads((ROOT/'manifests/linkding-extension-controls-v2.json').read_text())
    base={w['id']:w['payload'] for w in controls['workflows']}
    sources={p:'https://github.com/sissbruecker/linkding/blob/'+controls['source_commit']+'/'+p for p in ['bookmarks/forms.py','bookmarks/models.py','bookmarks/validators.py','bookmarks/api/serializers.py']}
    constraints={
      'bookmark.url':{'family':'required_url','required':True,'nullable':False,'max_length':2048,'native':'BookmarkForm.url with BookmarkURLValidator; inherited model validation on save','api':'Bookmark.url model and BookmarkSerializer','source_paths':['bookmarks/forms.py','bookmarks/models.py','bookmarks/validators.py','bookmarks/api/serializers.py']},
      'bookmark.title':{'family':'optional_length','required':False,'nullable':False,'max_length':512,'omitted_default':'','native':'BookmarkForm.title max_length=512 required=False','api':'Bookmark.title blank=True and BookmarkSerializer','source_paths':['bookmarks/forms.py','bookmarks/models.py','bookmarks/api/serializers.py']},
      'bundle.name':{'family':'required_length','required':True,'nullable':False,'max_length':256,'native':'BookmarkBundleForm.name max_length=256','api':'BookmarkBundle.name and BookmarkBundleSerializer','source_paths':['bookmarks/forms.py','bookmarks/models.py','bookmarks/api/serializers.py']},
      'bundle.any_tags':{'family':'optional_length','required':False,'nullable':False,'max_length':1024,'omitted_default':'','native':'BookmarkBundleForm.any_tags optional; inherited model validation','api':'BookmarkBundle.any_tags and BookmarkBundleSerializer','source_paths':['bookmarks/forms.py','bookmarks/models.py','bookmarks/api/serializers.py']},
      'bundle.filter_unread':{'family':'enum','required':False,'nullable':False,'options':['off','yes','no'],'omitted_default':'off','native':'BookmarkBundleForm.filter_unread ChoiceField','api':'BookmarkBundle.FILTER_UNREAD_CHOICES and BookmarkBundleSerializer','source_paths':['bookmarks/forms.py','bookmarks/models.py','bookmarks/api/serializers.py']},
      'bundle.filter_shared':{'family':'enum','required':False,'nullable':False,'options':['off','yes','no'],'omitted_default':'off','native':'BookmarkBundleForm.filter_shared ChoiceField','api':'BookmarkBundle.FILTER_SHARED_CHOICES and BookmarkBundleSerializer','source_paths':['bookmarks/forms.py','bookmarks/models.py','bookmarks/api/serializers.py']},
    }
    pool=[]
    def add(flow,field,variant,value=None,omit=False,predictor='unknown'):
        payload=dict(base[flow]);payload.pop(field,None) if omit else payload.update({field:value})
        key=flow+'.'+field;pool.append({'id':flow+'-'+field+'-'+variant,'workflow':flow,'field':field,'variant':variant,'constraint':key,'family':constraints[key]['family'],'payload':payload,'constraint_consistency_prediction':predictor})
    for key,c in constraints.items():
        flow,field=key.split('.')
        add(flow,field,'omitted',omit=True,predictor='violation' if c['required'] else 'compatible')
        add(flow,field,'null',None,predictor='violation')
        add(flow,field,'empty','',predictor='violation' if c['required'] else 'unknown' if c['family']=='enum' else 'compatible')
        if 'max_length' in c:
            for delta in [-1,0,1]:
                size=c['max_length']+delta
                prefix='https://example.invalid/' if field=='url' else ''
                value=prefix+'x'*(size-len(prefix))
                add(flow,field,'length-'+str(size),value,predictor='violation' if delta>0 else 'compatible')
        if c['family']=='enum':add(flow,field,'invalid-option','not-an-option',predictor='violation')
        if field=='url':add(flow,field,'invalid-url','not-a-url',predictor='violation')
    selected=[];remainder=[]
    # Round-robin families; stable seeded ordering within each family.
    for flow in sorted(base):
        families={}
        for case in pool:
            if case['workflow']==flow:families.setdefault(case['family'],[]).append(case)
        for values in families.values():values.sort(key=lambda c:hashlib.sha256((SEED+':'+c['id']).encode()).hexdigest())
        ordered=[]
        while any(families.values()):
            for family in sorted(families):
                if families[family]:ordered.append(families[family].pop(0))
        selected.extend(ordered[:12]);remainder.extend(ordered[12:])
    valid=[]
    variants={'bookmark':[{}, {'title':'Interior title'}, {'title':'x'*511}, {'url':'https://example.invalid/second'}], 'bundle':[{}, {'name':'Interior bundle'}, {'name':'x'*255}, {'filter_unread':'yes','filter_shared':'no'}]}
    for flow,edits in variants.items():
        for i,edit in enumerate(edits):valid.append({'id':flow+'-valid-'+str(i+1),'workflow':flow,'payload':{**base[flow],**edit},'constraint_consistency_prediction':'compatible'})
    return {'kind':'linkding_candidate_inventory_v1','seed':SEED,'source_commit':controls['source_commit'],'sources':sources,'constraints':constraints,'selection':'Family round robin; seeded SHA256 ordering within family; first 12 per workflow. All unselected candidates retained.','validation_layer_note':'Django ModelForm validation executes on the native form POST endpoint. It is not browser-only validation. DOM attributes will be measured separately; source constraints alone do not establish browser enforcement.','source_only_registration':True,'execution_authorized':False,'qualification_required':'Ordinary paired controls plus constraint-specific violating adapter controls, frozen runtime and cost bound must pass before scientific execution.','excluded_fields':{'bookmark.description':'Prescribed unrelated continuation edit','bookmark.notes':'No declared length/range constraint in pinned source','bundle.search':'Prescribed unrelated continuation edit','bundle.all_tags':'Same constraint family as any_tags; field variant does not add a workflow','bundle.excluded_tags':'Same constraint family as any_tags; field variant does not add a workflow'},'normalization_policy':'Compare continuations to persisted prefix. Report producer normalization separately. No observed state change automatically constitutes a defect.','selected_boundary_cases':selected,'unselected_boundary_cases':remainder,'valid_controls':valid,'counts':{'generated_boundary':len(pool),'selected_boundary':len(selected),'unselected_boundary':len(remainder),'valid_controls':len(valid)}}
if __name__=='__main__':
    path=ROOT/'manifests/linkding-candidate-inventory-v1.json'
    text=json.dumps(build(),indent=2)+'\n'
    if path.exists() and path.read_text()!=text:raise SystemExit('Registered inventory differs; use a versioned amendment')
    path.write_text(text);print(json.dumps(build()['counts']))
