#!/usr/bin/env bash
set -euo pipefail
out="$1"
mkdir -p "$out/extracted"
image_ref='am1n3e/webarena-verified-reddit@sha256:0594908059a03e5f610005689440a95c05e776e734006197c7b1eba12734cb46'
container_name='study-reddit-api-source-v1'
df -B1 / > "$out/disk-before.txt"
python3 - "$out/disk-before.txt" <<'PY'
import pathlib,sys
assert int(pathlib.Path(sys.argv[1]).read_text().splitlines()[1].split()[3]) >= 30000000000
PY
trap 'docker rm -f -v "$container_name" >/dev/null 2>&1 || true' EXIT
timeout 15m docker pull "$image_ref" > "$out/pull.log" 2>&1
docker image inspect "$image_ref" --format '{{json .RepoDigests}} {{.Id}} {{.Architecture}} {{.Size}}' > "$out/image-identity.txt"
docker create --name "$container_name" --network none --entrypoint /bin/true "$image_ref" > "$out/container-id.txt"
: > "$out/extraction-status.tsv"
for name in composer.json composer.lock config/routes.yaml config/routes src/Controller; do
 dest="$out/extracted/$name"
 mkdir -p "$(dirname "$dest")"
 if docker cp "$container_name:/var/www/html/$name" "$dest" 2>> "$out/extraction-errors.log"; then
  printf '%s\tcopied\n' "$name" >> "$out/extraction-status.tsv"
 else
  printf '%s\tmissing\n' "$name" >> "$out/extraction-status.tsv"
 fi
done
docker inspect "$container_name" --format '{{json .State}}' > "$out/container-state.json"
df -B1 / > "$out/disk-after.txt"
python3 - "$out" <<'PY'
import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1]);state=json.loads((root/'container-state.json').read_text())
assert state['Status']=='created' and not state['Running'] and state['StartedAt'].startswith('0001-')
files=sorted(p for p in (root/'extracted').rglob('*') if p.is_file())
assert sum(p.stat().st_size for p in files)<10*1024*1024,'Unexpected source export size'
result={'container_started':False,'scientific_cases_executed':0,'business_writes_executed':0,'extracted_files':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
(root/'extraction-summary.json').write_text(json.dumps(result,indent=2)+'\n')
print('Stopped-container source extraction complete:',len(files),'files')
PY
