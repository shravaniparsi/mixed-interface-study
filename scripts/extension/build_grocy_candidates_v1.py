#!/usr/bin/env python3
"""Finite source-based Grocy inventory; exploratory energy observation excluded explicitly."""
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];SEED='production-extension-v1:grocy:20261110'
def build():
    controls=json.loads((ROOT/'manifests/grocy-extension-controls-v3.json').read_text());pool=[];valid=[];flows=copy.deepcopy(controls['workflows'])
    for w in flows:
        # API nullability comes from the pinned database schema, not UI required flags.
        if w['id']=='product':
            for ref in w['references']:
                if ref['field'] in ['qu_id_consume','qu_id_price']:ref['nullable']=True
        def add(field,variant,value=None,omit=False,family='required_name',prediction='violation'):
            payload=dict(w['payload'])
            if omit:payload.pop(field,None)
            else:payload[field]=value
            pool.append({'id':w['id']+'-'+field+'-'+variant,'workflow':w['id'],'field':field,'variant':variant,'family':family,'payload':payload,'native_constraint_prediction':prediction})
        if w['id'] in ['location','task']:
            for variant,value,omit,pred in [('omitted',None,True,'violation'),('null',None,False,'violation'),('empty','',False,'violation'),('whitespace','   ',False,'compatible')]:add('name',variant,value,omit,prediction=pred)
        if w['id']=='product':
            for variant,value,omit,pred in [('omitted',None,True,'compatible_after_default'),('null',None,False,'violation'),('below',-1,False,'violation'),('at',0,False,'compatible'),('above',1,False,'compatible')]:add('min_stock_amount',variant,value,omit,'numeric_minimum',pred)
        refs=['location_id','qu_id_purchase','qu_id_stock','qu_id_consume','qu_id_price'] if w['id']=='product' else ['category_id','assigned_to_user_id'] if w['id']=='task' else []
        for field in refs:
            for variant,value,omit in [('omitted',None,True),('null',None,False),('zero',0,False),('negative',-1,False),('missing-positive',2147483647,False)]:
                pred='compatible_absence' if w['id']=='task' and variant in ['omitted','null'] else 'violation'
                add(field,variant,value,omit,'reference',pred)
        for i,name in enumerate(['Ordinary '+w['id'],'Second '+w['id'],'Valid '+w['id']+' 3','Valid '+w['id']+' 4']):
            payload={**w['payload'],'name':name}
            if w['id']=='product':payload['min_stock_amount']=i
            valid.append({'id':w['id']+'-valid-'+str(i+1),'workflow':w['id'],'payload':payload,'native_constraint_prediction':'compatible'})
    selected=[];remainder=[]
    for w in flows:
        families={}
        for c in pool:
            if c['workflow']==w['id']:families.setdefault(c['family'],[]).append(c)
        for cs in families.values():cs.sort(key=lambda c:hashlib.sha256((SEED+':'+c['id']).encode()).hexdigest())
        ordered=[]
        while any(families.values()):
            for key in sorted(families):
                if families[key]:ordered.append(families[key].pop(0))
        selected.extend(ordered[:12]);remainder.extend(ordered[12:])
    return {'kind':'grocy_candidate_inventory_v1','source_commit':controls['source_commit'],'seed':SEED,'execution_authorized':False,'workflows':flows,'selected_boundary_cases':selected,'unselected_boundary_cases':remainder,'valid_controls':valid,'counts':{'generated_boundary':len(pool),'selected_boundary':len(selected),'unselected_boundary':len(remainder),'valid_controls':len(valid)},'provenance':{'required_names':'views/locationform.blade.php and views/taskform.blade.php required attributes; native ValidateForm in public/js/grocy.js','product_numeric_minimum':'views/productform.blade.php min_stock_amount -> components.numberpicker, minimum 0','product_reference_selectors':'views/productform.blade.php five required selectors; negative DOM probes independently qualified','task_reference_selectors':'views/taskform.blade.php category selector and components/userpicker.blade.php; optional blank option, actual reference inventories qualified','api_nullability':'migrations/0207.sql required location/purchase/stock IDs; 0210.sql and 0219.sql nullable consume/price IDs. UI required is not relabeled as an API NOT NULL constraint.','api_dispatch':'controllers/Api/GenericEntityApiController.php; parsed body to database row save/update','full_record_domain':'v3 ordinary control registry; complete returned mutable-field inventory with within-branch preservation of id, row_created_timestamp and userfields'},'baseline_requirements':['Record immediate status and declared business-type/minimum signals with explicit schema ambiguity handling.','Compare full-record API same-edit/readback and all preserved fields.','Check non-null reference existence for both channels; nullable API references remain allowed according to database contract. Missing referenced objects are a shared API signal.','Record native loaded representation, actual validation and complete persisted readback. A blank optional selector representing null is not itself a load failure.','Never count shared type, minimum or reference signals as native-only.'],'exclusions':{'product.calories':'Already exposed by post-hoc ordinary-record audit. Explicit zero in this prospective cohort; separate exploratory replication/counterfactual cohort required.','product.name':'Unrelated rename continuation, not varied in producer.','description':'Unrelated continuation for location/task; fixed preserved text for product.','additional_product_numeric_and_flag_fields':'Outside the preselected stock-minimum/reference mutation scope. All are retained in full-record preservation checks; no exhaustive form-constraint claim.','dates_and_cross_resource_tree_workflows':'Fixed ordinary fixture values; no date-format or tree mutation inference.'},'qualification_gate':'v3 full-record controls and exact finite-executor valid controls must pass before boundary execution; synthetic probes already separate from natural findings.'}
if __name__=='__main__':
    result=build();p=ROOT/'manifests/grocy-candidate-inventory-v1.json';s=json.dumps(result,indent=2)+'\n'
    if p.exists() and p.read_text()!=s:raise SystemExit('Inventory differs; use a versioned amendment')
    p.write_text(s);print(json.dumps(result['counts']))
