#!/usr/bin/env python3
"""Freeze API-schema-only input samples before new frontend constraint inspection."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def resolve(schema,document):
    s=dict(schema)
    if '$ref' in s:
        ref=s.pop('$ref');assert ref.startswith('#/');target=document
        for key in ref[2:].split('/'):target=target[key.replace('~1','/').replace('~0','~')]
        s={**resolve(target,document),**s}
    if 'allOf' in s:
        parts=s.pop('allOf');assert len(parts)==1,'Unsupported compound intersection';s={**resolve(parts[0],document),**s}
    return s

def build():
    selection=read(ROOT/'manifests/independent-input-selection-v1.json');seed=selection['seed'];sources={};documents={}
    for name in ['independent-api-capture-results-v1','independent-api-capture-results-v2']:
        proof=ROOT/'manifests'/f'{name}.json';sources[str(proof.relative_to(ROOT))]=sha(proof)
        for app,row in read(proof)['records'].items():
            assert row['qualified'];p=ROOT/row['schema'];assert sha(p)==row['schema_sha256'];documents[app]=read(p);sources[row['schema']]=sha(p)
    definitions={
        'paperless.storage_path':dict(component='StoragePathRequest',producer_method='POST',producer_path='/api/storage_paths/',edit_field='name',base={'name':'Ordinary storage path','path':'study-storage','match':'study','matching_algorithm':1,'is_insensitive':True,'owner':1},excluded={'set_permissions':'Nested permission mutation outside scalar independent-input scope'},references={'owner':[1]},fixture_constraints={'owner':'Separate nonadmin actor must have id1; no arbitrary integer reference sampling'}),
        'paperless.custom_field':dict(component='CustomFieldRequest',producer_method='POST',producer_path='/api/custom_fields/',edit_field='name',base={'name':'Ordinary custom field','data_type':'string','extra_data':{}},excluded={},references={},fixture_constraints={'extra_data':'Ordinary empty metadata object; no nested-value mutations. Schema explicitly permits null and absence.'}),
        'grocy.task_category':dict(component='TaskCategory',producer_method='POST',producer_path='/api/objects/task_categories',edit_field='description',base={'name':'Ordinary category','description':'Ordinary description'},excluded={'id':'Generated identity','row_created_timestamp':'Generated creation metadata'},references={},fixture_constraints={'schema_binding':'Runtime exposed-entity enum permits task_categories; named TaskCategory component supplies shape despite incomplete generic oneOf list. This is documented mapping inference.'}),
        'vikunja.saved_filter':dict(component='SavedFilter',producer_method='POST',producer_path='/api/v2/filters',edit_field='description',base={'title':'Ordinary saved filter','description':'<p>Ordinary description</p>','filters':{},'is_favorite':False},excluded={'filters':'Nested query/lifecycle scope unsupported for mutations; ordinary empty query is fixed'},references={},fixture_constraints={'filters':'Must qualify empty query before any scientific case; API states filter queries are validated'}),
        'gitea.repository_settings':dict(component='CreateRepoOption',producer_method='POST',producer_path='/api/v1/user/repos',edit_field='description',base={'name':'study-repo','description':'Ordinary description','private':True,'auto_init':False,'template':False,'object_format_name':'sha1','trust_model':'default'},excluded={'gitignores':'Template catalog reference not resolved','license':'Template catalog reference not resolved','readme':'Template catalog reference not resolved','issue_labels':'Label-set catalog reference not resolved'},references={},fixture_constraints={'name':'Resolve created repository identity from POST result, including renamed synthetic names. All instances isolated on localhost.'})}
    workflows=[];all_selected=[];generated_all=[];unselected_all=[]
    for wf in selection['workflows']:
        wid=wf['id'];app=wf['application'];doc=documents[app]
        if wid=='grocy.shopping_list':
            assert 'shopping_lists' in doc['components']['schemas']['ExposedEntity_NotIncludingNotEditable']['enum'];assert 'ShoppingList' not in doc['components']['schemas'];workflows.append(dict(id=wid,status='schema_scope_excluded',reason='Runtime permits shopping_lists but supplies no ShoppingList object schema. No field types inferred from frontend or database.'));continue
        spec=definitions[wid];schema=doc.get('definitions',doc.get('components',{}).get('schemas',{}))[spec['component']];props=schema['properties'];required=set(schema.get('required',[]));generated=[];unsupported=dict(spec['excluded']);seen=set();base=spec['base'];fields={}
        assert spec['edit_field'] in props
        for field,raw in sorted(props.items()):
            s=resolve(raw,doc);fields[field]=s
            if s.get('readOnly'):unsupported[field]='API read-only field';continue
            if field==spec['edit_field']:unsupported[field]='Unrelated continuation edit';continue
            if field in unsupported:continue
            alternatives=[]
            if field not in required and field in base:alternatives.append(('omitted',None))
            if s.get('nullable') or s.get('type')=='null' or isinstance(s.get('type'),list) and 'null' in s['type']:alternatives.append(('null',None))
            if field in spec['references']:alternatives += [('reference-'+str(i),value) for i,value in enumerate(spec['references'][field])]
            elif 'enum' in s:alternatives += [('enum-'+str(i),v) for i,v in enumerate(s['enum'])]
            elif s.get('type')=='boolean':alternatives += [('false',False),('true',True)]
            elif s.get('type')=='string':
                if s.get('format') or s.get('pattern'):unsupported[field]='Formatted/patterned scalar lacks predeclared valid synthetic generator';continue
                minimum=s.get('minLength',0);maximum=s.get('maxLength',1000000)
                for label,value in [('empty',''),('short','x'),('ordinary','Study value')]:
                    if minimum<=len(value)<=maximum:alternatives.append((label,value))
            elif s.get('type')=='integer':
                for label,value in [('one',1),('two',2)]:
                    if s.get('minimum',float('-inf'))<=value<=s.get('maximum',float('inf')):alternatives.append((label,value))
            elif not alternatives:unsupported[field]='Unsupported nested or unspecified type'
            if 'default' in s:alternatives.append(('default',s['default']))
            for label,value in alternatives:
                payload=dict(base)
                if label=='omitted':payload.pop(field,None)
                else:payload[field]=value
                key=json.dumps(payload,sort_keys=True,separators=(',',':'))
                if payload==base or key in seen:continue
                seen.add(key);generated.append(dict(id=wid+':'+field+':'+label,workflow=wid,field=field,mutation=label,producer_payload=payload,cohort='schema_sample'))
        groups={f:sorted([c for c in generated if c['field']==f],key=lambda c:hashlib.sha256((seed+':'+c['id']).encode()).hexdigest()) for f in sorted({c['field'] for c in generated})};chosen=[]
        while any(groups.values()) and len(chosen)<12:
            for f in groups:
                if groups[f] and len(chosen)<12:chosen.append(groups[f].pop(0))
        selected_ids={c['id'] for c in chosen};unselected=[c for c in generated if c['id'] not in selected_ids];generated_all+=generated;all_selected+=chosen;unselected_all+=unselected
        workflows.append(dict(id=wid,status='api_input_frozen_native_eligibility_pending',application=app,component=spec['component'],producer_method=spec['producer_method'],producer_path=spec['producer_path'],ordinary_payload=base,edit_field=spec['edit_field'],edit_value='Edited ordinary description' if spec['edit_field']=='description' else 'Edited ordinary name',api_fields=fields,api_required=sorted(required),unsupported_fields=unsupported,fixture_constraints=spec['fixture_constraints'],generated_count=len(generated),selected_count=len(chosen)))
    return dict(kind='independent_api_input_inventory_v1',seed=seed,selection_sha256=sha(ROOT/'manifests/independent-input-selection-v1.json'),generator_sha256=sha(__file__),source_sha256=sources,workflows=workflows,generated=generated_all,selected=all_selected,unselected=unselected_all,ordinary_controls=[dict(id=w['id']+':valid:'+str(i),workflow=w['id'],cohort='valid_control') for w in workflows if w['status'].startswith('api_input_frozen') for i in range(1,5)],scientific_execution_authorized=False,new_frontend_constraints_inspected=False,interpretation='Frozen before new native-workflow validation inspection. Schema-compatible syntax is not business-validity or server-acceptance assurance. Backend serializers were read for Paperless; schema sampling does not omit enum values known to require extra business data. Fields and exclusions are preserved, including one schema-scope exclusion. Apps and shared infrastructure were previously exposed; this is not an untouched-app holdout.')
if __name__=='__main__':
    p=ROOT/'manifests/independent-api-input-inventory-v1.json';assert not p.exists();v=build();p.write_text(json.dumps(v,indent=2)+'\n');print({k:len(v[k]) for k in ['generated','selected','unselected','ordinary_controls']});print([(w['id'],w['status'],w.get('selected_count')) for w in v['workflows']])
