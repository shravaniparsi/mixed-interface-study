#!/usr/bin/env python3
"""Merge supplied task text without model calls or new qualification content."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'results/agentcompany-task-asset-inventory-v1/source/workspaces/tasks/hr-new-grad-job-description'
OUTPUT = ROOT / 'fixtures/agentcompany-owncloud-control-v1/job_description.md'


def build():
    template = (SOURCE / 'template.md').read_text()
    requirements = (SOURCE / 'requirement.txt').read_text()
    labels = ['Key Responsibilities', 'Minimum Qualification', 'Preferred Qualification', 'Salary Range']
    sections = re.split(r'^(Key Responsibilities|Minimum Qualification|Preferred Qualification|Salary Range):\s*\n', requirements, flags=re.M)
    assert sections[0] == '' and sections[1::2] == labels
    contents = [v.strip() for v in sections[2::2]]
    assert len(contents) == 4 and template.count('[Insert Information]') == 4
    merged = template
    for content in contents:
        merged = merged.replace('[Insert Information]', content, 1)
    raw = (merged.rstrip() + '\n').encode()
    return raw, {'kind': 'agentcompany_owncloud_ordinary_control_v1',
                 'task': 'hr-new-grad-job-description', 'branches': ['native_native', 'api_native', 'api_api'],
                 'source_sha256': {name: hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() for name in ('template.md', 'requirement.txt')},
                 'payload_sha256': hashlib.sha256(raw).hexdigest(), 'payload_bytes': len(raw),
                 'destination': '/Documents/job_description.md', 'share_type': 3, 'permissions': 1,
                 'scientific_inputs': 0, 'interpretation': 'One ordinary task, three interface paths; not independent defects or a benchmark success rate.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    raw, value = build()
    manifest = ROOT / 'manifests/agentcompany-owncloud-ordinary-v1.json'
    if args.verify:
        assert OUTPUT.read_bytes() == raw and json.loads(manifest.read_text()) == value
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(raw)
        manifest.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(value, indent=2))
