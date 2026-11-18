#!/usr/bin/env python3
"""Resolve historical reservation labels against later closed-study evidence."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'manifests/reserved-frame-current-status-v2.json'


def build():
    inputs = ['manifests/project-family-partition-v1.json',
              'manifests/reserved-frame-status-closed-v1.json',
              'manifests/reserved-continuation-source-collection-v1.json',
              'manifests/infrastructure-extension-closure-v1.json']
    data = [json.loads((ROOT/p).read_text()) for p in inputs]
    partition, closed, collection, extension = data
    reserved = {r['full_name'].lower():r for r in partition['rows'] if r['partition']=='evaluation_reserved'}
    dispositions = {r['repository'].lower():r for r in closed['rows']}
    if set(reserved)!=set(dispositions) or len(reserved)!=9 or not closed['closed']:
        raise ValueError('Historical reservation/closure coverage mismatch')
    if closed['scientific_cases']!=0 or extension['scientific_cases']!=0 or extension['qualified_workflows']!=0:
        raise ValueError('Closure evidence changed; reassess rather than overwrite conclusions')
    for row in closed['rows']:
        if hashlib.sha256((ROOT/row['evidence']).read_bytes()).hexdigest()!=row['evidence_sha256']:
            raise ValueError('Disposition evidence changed: '+row['evidence'])
    for row in extension['runs']:
        if hashlib.sha256((ROOT/row['manifest']).read_bytes()).hexdigest()!=row['manifest_sha256']:
            raise ValueError('Extension evidence changed: '+row['manifest'])
    rows = []
    for name, old in sorted(reserved.items(),key=lambda pair:pair[1]['rank']):
        exposures = [r for r in collection['rows'] if r['repository'].lower()==name and r.get('status')=='retrieved']
        implementation = [r['path'] for r in exposures if r['path'].endswith(('.ts','.html'))]
        rows.append({'repository':old['full_name'],'revision':old['commit'],'family':old['group_id'],
                     'historical_partition':old['partition'],'current_status':'closed_original_frame',
                     'disposition':dispositions[name]['status'],
                     'retrieved_files_in_initial_source_schedule':len(exposures),
                     'component_or_template_files_in_initial_schedule':len(implementation),
                     'untouched_evaluation_reservation_available':False})
    return {'kind':'reconciled_historical_reservation_status','input_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in inputs},
            'rows':rows,'projects':len(rows),'conservative_families':len({r['family'] for r in rows}),
            'untouched_reserved_projects_available':0,'scientific_cases_in_closed_frame_and_extension':0,
            'new_source_reads':0,'new_application_executions':0,
            'scope':'Initial collection counts are partial exposure evidence; dependency and runtime exposure is additional. Historical partition remains immutable.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify',action='store_true');a=p.parse_args();d=build()
    if a.verify:
        if json.loads(OUT.read_text())!=d:raise ValueError('Saved reconciliation differs')
        print('Nine historical reservations reconciled to closed status; zero untouched evaluation slots.')
    else:
        OUT.write_text(json.dumps(d,indent=2)+'\n');print('Current reservation status written.')
