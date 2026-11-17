#!/usr/bin/env python3
"""Classify the one registered build from retained evidence, without rerunning it."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUN_ID=44087019996
FREEZE='2a920b3a07f3d3a975404fa6f10427fac64a9c22'
SOURCE='29f5a77069bee0163e3cfebbb6fd5969f23160a1'
OUT=ROOT/'manifests/development-spec-build-v1.json'


def classify(directory):
    run=json.loads((directory/'run.json').read_text())
    assert run['id']==RUN_ID and run['head_sha']==FREEZE and run['run_attempt']==1
    assert run['status']=='completed', 'Do not classify a live run'
    execution=None
    jars=None
    artifact=None
    if (directory/'artifact-verification.json').exists():
        artifact=json.loads((directory/'artifact-verification.json').read_text())
        assert artifact['artifact_id']==14329468041
        assert artifact['zip_sha256']=='41c88020393302672e827018887395d8da3cd9a493f41f609d52e52cb09401cc'
    status='setup_or_evidence_incomplete'
    if (directory/'execution.json').exists():
        execution=json.loads((directory/'execution.json').read_text())
        assert execution['command_timeout_seconds']==1500
        assert (directory/'source-commit.txt').read_text().strip()==SOURCE
        assert 'Temurin-17.0.2+8' in (directory/'java-version.txt').read_text()
        status='build_failed' if execution['exit_code'] else 'build_output_unqualified'
        if (directory/'jars.json').exists():
            jars=json.loads((directory/'jars.json').read_text())
        if execution['exit_code']==0 and run['conclusion']=='success' and jars is not None:
            log=(directory/'build.log').read_text()
            required=['> Task :webapp', '> Task :compileJava', '> Task :bootJar']
            if (len(jars)==1 and jars[0].get('executable_boot_jar') is True and
                jars[0].get('bytes',0)>0 and jars[0]['bytes']<=268435456 and
                all(token in log.splitlines() for token in required) and 'BUILD SUCCESSFUL' in log):
                if artifact is not None:
                    checks=artifact['jar_checks']
                    assert checks['jar_sha256']==jars[0]['sha256'] and checks['bytes']==jars[0]['bytes']
                    assert checks['launcher_present'] and checks['boot_classes_entries']>0
                    status='original_bootjar_build_qualified'
    return dict(kind='closed_development_bootjar_build',run_id=RUN_ID,freeze=FREEZE,
        source_commit=SOURCE,workflow_conclusion=run['conclusion'],status=status,
        execution=execution,jars=jars,artifact=artifact,
        github_timing=json.loads((directory/'timing.json').read_text()),
        files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.iterdir())
               if p.is_file() and p.suffix not in ('.jar','.zip')},
        application_started=False,specification_obtained=False,baseline_qualified=False,
        independent_evaluation_cases=0)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--verify',action='store_true')
    a=p.parse_args()
    text=json.dumps(classify(a.archive),indent=2)+'\n'
    if a.verify:
        assert OUT.read_text()==text
        print('Closed build classification and archive hashes verified')
    else:
        OUT.write_text(text)
        print(json.loads(text)['status'])
