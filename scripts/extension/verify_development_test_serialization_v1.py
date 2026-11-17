#!/usr/bin/env python3
"""Verify archived byte evidence without rerunning closed serialization."""
import base64
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
out=ROOT/'results/development-test-serialization-v1'
d=json.loads((out/'measurement.json').read_text())
assert not d['errors'] and len(d['rows'])==5
assert hashlib.sha256((out/'SerializationProbe.java').read_bytes()).hexdigest()==d['wrapper_sha256']
assert all(c['exit_code']==0 for c in d['commands'])
execution=d['commands'][-1]
assert execution['args'][-1]=='SerializationProbe' and not execution['stderr']
lines=execution['stdout'].splitlines()
assert len(lines)==len(d['rows'])
for row,line in zip(d['rows'],lines):
    name,encoded=line.split('\t')
    raw=base64.b64decode(encoded,validate=True)
    assert name==row['id'] and row['status']=='serialized'
    assert hashlib.sha256(raw).hexdigest()==row['body_sha256']
    assert json.loads(raw)==row['body']
    assert row['password_presence']==('present' if 'password' in row['body'] else 'absent')
assert 'password' not in d['rows'][-1]['body']
assert d['independent_evaluation_cases']==d['application_requests']==0
print('Five archived serialization byte records verified; null-password fixture omits password. No backend outcome verified.')
