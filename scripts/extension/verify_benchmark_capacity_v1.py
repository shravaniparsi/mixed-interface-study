#!/usr/bin/env python3
"""Verify read-only host evidence and immutable image metadata."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def main():
    parser = argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    archive=ROOT/'results/benchmark-host-capacity-v1-ci-43166124958';folder=archive/'benchmark-host-capacity-43166124958'
    run=json.loads((archive/'run.json').read_text());assert run['status']=='completed' and run['conclusion']=='success';assert run['headSha']=='e570dc154415bc233fa795de19603a1f5d5c501c'
    jobs=run['jobs'];assert len(jobs)==1
    job=jobs[0];duration=(datetime.fromisoformat(job['completedAt'].replace('Z','+00:00'))-datetime.fromisoformat(job['startedAt'].replace('Z','+00:00'))).total_seconds()
    rows=[line.split() for line in (folder/'filesystems.txt').read_text().splitlines()[1:]]
    rootrows=[row for row in rows if row[-1]=='/'];assert rootrows and all(row==rootrows[0] for row in rootrows)
    available=int(rootrows[0][3]);memory=next(line.split() for line in (folder/'memory.txt').read_text().splitlines() if line.startswith('Mem:'))
    proof=ROOT/'results/benchmark-image-digest-verification-v1';images=json.loads((proof/'verification.json').read_text())
    for row in images:
        raw=(proof/(row['site']+'-manifest.raw.json')).read_bytes();assert 'sha256:'+hashlib.sha256(raw).hexdigest()==row['manifest_digest'];manifest=json.loads(raw)
        raw=(proof/(row['site']+'-config.raw.json')).read_bytes();assert 'sha256:'+hashlib.sha256(raw).hexdigest()==row['config_digest']==manifest['config']['digest']
        assert row['compressed_layer_bytes']==sum(layer['size'] for layer in manifest['layers'])
    files=sorted(p for base in [archive,proof] for p in base.rglob('*') if p.is_file())
    result={'kind':'benchmark_capacity_verification_v1','run_id':43166124958,'job_id':job['databaseId'],'job_seconds':duration,'root_available_bytes':available,'memory_total_bytes':int(memory[1]),'cpu_count':int((folder/'cpus.txt').read_text()),'engineering_disk_threshold_bytes':70000000000,'disk_threshold_met':available>=70000000000,'cleanup_performed':False,'image_layers_downloaded':False,'application_tasks_executed':0,'paid_model_calls':0,'images':images,'scope':'One observed disposable runner; next job must recheck capacity. No conclusion about API compatibility or scientific validity.','source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    target=ROOT/'manifests/benchmark-capacity-v1.json'
    if args.verify:assert json.loads(target.read_text())==result
    else:target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['source_sha256','images']},indent=2))

if __name__=='__main__':main()
