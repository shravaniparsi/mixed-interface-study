#!/usr/bin/env python3
"""Verify the pinned hosted interruption qualification and fresh-control evidence."""
import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
from validate_petclinic_integrity import validate_run
artifact=Path(sys.argv[1])
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=read(artifact/'petclinic-interruption-report.json')
plan=read(artifact/'petclinic-interruption-plan.json')
assert report['source_commit']=='51e03e509bd44cbfd498dafdca11141a359075b1'
assert report['status']=='qualified_at_declared_checkpoint' and not report['rescue_actions']
assert report['source_sha256']==plan['source_sha256']
for path,h in plan['source_sha256'].items():assert sha(root/path)==h,path
assert report['interruption']['signal']=='SIGTERM'
assert report['interruption']['wrapper_returncode']==143
assert report['interruption']['wrapper_exit_s']<=18
assert any('chrome' in p['command'].lower() for p in report['checkpoint']['observed_descendants'])
assert any(' -jar ' in p['command'] for p in report['checkpoint']['observed_descendants'])
for stage in ('interrupted','fresh'):
 c=report[stage+'_cleanup']
 assert c['observed_processes'] and not c['live_survivors'] and not any(c['ports_open'].values())
 assert set(c['wrapper_cleanup'])=={'runner','frontend'}
 assert all(r['exit_confirmed'] and not r['errors'] for r in c['wrapper_cleanup'].values())
 assert c['wrapper_cleanup']==read(artifact/('petclinic-'+stage)/'petclinic-owned-process-cleanup.json')
fresh=artifact/'petclinic-fresh'
validated=validate_run(fresh/'petclinic-integrity-controls',fresh)
assert validated==report['fresh_control_validation']==read(fresh/'petclinic-integrity-validation.json')
print(json.dumps({'status':'verified','source_commit':report['source_commit'],'wrapper_exit_s':report['interruption']['wrapper_exit_s'],'elapsed_s':report['elapsed_s'],'observed_processes':{s:len(report[s+'_cleanup']['observed_processes']) for s in ('interrupted','fresh')},'fresh_branches':validated['branches'],'fresh_guards':sum(c['guards'] for c in validated['cases']),'native_requests':sum(c['native_requests'] for c in validated['cases']),'rescue_actions':len(report['rescue_actions']),'report_sha256':sha(artifact/'petclinic-interruption-report.json')},indent=2))
