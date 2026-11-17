#!/usr/bin/env python3
"""Fixed filename-only admission schedule; does not read source contents."""
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def build(tree_root):
 partition=json.loads((ROOT/'manifests/project-family-partition-v1.json').read_text());rows=[]
 for project in partition['rows']:
  if project['partition']!='evaluation_reserved':continue
  p=tree_root/(str(project['rank'])+'.json');raw=p.read_bytes();tree=json.loads(raw);assert not tree['truncated']
  blobs={b['path']:b for b in tree['tree'] if b['type']=='blob'}
  candidates=sorted(p for p in blobs if p.endswith('.component.ts') and not set(p.split('/'))&{'test','tests','node_modules','dist','target'} and '.spec.' not in p)
  selected=candidates[:32];paths=[]
  for p in selected:
   paths.append(p);html=p[:-3]+'.html'
   if html in blobs:paths.append(html)
  for stem in ['readme','license']:
   matches=sorted(p for p in blobs if '/' not in p and p.lower().split('.')[0]==stem)
   if matches:paths.append(matches[0])
  rows.append({**project,'tree_sha256':hashlib.sha256(raw).hexdigest(),'candidate_count':len(candidates),'candidate_prefix':selected,'excluded_tail':candidates[32:],'files':[{'path':p,'blob_sha':blobs[p]['sha'],'bytes':blobs[p].get('size'),'eligible_bytes':blobs[p].get('size',262145)<=262144} for p in sorted(set(paths))]})
 assert len(rows)==9 and len({r['group_id'] for r in rows})==8
 return {'kind':'reserved_continuation_source_admission_schedule','source_contents_read':False,'independent_evaluation_cases':0,'rows':rows}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--tree-root',type=Path,required=True);p.add_argument('--verify',action='store_true');a=p.parse_args();d=build(a.tree_root);out=ROOT/'manifests/reserved-continuation-source-schedule-v1.json'
 if a.verify:assert json.loads(out.read_text())==d
 else:out.write_text(json.dumps(d,indent=2)+'\n')
 print(json.dumps([{'repository':r['full_name'],'candidates':r['candidate_count'],'selected_components':len(r['candidate_prefix']),'scheduled_files':len(r['files'])} for r in d['rows']],indent=2))
