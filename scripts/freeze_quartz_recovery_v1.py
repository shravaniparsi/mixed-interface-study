#!/usr/bin/env python3
"""Release the prepared recovery collection after successful hosted CI; never bypass billing."""
import argparse,subprocess
from datetime import datetime,timezone
from pathlib import Path
from quartz_recovery_preflight_v1 import ROOT,PREPARATION,FREEZE,read,sha
from verify_quartz_recovery_release_v1 import preparation_verified,ci_accepted
from mixed_interface.common_execution_v1 import write
from mixed_interface.repetition import require

def freeze(ci_path):
    require(not FREEZE.exists(),'Recovery already released')
    prep=preparation_verified();commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    require(not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip(),'Tracked source changes pending')
    ci=read(ci_path);ci_accepted(ci,commit)
    target=ROOT/'manifests/quartz-recovery-release-ci-v1.json';require(not target.exists(),'CI record already retained');target.write_bytes(Path(ci_path).read_bytes())
    value={'kind':'prospective_exposed_quartz_recovery_release_v1','frozen_at_utc':datetime.now(timezone.utc).isoformat(),
        'primary_freeze_complete':True,'preparation_sha256':sha(PREPARATION),'qualification_sha256':prep['qualification_sha256'],
        'source_commit':commit,'hosted_ci_run':ci['id'],'hosted_ci_record':str(target.relative_to(ROOT)),'hosted_ci_record_sha256':sha(target),
        'scope':prep['scope']}
    write(FREEZE,value);return value
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--ci-run-json',type=Path,required=True);args=p.parse_args();print(freeze(args.ci_run_json)['frozen_at_utc'])
