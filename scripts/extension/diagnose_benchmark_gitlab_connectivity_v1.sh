#!/usr/bin/env bash
set -euo pipefail
out="$1"
mkdir -p "$out"
image_ref='am1n3e/webarena-verified-gitlab@sha256:673ba94d757c5b3f4bb55751ad8b745a33bad2b987349322403cbc41035a92e0'
container_name='study-gitlab-connectivity-v1'
network_name='study-gitlab-connectivity-net-v1'
df -B1 / > "$out/disk-before.txt"
python3 - "$out/disk-before.txt" <<'PY'
import pathlib,sys
assert int(pathlib.Path(sys.argv[1]).read_text().splitlines()[1].split()[3]) >= 70000000000
PY
cleanup() {
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
docker inspect "$container_name" --format '{{json .NetworkSettings.Ports}}' > "$out/published-ports.json"
docker network inspect "$network_name" --format '{{.Internal}} {{.Driver}}' > "$out/network-mode.txt"
python3 scripts/extension/probe_benchmark_gitlab_connectivity_v1.py --container "$container_name" --output "$out/connectivity.json"
