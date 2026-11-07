#!/usr/bin/env python3
"""Rebuild or verify retrospective attributed engineering-control comparisons."""
import argparse,hashlib,json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.attribution import normalize_case,compare_pair,counts
from summarize_petclinic_integrity_components import summarize_compact
from summarize_petclinic_oracle_components import same,digest,INITIAL_STATE_SHA256

DEST=ROOT/'results/unified-controls-20261107'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_bytes())
def required(value,label):
    if not value:raise ValueError(label)
def command(raw,name,stage=None):
    guards=raw['integrity']['guards']
    matches=[g for g in guards if g['name']==name and (stage is None or g.get('stage')==stage)]
    if len(matches)!=1:return None
    return matches[0]
def rw_post(raw):
    return {'business_fields':raw['accepted_producer'],'reference':raw['resource_reference']} if 'accepted_producer' in raw else raw.get('prefix_state')


def build():
    manifest=load(ROOT/'manifests/unified-control-inputs-v1.json')
    for name,pin in manifest['input_sha256'].items():
        path=ROOT/name
        required(path.resolve().is_relative_to(ROOT.resolve()),'Input path escapes repository')
        required(sha(path)==pin,'Changed frozen input: '+name)
    mapping=load(ROOT/'manifests/component-attribution-v1.json')['rules']
    inventory=load(ROOT/'manifests/paired-candidate-inventory-v1.json')
    reports=manifest['reports'];raws={};entries={};resets={};normalized={};source_reports={};members={}
    for source in ('realworld_generated','realworld_legacy'):
        report=load(ROOT/reports[source]['components']);summary=load(ROOT/reports[source]['summary']);source_reports[source]=report
        required(report['status']=='complete_observations','Incomplete RealWorld source report')
        required(report['input_summary_sha256']==sha(ROOT/reports[source]['summary']),'RealWorld source summary mismatch')
        required(report['case_count']==len(report['cases']),'RealWorld case count mismatch')
        for e in summary['validation' if source.endswith('generated') else 'branches']:entries[source+'::'+e['case_id']]=e
        for c in report['cases']:
            key=source+'::'+c['case_id'];ref=manifest['realworld_raw'][key];raw=load(ROOT/ref['observation']);raws[key]=raw
            if 'reset' in ref:resets[key]=load(ROOT/ref['reset'])
            required(key not in normalized,'Duplicate RealWorld case')
            normalized[key]=normalize_case(c,source,mapping[source],record_id=key)
    pc=summarize_compact(ROOT/reports['petclinic_integrity']['directory']);source_reports['petclinic_integrity']=pc
    required(pc['status']=='complete_observations','Incomplete PetClinic component extraction')
    for c in pc['cases']:
        key='petclinic_integrity::'+c['case_id'];normalized[key]=normalize_case(c,'petclinic_integrity',mapping['petclinic_integrity'],record_id=key)
        raws[key]=load(ROOT/reports['petclinic_integrity']['directory']/'observations'/(c['case_id']+'.json'))
    quartz=load(ROOT/reports['quartz_controls']['summary']);qbycase={}
    required(not quartz['campaign_issues'] and quartz['pair_count']==2,'Unqualified Quartz control campaign')
    for p in quartz['pairs']:
        required(p['valid'] is True and not p['issues'] and p['comparisons']['clean_ordinary_controls'],'Unqualified Quartz pair')
        for b in p['branches']:qbycase[b['case_id']]=(p,b)
    for pair in inventory['pairs']:
        catalog=pair['catalog'];found={}
        if catalog=='realworld_development':
            found={o:'realworld_legacy::'+pair['candidate_id']+'-'+o+'-r1' for o in ('api','ui')}
        elif catalog=='petclinic_development':
            found={o:'petclinic_integrity::'+pair['candidate_id']+'-'+('api_semantic' if o=='api' else 'fresh_ui') for o in ('api','ui')}
        elif catalog=='realworld_generated_integration':
            found={o:'realworld_generated::'+pair['case_ids'][o] for o in ('api','ui')}
        elif catalog=='quartz_generated_v2' and all(cid in qbycase for cid in pair['case_ids'].values()):
            for o,cid in pair['case_ids'].items():
                p,b=qbycase[cid];key='quartz_controls::'+cid
                c={'case_id':cid,'route':pair['producer_interface']+'-'+o,'accepted_prefix':True,'execution_evidence_complete':True,'components':b['components']}
                normalized[key]=normalize_case(c,'quartz_controls',mapping['quartz_controls'],record_id=key);found[o]=key
        if found and all(k in normalized for k in found.values()):members[pair['pair_id']]=(pair,found)
        elif found and any(k in normalized for k in found.values()):raise ValueError('Only one selected branch of declared pair: '+pair['pair_id'])
    comparisons=[];used=set()
    for pair_id,(declared,keys) in members.items():
        a,u=(normalized[keys[o]] for o in ('api','ui'));used.update(keys.values());accepted=a['accepted_prefix'] and u['accepted_prefix']
        catalog=declared['catalog'];producer=declared['producer_interface']
        gates={'same_declared_prefix':a['route'].split('-')[0]==u['route'].split('-')[0]==producer}
        if catalog=='quartz_generated_v2':
            pa=qbycase[declared['case_ids']['api']][0];pu=qbycase[declared['case_ids']['ui']][0];c=pa['comparisons']
            required(pa['pair_id']==pu['pair_id'],'Quartz declared/campaign pair mismatch')
            gates.update(same_initial_state=c['same_full_initial_state'],same_pre_candidate_state=c['same_full_initial_state'],
              same_observed_prefix_command=c['same_registered_prefix'] and c['actual_producer_input_matches_registered'],
              same_prefix_outcome=c['ordinary_response_statuses'],independent_reset_evidence=c['independent_jvm_pid_evidence'] and c['independent_evidence_directories'],
              same_accepted_prefix_state=c['same_accepted_postprefix_business_state'],same_intended_consumer_command=c['same_intended_bound_consumer_payload'])
        else:
            ar,ur=(raws[keys[o]] for o in ('api','ui'))
            pre=[r['integrity']['before'] for r in (ar,ur)]
            gates['same_pre_candidate_state']=all(s['readable'] is True for s in pre) and same(pre[0]['data'],pre[1]['data'])
            if catalog=='petclinic_development':
                initial=[next(e['response'] for e in r['trace'] if e.get('phase')=='reset_verification') for r in (ar,ur)]
                gates['same_initial_state']=same(*initial) and all(digest(v)==INITIAL_STATE_SHA256 for v in initial)
                gates['independent_reset_evidence']=ar['backend_pid']!=ur['backend_pid'] and all(r['backend_cleanup']['confirmed'] for r in (ar,ur))
                prefix=[command(r,'candidate_prefix_command') for r in (ar,ur)];consumer=[command(r,'continuation_edit_command') for r in (ar,ur)]
                post=[r['post_prefix_graph'] for r in (ar,ur)]
                statuses=[r['prefix_status'] for r in (ar,ur)]
            else:
                gates['same_initial_state']=gates['same_pre_candidate_state']
                if catalog=='realworld_development':
                    summary=load(ROOT/reports['realworld_legacy']['summary']);e=[entries[keys[o]] for o in ('api','ui')]
                    gates['independent_reset_evidence']=e[0]['evidence']!=e[1]['evidence'] and all(x['reset_sha256']==summary['fixture_sha256'] and x['execution_status']=='completed' for x in e)
                else:
                    r=[resets[keys[o]] for o in ('api','ui')]
                    gates['independent_reset_evidence']=keys['api']!=keys['ui'] and all(x['independent_offline_reset'] is True for x in r) and r[0]['sha256']==r[1]['sha256']
                prefix=[command(r,'submitted_command','prefix') for r in (ar,ur)];consumer=[command(r,'submitted_command','continuation') for r in (ar,ur)]
                post=[rw_post(r) for r in (ar,ur)]
                statuses=[r.get('prefix_status',r.get('observations',{}).get('prefix_status')) for r in (ar,ur)]
            gates['same_observed_prefix_command']=all(p is not None and p['passed'] is True for p in prefix) and same(prefix[0]['observed'],prefix[1]['observed'])
            gates['same_prefix_outcome']=statuses[0]==statuses[1] and a['accepted_prefix']==u['accepted_prefix']
            gates['same_accepted_prefix_state']=(all(p is not None for p in post) and same(*post)) if accepted else None
            gates['same_intended_consumer_command']=(all(c is not None and c['passed'] is True for c in consumer) and same(consumer[0]['expected'],consumer[1]['expected'])) if accepted else None
        item=compare_pair(a,u,gates,pair_id=pair_id,catalog=catalog,workflow=declared['workflow_id'])
        item['registered_semantics_sha256']=declared['registered_semantics_sha256'];item['prior_exposure']=declared['prior_exposure']
        item['reset_evidence_scope']='Source-qualified reset records and state checks; RealWorld legacy reset hashes are recorded assertions, not independent process-cleanup qualification.'
        comparisons.append(item)
    singleton_keys=set(normalized)-used
    expected_singletons={'realworld_legacy::'+p['candidate_id']+'-ui-r1' for p in inventory['unpaired_controls'] if p['catalog']=='realworld_development'}
    required(singleton_keys==expected_singletons,'Unaccounted or missing singleton controls')
    total=counts(comparisons,normalized,singleton_keys)
    source_files=['scripts/build_control_analysis.py','scripts/summarize_petclinic_integrity_components.py','scripts/summarize_petclinic_oracle_components.py','scripts/validate_petclinic_integrity.py','src/mixed_interface/attribution.py','manifests/component-attribution-v1.json','manifests/unified-control-inputs-v1.json']
    result={'kind':'retrospective_unified_control_analysis','schema_version':1,'scope':'Previously examined engineering controls only; source catalogs overlap.',
      'source_sha256':{name:sha(ROOT/name) for name in source_files},'input_file_count':len(manifest['input_sha256']),
      'counts':total,'by_catalog':{c:counts([p for p in comparisons if p['catalog']==c],[],[]) for c in sorted({p['catalog'] for p in comparisons})},
      'pairs':comparisons,'singletons':[{'record_id':k,'reason':'No declared matching API continuation control'} for k in sorted(singleton_keys)],
      'records':[normalized[k] for k in sorted(normalized)],'primary_freeze_complete':False,'application_executions_added':0,
      'adjudicated_root_causes':None,'limitations':['Check-signal overlap on ordinary controls is not defect yield, prevalence, diagnostic advantage or selector effectiveness.',
        'Rejected prefixes and unpaired controls are outside the continuation-contrast denominator.',
        'RealWorld business-state comparisons use existing recorded projections; no new timestamp or identifier normalization is introduced.',
        'Primary scheduling, interruption/browser cleanup, cost boundaries and the final evaluation freeze remain open.']}
    # Catalog denominators include their actual branches and singleton controls.
    source_catalog={'realworld_legacy':'realworld_development','realworld_generated':'realworld_generated_integration','petclinic_integrity':'petclinic_development','quartz_controls':'quartz_generated_v2'}
    for catalog in result['by_catalog']:
        rs=[r for r in normalized.values() if source_catalog[r['source']]==catalog]
        ss=[k for k in singleton_keys if source_catalog[normalized[k]['source']]==catalog]
        result['by_catalog'][catalog]=counts([p for p in comparisons if p['catalog']==catalog],rs,ss)
    return {'analysis.json':result,'petclinic-components.json':pc}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    outputs=build()
    if args.verify:
        for name,value in outputs.items():required(load(DEST/name)==value,'Derived report differs: '+name)
        print('Frozen control inputs, component attribution and paired accounting reproduce exactly.')
    else:
        DEST.mkdir(parents=True,exist_ok=True)
        for name,value in outputs.items():(DEST/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
        print(json.dumps(outputs['analysis.json']['counts'],indent=2))
if __name__=='__main__':main()
