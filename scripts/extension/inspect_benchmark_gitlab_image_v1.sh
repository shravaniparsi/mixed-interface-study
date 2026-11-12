#!/usr/bin/env bash
set -euo pipefail
out="$1"
mkdir -p "$out/extracted"
image_ref='am1n3e/webarena-verified-gitlab@sha256:673ba94d757c5b3f4bb55751ad8b745a33bad2b987349322403cbc41035a92e0'
container_name='study-gitlab-metadata-v1'
df -B1 / > "$out/disk-before.txt"
free -b > "$out/memory.txt"
python3 - "$out/disk-before.txt" <<'PY'
import pathlib,sys
fields=pathlib.Path(sys.argv[1]).read_text().splitlines()[1].split()
assert int(fields[3]) >= 70000000000, 'Insufficient free space: no image pull permitted'
PY
trap 'docker rm -f "$container_name" >/dev/null 2>&1 || true' EXIT
timeout 15m docker pull "$image_ref" 2>&1 | tee "$out/pull.log"
docker image inspect "$image_ref" --format '{{json .RepoDigests}} {{.Id}} {{.Architecture}} {{.Size}}' > "$out/image-identity.txt"
docker create --name "$container_name" --network none --entrypoint /bin/true "$image_ref" > "$out/container-id.txt"
: > "$out/extraction-status.tsv"
for name in VERSION REVISION GITLAB_REVISION doc/api/projects.md doc/api/issues.md doc/api/merge_requests.md doc/api/members.md doc/api/repository_files.md doc/api/commits.md doc/api/index.md; do
  dest="$out/extracted/$name"
  mkdir -p "$(dirname "$dest")"
  if docker cp "$container_name:/opt/gitlab/embedded/service/gitlab-rails/$name" "$dest" 2>> "$out/extraction-errors.log"; then
    printf '%s\t%s\n' "$name" copied >> "$out/extraction-status.tsv"
  else
    printf '%s\t%s\n' "$name" missing >> "$out/extraction-status.tsv"
  fi
done
if docker cp "$container_name:/opt/gitlab/version-manifest.txt" "$out/extracted/package-version-manifest.txt" 2>> "$out/extraction-errors.log"; then
  printf '%s\t%s\n' package-version-manifest.txt copied >> "$out/extraction-status.tsv"
else
  printf '%s\t%s\n' package-version-manifest.txt missing >> "$out/extraction-status.tsv"
fi
docker inspect "$container_name" --format '{{json .State}}' > "$out/container-state.json"
df -B1 / > "$out/disk-after.txt"
python3 - "$out" <<'PY'
import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1]);state=json.loads((root/'container-state.json').read_text())
assert state['Status']=='created' and not state['Running']
files=sorted(p for p in (root/'extracted').rglob('*') if p.is_file())
result={'container_started':False,'scientific_cases_executed':0,'extracted_files':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'version_file_present':(root/'extracted/VERSION').exists()}
(root/'extraction-summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
PY
