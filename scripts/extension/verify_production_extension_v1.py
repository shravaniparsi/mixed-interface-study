#!/usr/bin/env python3
"""Rebuild every finite result from retained raw evidence and compare saved proofs."""
import hashlib,importlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUNS=[('linkding','initial','42879907054'),('paperless','initial','42885223012'),('grocy','initial','42893369321'),('grocy','followup','42894961954'),('memos','initial','42901314025'),('memos','followup','42902643603'),('vikunja','initial','42907501262'),('vikunja','followup','42908626421'),('gitea','initial','42911846583'),('gitea','followup','42912939898')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
    rows=[]
    for app,phase,run in RUNS:
        p=ROOT/'manifests'/f'{app}-{phase}-results-v1.json';module=importlib.import_module(f'verify_{app}_{"cases" if phase=="initial" else "followups"}_v1');folder=ROOT/'results'/(f'{app}-cases-v1-initial-ci-{run}' if phase=='initial' else f'{app}-followups-v1-ci-{run}')
        if phase=='initial' and app in ['linkding','paperless','grocy']:rebuilt=module.check(folder,ROOT/'manifests'/f'{app}-execution-v1.json')
        elif phase=='initial' and app=='gitea':rebuilt=module.build(folder,ROOT/'manifests/gitea-execution-v1.json')
        else:rebuilt=module.build(folder)
        assert rebuilt==json.loads(p.read_text()),'Saved proof differs: '+str(p)
        rows.append(dict(application=app,phase=phase,run_id=run,pairs=len(rebuilt['records']),proof=str(p.relative_to(ROOT)),proof_sha256=sha(p),verifier=str(Path(module.__file__).relative_to(ROOT)),verifier_sha256=sha(Path(module.__file__))))
    return dict(kind='production_extension_reverification_v1',runs=rows,total_pairs=sum(r['pairs'] for r in rows),all_saved_proofs_reconstructed=True,scope='Finite scientific initial/followup runs only. Does not erase qualification failures, the one Memos unqualified repeat, or separate exploratory cohorts.')
if __name__=='__main__':
    p=ROOT/'manifests/production-extension-reverification-v1.json';assert not p.exists();v=build();p.write_text(json.dumps(v,indent=2)+'\n');print('Reconstructed',len(v['runs']),'runs;',v['total_pairs'],'pairs.')
