"""Reject incomplete schedules and accidental reuse of defect-input schedules."""
import collections,json,pathlib
from source_check import require
ROOT=pathlib.Path(__file__).resolve().parents[2]
def at(value,pointer):
 for part in pointer.split('/')[1:]:value=value[int(part)] if isinstance(value,list) else value[part.replace('~1','/').replace('~0','~')]
 return value
def verify(matrix):
 require(matrix['scope']=='ordinary_controls_only','ordinary_scope')
 require(matrix['scientific_defect_inputs']==0 and matrix['independent_systems_for_evaluation']==0,'no_scientific_cases')
 require([s['id'] for s in matrix['systems']]==['zipline','shlink'],'fixed_systems')
 forbidden={'producers','producer_order','mutations','omitted','null'}
 def scan(value):
  require(value is not None,'no_null_inputs')
  if isinstance(value,dict):
   require(not set(value)&forbidden,'no_defect_schedule')
   for child in value.values():scan(child)
  elif isinstance(value,list):
   for child in value:scan(child)
 scan(matrix)
 summary={}
 for s in matrix['systems']:
  fields={f['pointer']:f for f in s['fields']};require(len(fields)==(4 if s['id']=='zipline' else 2),'all_fields')
  for p,f in fields.items():
   require(at(s['api'],p)==f['ordinary'],'ordinary_matches_api',pointer=p)
   require(f['replacement']!=f['ordinary'],'real_valid_replacement',pointer=p)
   require(f['unrelated_pointer'] in fields and f['unrelated_pointer']!=p,'unrelated_field')
   at(s['native'],p)
  branches=s['branches'];require([b['sequence'] for b in branches]==list(range(1,len(branches)+1)),'ordered_sequences')
  require(len({b['id'] for b in branches})==len(branches),'unique_branch_ids')
  expected=collections.Counter((r,p,arm) for r in range(1,4) for p in fields for arm in ['untouched','noop_repair'])
  actual=collections.Counter((b['repetition'],b['target'],b['arm']) for b in branches)
  require(actual==expected,'complete_three_repetition_matrix')
  first=collections.Counter()
  for i in range(0,len(branches),2):
   a,b=branches[i:i+2];require((a['repetition'],a['target'])==(b['repetition'],b['target']),'adjacent_matched_pair');first[a['arm']]+=1
  require(first['untouched']==first['noop_repair'],'balanced_first_arm')
  for b in branches:
   require(b['fresh_browser_context'] is True and b['restore_persistent_root'] is True,'fresh_isolated_branch')
   require(b['unrelated']==fields[b['target']]['unrelated_pointer'],'fixed_unrelated_field')
  summary[s['id']]=dict(repetitions=3,fields=len(fields),branches=len(branches))
 return summary
if __name__=='__main__':print(json.dumps(verify(json.loads((ROOT/'manifests/fresh-session-ordinary-matrix-v1.json').read_text())),indent=2))
