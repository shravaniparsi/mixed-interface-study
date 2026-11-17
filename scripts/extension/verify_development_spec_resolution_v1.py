#!/usr/bin/env python3
"""Recheck retained resolution evidence without rerunning Gradle."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DIR=ROOT/'results/development-spec-resolution-v1-ci-44086283562'
OUT=ROOT/'manifests/development-spec-resolution-v1.json'
def build():
    run=json.loads((DIR/'run.json').read_text())
    execution=json.loads((DIR/'execution.json').read_text())
    timing=json.loads((DIR/'timing.json').read_text())
    log=(DIR/'dependency-insight.log').read_text()
    assert run['id']==44086283562 and run['head_sha']=='cd4cc87c0337d6840774d9660cf5f3b7fd87dbd9'
    assert run['status']=='completed' and run['conclusion']=='success' and run['run_attempt']==1
    assert (DIR/'source-commit.txt').read_text().strip()=='29f5a77069bee0163e3cfebbb6fd5969f23160a1'
    assert execution['exit_code']==0 and execution['elapsed_seconds']<=600
    assert 'Temurin-17.0.2+8' in (DIR/'java-version.txt').read_text()
    assert '> Task :dependencyInsight' in log and 'BUILD SUCCESSFUL' in log
    assert 'org.springdoc:springdoc-openapi-webmvc-core:1.6.11 (by constraint)' in log
    assert 'tech.jhipster:jhipster-dependencies:7.9.3' in log
    assert '1 actionable task: 1 executed' in log
    return dict(kind='closed_development_dependency_resolution',run_id=run['id'],attempt=1,
        freeze=run['head_sha'],source_commit=(DIR/'source-commit.txt').read_text().strip(),
        artifact_id=14328764052,artifact_zip_sha256='14359c7b5024488a2a5ee397fbc0bc4f56f48386d6f9a876e1040772877c3c40',
        resolved_dependency='org.springdoc:springdoc-openapi-webmvc-core:1.6.11',
        qualification='runtimeClasspath_dependency_resolution_only',execution=execution,
        github_timing=timing,files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DIR.iterdir()) if p.is_file()},
        application_compiled=False,specification_obtained=False,baseline_qualified=False,independent_evaluation_cases=0)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args()
    text=json.dumps(build(),indent=2)+'\n'
    if a.verify:
        assert OUT.read_text()==text
        print('Closed resolution evidence verified; application/specification baseline remains unqualified')
    else:OUT.write_text(text)
