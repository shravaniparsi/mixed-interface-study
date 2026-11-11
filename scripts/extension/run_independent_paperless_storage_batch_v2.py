#!/usr/bin/env python3
"""Bounded, serial fresh-container pairs within a registered CI batch."""
import argparse,json,subprocess,time,signal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    reg=json.loads((ROOT/'manifests/independent-paperless-storage-execution-v2.json').read_text());batch=next(b for b in reg['batches'] if b['id']==a.batch);units={u['id']:u for u in reg['units']};a.output.mkdir(parents=True,exist_ok=False);records=[];failed=False;start=time.monotonic()
    child=None
    def interrupted(signum,frame):
        if child and child.poll() is None:
            child.terminate()
            try:child.wait(timeout=60)
            except subprocess.TimeoutExpired:child.kill()
        raise SystemExit(124)
    signal.signal(signal.SIGTERM,interrupted)
    for uid in batch['unit_ids']:
        child=subprocess.Popen(['python','scripts/extension/run_independent_paperless_storage_cases_v2.py','--unit',uid,'--output',str(a.output/uid)],cwd=ROOT)
        try:code=child.wait(timeout=900)
        except subprocess.TimeoutExpired:
            child.terminate()
            try:child.wait(timeout=60)
            except subprocess.TimeoutExpired:child.kill();child.wait()
            code=124
        ok=code==0
        if units[uid]['cohort']=='valid_control' and ok:
            for channel in ('api','ui'):
                o=json.loads((a.output/uid/channel/'observation.json').read_text());ok=ok and o['continuation']=='clean_preserving_continuation' and not o.get('response_contract_violations') and not o.get('native_representation_signal')
        failed=failed or not ok;records.append({'unit':uid,'returncode':code,'gate_passed':ok});(a.output/'batch.json').write_text(json.dumps({'batch':a.batch,'records':records,'elapsed_s':time.monotonic()-start},indent=2)+'\n')
    return int(failed)
if __name__=='__main__':raise SystemExit(main())
