#!/usr/bin/env python3
"""Exact reported-credit sensitivity, not imputed counterfactual test outcomes."""
from collections import defaultdict,Counter
import argparse
import csv
from fractions import Fraction
import hashlib
import itertools
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def rational(x):return {'numerator':x.numerator,'denominator':x.denominator,'percentage':float(x*100)}
def blob(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()

def build():
    audit_path=ROOT/'manifests/restestbench-released-status-v1.json';audit=json.loads(audit_path.read_text())
    pins=json.loads((ROOT/'results/restestbench-released-status-v1/source-pins.json').read_text())
    credits=Counter()
    for match in audit['matches']:
        assert match['credited_in_evaluation'] and match['present_in_consolidated_csv']
        parts=match['execution_file'].split('/');credits[(parts[2],'/'.join(parts[3:-1]))]+=1
    groups=defaultdict(list);matched=0;selected=0;row_proof=[]
    for number in (1,2,3):
        group=f'results_{number}';path=f'results/runs/{group}/benchmark_results.csv'
        source=ROOT/'results/restestbench-released-status-v1/matching_sources'/path
        assert blob(source.read_bytes())==pins['files'][path]
        for row in csv.DictReader(source.open()):
            if row['tool']!='zero-shot' or row['generation_context']!='valid':continue
            selected+=1;score=Fraction(row['score']);maximum=Fraction(row['max_score'])
            assert score.denominator==maximum.denominator==1 and 0<=score<=maximum
            unsupported=credits.get((group,row['output_folder'].replace('\\','/')),0);matched+=unsupported
            lower=(score-unsupported)/maximum;upper=score/maximum;assert lower>=0
            key=(row['service_name'],row['precise_description'],row['model'])
            groups[key].append((group,lower,upper))
            row_proof.append({'run_group':group,'service':key[0],'precise_description':key[1],'model':key[2],'score':int(score),'max_score':int(maximum),'unsupported_credits':unsupported})
    assert selected==180 and matched==sum(credits.values())==6 and len(groups)==60
    values={};cells=[]
    for key,rows in sorted(groups.items()):
        assert len(rows)==3 and {r[0] for r in rows}=={'results_1','results_2','results_3'}
        lower=sum((r[1] for r in rows),Fraction())/3;upper=sum((r[2] for r in rows),Fraction())/3
        values[key]=(lower,upper)
        cells.append({'service':key[0],'precise_description':key[1],'model':key[2],'lower':rational(lower),'upper':rational(upper),'width_percentage_points':float((upper-lower)*100)})
    pair_counts=Counter();overlap=[];group_counts={}
    for group in sorted({k[:2] for k in values}):
        models=sorted(k[2] for k in values if k[:2]==group);assert len(models)==10
        counts=Counter()
        for left,right in itertools.combinations(models,2):
            lo_a,hi_a=values[group+(left,)];lo_b,hi_b=values[group+(right,)]
            original='tie' if hi_a==hi_b else 'left_higher' if hi_a>hi_b else 'right_higher'
            if lo_a==hi_a==lo_b==hi_b:status='unchanged_point_tie'
            elif lo_a>hi_b or lo_b>hi_a:status='certified_strict_order'
            else:status='overlapping_intervals'
            pair_counts[status]+=1;counts[status]+=1
            if status=='overlapping_intervals':overlap.append({'service':group[0],'precise_description':group[1],'left':left,'right':right,'original_order':original,'left_lower':rational(lo_a),'left_upper':rational(hi_a),'right_lower':rational(lo_b),'right_upper':rational(hi_b)})
        group_counts['/'.join(group)]=dict(counts)
    assert sum(pair_counts.values())==270
    return {'kind':'restestbench_credit_sensitivity_v1','post_hoc':True,'selected_csv_rows':selected,'unsupported_credits':matched,'aggregate_cells':len(cells),'uncertain_cells':sum(c['width_percentage_points']>0 for c in cells),'pair_counts':dict(pair_counts),'group_pair_counts':group_counts,'overlapping_pairs':overlap,'cells':cells,'selected_rows':row_proof,'actual_ranking_reversal_established':False,'paper_conclusion_change_established':False,'denominator_policy':'original fixed mutant denominator','aggregation':'equal-weight mean of three reported repetitions within service and description mode','source_audit_sha256':hashlib.sha256(audit_path.read_bytes()).hexdigest(),'new_model_calls':0,'new_application_executions':0}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args();value=build();output=ROOT/'manifests/restestbench-credit-sensitivity-v1.json'
    if args.verify:assert json.loads(output.read_text())==value
    else:
        assert not output.exists();output.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({k:v for k,v in value.items() if k not in ['cells','selected_rows','overlapping_pairs']},indent=2))
    print(json.dumps(value['overlapping_pairs'],indent=2))
if __name__=='__main__':main()
