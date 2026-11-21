import sys,pathlib,json,hashlib,os
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'relaticle-state-v1'))
from sqlite_state import snapshot,canonical
value=snapshot(os.environ['STUDY_DB']);label=sys.argv[1];private=pathlib.Path(os.environ['STUDY_PRIVATE']);public=pathlib.Path(os.environ['STUDY_EVIDENCE']);(private/(label+'.json')).write_bytes(canonical(value))
rows={}
for name,table in value['tables'].items():
 columns=([table['rowid_alias']] if table['rowid_alias'] else [])+[c[1] for c in table['columns'] if c[6]!=1]
 rows[name]=[{k:v['value'] for k,v in zip(columns,row)} for row in table['rows']]
allowed={'notes','custom_field_values','custom_fields','noteables'}
summary={'sha256':hashlib.sha256(canonical(value)).hexdigest(),'schema':value['schema'],'tables':{name:{'rows':table['rows'] if name in allowed else None,'rowid_alias':table['rowid_alias'],'row_count':len(table['rows']),'sha256':hashlib.sha256(canonical(table)).hexdigest(),'columns':table['columns'],'foreign_keys':table['foreign_keys'],'indexes':table['indexes']} for name,table in value['tables'].items()}}
(public/(label+'.json')).write_bytes(canonical(summary));print(json.dumps(rows))
