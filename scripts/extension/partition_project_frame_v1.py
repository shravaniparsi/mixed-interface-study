"""Deterministic pre-source reservation with conservative metadata families."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['manifests/independent-project-frame-feasibility-v1.json','manifests/project-structure-screen-v1.json','manifests/project-package-screen-v1.json']
SEED='mixed-interface-independent-frame-v1'
def construct():
    frame,structure,packages=[json.loads((ROOT/p).read_text()) for p in SOURCES]
    rows=frame['rows'];names=sorted(r['full_name'].lower() for r in rows);assert len(names)==len(set(names))==20
    parents={n:n for n in names};edges=[]
    def find(x):
        while parents[x]!=x:x=parents[x]
        return x
    def join(a,b,reason):
        edges.append(dict(left=a,right=b,reason=reason));ra,rb=find(a),find(b)
        if ra!=rb:parents[max(ra,rb)]=min(ra,rb)
    owners={}
    for n in names:owners.setdefault(n.split('/')[0],[]).append(n)
    for members in owners.values():
        for member in members[1:]:join(members[0],member,'same_owner')
    risk={r['full_name'].lower() for r in structure['rows'] if r['path_groups']['generator_markers']['count']>0}
    for row in packages['rows']:
        if any(any(name in values for name in ('generator-jhipster','jhipster')) for values in row.get('framework_declarations',{}).values()):risk.add(row['full_name'].lower())
    risk=sorted(risk)
    for n in risk[1:]:join(risk[0],n,'conservative_generator_risk_bucket')
    grouped={}
    for n in names:grouped.setdefault(find(n),[]).append(n)
    groups=[]
    for members in grouped.values():
        canonical='\n'.join(sorted(members));digest=hashlib.sha256((SEED+'\n'+canonical).encode()).hexdigest()
        groups.append(dict(members=sorted(members),assignment_digest=digest))
    groups.sort(key=lambda g:g['assignment_digest']);assert len({g['assignment_digest'] for g in groups})==len(groups)
    split=len(groups)//2
    for index,g in enumerate(groups):g.update(group_id='family-'+g['assignment_digest'][:16],partition='development' if index<split else 'evaluation_reserved')
    assignments={member:g for g in groups for member in g['members']}
    result=dict(kind='prospective_metadata_family_reservation',seed=SEED,input_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},edges=edges,groups=groups,rows=[dict(rank=r['rank'],full_name=r['full_name'],commit=r['pin']['sha'],group_id=assignments[r['full_name'].lower()]['group_id'],partition=assignments[r['full_name'].lower()]['partition']) for r in rows],applications_admitted=0,independent_families_verified=0)
    assert set(assignments)==set(names)
    assert all(assignments[e['left']]['group_id']==assignments[e['right']]['group_id'] for e in edges)
    assert all(len({assignments[n]['partition'] for n in members})==1 for members in owners.values())
    assert len({assignments[n]['partition'] for n in risk})<=1
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');args=p.parse_args();result=construct();dest=ROOT/'manifests/project-family-partition-v1.json'
    if args.verify:assert result==json.loads(dest.read_text())
    else:dest.write_text(json.dumps(result,indent=2)+'\n')
    from collections import Counter
    print(json.dumps(dict(groups=len(result['groups']),group_partitions=dict(Counter(g['partition'] for g in result['groups'])),repository_partitions=dict(Counter(r['partition'] for r in result['rows'])),verified=args.verify),indent=2))
