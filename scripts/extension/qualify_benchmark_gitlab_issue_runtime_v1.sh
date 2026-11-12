#!/usr/bin/env bash
set -euo pipefail
out="$1"
mkdir -p "$out"
credentials_file="$(mktemp)"
image_ref='am1n3e/webarena-verified-gitlab@sha256:673ba94d757c5b3f4bb55751ad8b745a33bad2b987349322403cbc41035a92e0'
container_name='study-gitlab-issue-control-v1'
network_name='study-gitlab-issue-control-net-v1'
df -B1 / > "$out/disk-before.txt"
python3 - "$out/disk-before.txt" <<'PY'
import pathlib,sys
assert int(pathlib.Path(sys.argv[1]).read_text().splitlines()[1].split()[3]) >= 70000000000
PY
cleanup() {
  rm -f "$credentials_file"
  docker inspect "$container_name" --format '{{.State.Status}} {{.State.Running}} {{.State.OOMKilled}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' > "$out/container-state.json" 2>/dev/null || true
  timeout 30s docker exec "$container_name" gitlab-ctl status > "$out/service-status.txt" 2>&1 || true
  docker exec "$container_name" cat /opt/gitlab/embedded/service/gitlab-rails/VERSION > "$out/version.txt" 2>/dev/null || true
  df -B1 / > "$out/disk-after.txt"
  docker rm -f "$container_name" >/dev/null 2>&1 || true
  docker network rm "$network_name" >/dev/null 2>&1 || true
}
trap cleanup EXIT
timeout 15m docker pull "$image_ref" > "$out/pull.log" 2>&1
docker image inspect "$image_ref" --format '{{json .RepoDigests}} {{.Id}} {{.Architecture}}' > "$out/image-identity.txt"
docker network create --internal "$network_name" > "$out/network-id.txt"
docker run -d --name "$container_name" --network "$network_name" --memory 10g --cpus 4 -p 127.0.0.1:8023:8023 "$image_ref" > "$out/container-id.txt"
python3 - "$credentials_file" <<'CREDS'
import json,os,pathlib,runpy,sys
module=runpy.run_path('scripts/extension/qualify_benchmark_gitlab_auth_v1.py')
path=pathlib.Path(sys.argv[1]);os.chmod(path,0o600)
path.write_text(json.dumps(module['benchmark_credentials']()))
CREDS
container_pid="$(docker inspect "$container_name" --format '{{.State.Pid}}')"
printf '%s\n' "$container_pid" > "$out/network-namespace-pid.txt"
sudo nsenter --target "$container_pid" --net -- /usr/bin/python3 - "$out" <<'PY'
import json,pathlib,sys,time,urllib.request,urllib.error
out=pathlib.Path(sys.argv[1]); start=time.monotonic(); attempts=[]; ready=False
while time.monotonic()-start < 600:
    row={'elapsed_seconds':round(time.monotonic()-start,3)}
    try:
        with urllib.request.urlopen('http://127.0.0.1:8023/-/health', timeout=10) as response:
            row.update(status=response.status,body=response.read(4096).decode('utf-8',errors='replace'))
        ready=row['status']==200 and row['body'].strip()=='GitLab OK'
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        row['error_type']=type(exc).__name__
    attempts.append(row)
    (out/'readiness.json').write_text(json.dumps({'ready':ready,'scientific_cases_executed':0,'attempts':attempts},indent=2)+'\n')
    if ready:
        break
    time.sleep(min(20,max(0,600-(time.monotonic()-start))))
print(json.dumps({'ready':ready,'attempts':len(attempts),'elapsed_seconds':round(time.monotonic()-start,3)}))
sys.exit(0 if ready else 1)
PY
timeout 2m sudo nsenter --target "$container_pid" --net -- /usr/bin/python3 scripts/extension/qualify_benchmark_gitlab_auth_v2.py --credentials-file "$credentials_file" --output "$out/authentication.json"
timeout 6m sudo nsenter --target "$container_pid" --net -- env PLAYWRIGHT_MODULE_PATH="$PLAYWRIGHT_MODULE_PATH" CHROME_EXECUTABLE="$CHROME_EXECUTABLE" "$(command -v node)" scripts/extension/qualify_benchmark_gitlab_issue_controls_v1.mjs --credentials "$credentials_file" --out "$out" --branch "$CONTROL_BRANCH"
