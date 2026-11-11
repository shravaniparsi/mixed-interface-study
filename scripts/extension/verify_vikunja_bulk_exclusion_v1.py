#!/usr/bin/env python3
"""Verify authorization qualification failure separately from scientific results."""
import argparse, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
 raw={};counts={};controls=[]
 for version,run in [('v1','43086390320'),('v2','43086867599')]:
  archive=ROOT/('results/vikunja-bulk-%s-ci-%s'%(version,run))
  regpath=ROOT/('manifests/vikunja-bulk-calibration-%s.json'%version);reg=read(regpath)
  for name,expected in reg['source_sha256'].items():assert sha(ROOT/name)==expected,name
  reports=sorted(archive.glob('*/report.json'));assert len(reports)==2
  observed=denied=successful=0
  for rp in reports:
   report=read(rp);assert report['run_id']==run;assert report['registry_sha256']==sha(regpath)
   for name,expected in report['files_sha256'].items():assert sha(rp.parent/name)==expected,name
   for name,expected in reg['upstream_git_blobs'][report['version']].items():
    data=(rp.parent/'upstream-source'/name).read_bytes();assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==expected
   paths=sorted((rp.parent/'observations').glob('*.json'))
   if version=='v1':
    assert report['status']=='incomplete' and not paths
    assert 'pattern all:dist: no matching files found' in (rp.parent/'command-03.log').read_text()
   else:
    assert report['status']=='observed' and len(paths)==12
    seen=set()
    for path in paths:
     o=read(path);key=(o['case'],o['channel']);assert key not in seen;seen.add(key);observed+=1
     if o['case']!='single_priority':
      assert not o['operation_success'] and o['before']==o['after']
      if o['channel']=='rest':assert o['response']['http_status']==401
      else:
       assert o['response']['isError'] is True
       assert 'tool not authorized for this token: tasks_bulk_update' in o['response']['content'][0]['text']
      denied+=1
     else:
      assert o['operation_success'];successful+=1
      b,a=o['before']['30'],o['after']['30']
      assert a['tasks'][0]['priority']==3
      for name in ('assignees','reminders','favorites'):assert a[name]==b[name]
      changes=sorted(k for k in b['tasks'][0] if a['tasks'][0][k]!=b['tasks'][0][k])
      assert set(changes)<= {'priority','updated'}
      controls.append({'version':report['version'],'channel':o['channel'],'changed_task_fields':changes})
   for path in rp.parent.rglob('*'):
    if path.is_file():raw[str(path.relative_to(ROOT))]=sha(path)
  counts[run]={'completed_observations':observed,'bulk_authorization_denials':denied,'successful_single_controls':successful}
 assert counts['43086867599']=={'completed_observations':24,'bulk_authorization_denials':20,'successful_single_controls':4}
 return {'kind':'vikunja_bulk_qualification_exclusion_v1','qualification':'failed_bulk_authorization','scientific_bulk_executions':0,'new_confirmed_mechanisms':0,'attempts':counts,'single_controls':controls,'no_further_attempt_in_registered_calibration':True,'raw_sha256':raw}
def main():
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();d=build();out=ROOT/'manifests/vikunja-bulk-exclusion-v1.json'
 if a.verify:assert read(out)==d
 else:out.write_text(json.dumps(d,indent=2)+'\n')
 print(json.dumps({k:v for k,v in d.items() if k not in ('raw_sha256','single_controls')}))
if __name__=='__main__':main()
