"""Deterministic frozen text-input construction; no network/application access."""
import copy,json,pathlib
INPUT=pathlib.Path(__file__).with_name('input.json')
def build(project_id):
    assert type(project_id) is int and project_id>0
    x=json.loads(INPUT.read_text());base={**x['ordinary'],'project':project_id};out=[]
    for row in x['scientific_producers']:
        body=copy.deepcopy(base)
        if row['mutation']!='none':
            field=row['target'][1:]
            assert field in ('description','name')
            if row['mutation']=='omit':del body[field]
            elif row['mutation']=='null':body[field]=None
            else:raise ValueError(row['mutation'])
        out.append({**row,'body':body})
    return out
if __name__=='__main__':
    # Synthetic binding for offline structural verification, never an application ID.
    cases=build(37);assert len(cases)==5
    ordinary=cases[0]['body']
    for case in cases[1:]:
        k=case['target'][1:];a=copy.deepcopy(case['body']);b=copy.deepcopy(ordinary)
        a.pop(k,None);b.pop(k);assert a==b
        assert (k not in case['body']) if case['mutation']=='omit' else (k in case['body'] and case['body'][k] is None)
    assert cases[0]['body']==ordinary
    print(json.dumps({'status':'verified','producers':5,'target_text_fields':2,'application_executed':False}))
