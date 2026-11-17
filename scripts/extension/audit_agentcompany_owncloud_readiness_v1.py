"""Reconstruct source/DOM observations, without claiming a runtime race."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'results/agentcompany-owncloud-readiness-source-v1'
ARCHIVE = ROOT / 'results/agentcompany-owncloud-ordinary-ci-44052230460/artifact'


def build():
    collection = json.loads((SOURCE / 'collection.json').read_text())
    assert collection['revision'] == '097d4d22e0cf3341c4923e26453efb32ddedfb24'
    for record in collection['files']:
        data = (SOURCE / record['path']).read_bytes()
        assert len(data) == record['bytes']
        assert hashlib.sha256(data).hexdigest() == record['sha256']
    anchors = {
        'apps/files/js/file-upload.js': ["freeSpace = $('#free_space').val();", 'freeSpace >= 0 && selection.totalBytes > freeSpace', 'return false; //don\'t upload anything'],
        'apps/files/js/files.js': ["getstoragestats.php", "$('#free_space').val(response.data.freeSpace);"],
        'apps/files/templates/list.php': ['id="free_space"', "isset($_['freeSpace'])"],
    }
    for name, literals in anchors.items():
        text = (SOURCE / name).read_text()
        assert all(literal in text for literal in literals)
    filelist = ROOT / 'results/agentcompany-owncloud-control-source-v1/apps/files/js/filelist.js'
    text = filelist.read_text()
    assert 'Math.ceil(this.$container.height() / 50)' in text
    assert 'this.updateStorageStatistics(true);' in text and 'this._nextPage(true);' in text
    observations = []
    for branch in ('native_native', 'api_native'):
        raw = (ARCHIVE / branch / 'failure.html').read_bytes()
        text = raw.decode()
        rows = re.findall(r'<tr\b[^>]*data-file="([^"]+)"', text)
        free_space = re.findall(r'<input\b[^>]*id="free_space"[^>]*value="([^"]*)"', text)
        assert len(free_space) == 1 and len(rows) == 14
        assert rows[-1] == 'Example.odt' and 'job_description.md' not in rows
        observations.append(dict(branch=branch, html_sha256=hashlib.sha256(raw).hexdigest(),
                                 rendered_files=rows, terminal_free_space=free_space[0]))
    return dict(kind='owncloud_readiness_source_diagnostic_v1', source_files=collection['files'],
                source_anchors=anchors, filelist_sha256=hashlib.sha256(filelist.read_bytes()).hexdigest(),
                terminal_dom_observations=observations,
                inference='Asynchronous storage update and viewport pagination are supported by upstream source. The earlier failure mechanism is not causally established.',
                missing_evidence=['Packaged equivalence for newly read source files', 'Free-space value at file selection time', 'Directory and storage response bodies and callback timing'],
                scientific_cases=0, confirmed_defects=0, application_reruns=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--verify', action='store_true'); args = parser.parse_args()
    value = build()
    target = ROOT / 'manifests/agentcompany-owncloud-readiness-diagnostic-v1.json'
    if args.verify:
        assert json.loads(target.read_text()) == value
    else:
        target.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: value[k] for k in ('inference', 'missing_evidence', 'scientific_cases', 'confirmed_defects', 'application_reruns')}, indent=2))
