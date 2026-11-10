#!/usr/bin/env python3
"""Evidence-bound descriptive summary; no population or independent-case inference."""
import hashlib,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
APPS=['linkding','paperless','grocy','memos','vikunja','gitea']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
    source_hashes={};apps={};initial_totals=Counter();follow_totals=Counter()
    for app in APPS:
        p=ROOT/'manifests'/f'{app}-initial-results-v1.json';data=json.loads(p.read_text());source_hashes[str(p.relative_to(ROOT))]=sha(p);rows=data['records'];counts={'boundary':Counter(),'valid_control':Counter()}
        for row in rows.values():
            cohort=row['unit']['cohort'] if app=='gitea' else row['cohort'];category=row['category'] if app=='gitea' else row['classification'];category={'channel_or_preservation_difference':'channel_difference'}.get(category,category);counts[cohort][category]+=1
        assert dict(counts)==data['counts'] if app!='gitea' else sum(sum(x.values()) for x in counts.values())==len(rows)
        row=dict(initial_run=data['run_identity'],initial_pairs=len(rows),initial_counts={k:dict(v) for k,v in counts.items()},boundary_variants=sum(counts['boundary'].values()),valid_controls=sum(counts['valid_control'].values()),followup_pairs=0,qualified_boundary_repeats=0,unqualified_boundary_repeats=0,baseline_native_only_signals=0)
        if app=='gitea':
            assert not data['missing_units'];row['baseline_native_only_signals']=data['native_only_signals'];row['generated_boundary_workflows']=2;row['ordinary_workflows']=3
        elif app=='linkding':
            assert all(r['classification'] in ['both_clean','producer_rejected'] for r in rows.values());row['baseline_native_only_signals']=0
        else:row['baseline_native_only_signals']=sum(r.get('baseline_overlap')=='native_only' for r in rows.values())
        for k,v in counts['boundary'].items():initial_totals[k]+=v
        follow=ROOT/'manifests'/f'{app}-followup-results-v1.json'
        if app in ['grocy','memos','vikunja','gitea']:
            later=json.loads(follow.read_text());source_hashes[str(follow.relative_to(ROOT))]=sha(follow);comp=later['comparisons'];row.update(followup_run=later['run_identity'],followup_pairs=len(later['records']),qualified_boundary_repeats=later['qualified_boundary_repeat_pairs'],unqualified_boundary_repeats=len(comp)-later['qualified_boundary_repeat_pairs'],qualified_repeats_matching_initial=sum(c.get('matches_initial_outcomes',c.get('matches_initial_channels',False)) and c['matches_initial_overlap'] for c in comp));follow_totals['pairs']+=row['followup_pairs'];follow_totals['qualified_boundary_repeats']+=row['qualified_boundary_repeats'];follow_totals['unqualified_boundary_repeats']+=row['unqualified_boundary_repeats']
        else:assert data['repeat_case_ids']==[]
        apps[app]=row
    return dict(kind='production_extension_descriptive_summary_v1',source_sha256=source_hashes,applications=apps,initial_boundary_counts=dict(initial_totals),initial_pairs=sum(a['initial_pairs'] for a in apps.values()),initial_valid_controls=sum(a['valid_controls'] for a in apps.values()),followup_totals=dict(follow_totals),finite_pairs=sum(a['initial_pairs']+a['followup_pairs'] for a in apps.values()),baseline_native_only_signals=sum(a['baseline_native_only_signals'] for a in apps.values()),natural_defects_confirmed=0,cohort_exclusions=['Original exploratory package','Ordinary adapter qualification/probes and failures','Grocy nine-pair post-exposure energy experiment'],interpretation=['These are six purposively chosen applications and correlated variants, not a population prevalence sample.','Boundary candidates were derived from native constraints; shared-baseline coverage is partly a consequence of this construction and is not an unbiased measure of all possible interface failures.','Successful API writes and semantic edits can coexist with blocked or non-preserving native continuations; that observation is distinct from incremental detection beyond shared constraints.','A shared consistency alert with a clean native continuation is not automatically a defect or an operational false positive.','No actual LLM agent or MCP intervention was tested. No novel defect or Q1 acceptance follows from case counts.'])
if __name__=='__main__':
    p=ROOT/'manifests/production-extension-summary-v1.json';assert not p.exists();v=build();p.write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({k:v[k] for k in ['initial_boundary_counts','initial_pairs','initial_valid_controls','followup_totals','finite_pairs','baseline_native_only_signals']},indent=2))
