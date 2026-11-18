#!/usr/bin/env bash
set -euo pipefail
: "${GITHUB_WORKSPACE:?}" "${BROWSER_NODE:?}" "${BROWSER_TOOLS:?}" "${BROWSER_EVIDENCE:?}"
test "$#" -eq 5
test "$1" = "$GITHUB_WORKSPACE/scripts/extension/observe_development_checkpoint_v2.mjs"
test "$2" = '--phase'
test "$4" = '--out'
test "$5" = "$BROWSER_EVIDENCE"
case "$3" in seed|restore1|restore2) phase_name="$3";; *) exit 2;; esac
set +e
docker run --name study-checkpoint-browser --network container:study-elasticsearch --shm-size=1g \
  -v "$BROWSER_NODE:/study/node:ro" -v "$BROWSER_TOOLS:/study/tools:ro" \
  -v "$GITHUB_WORKSPACE:$GITHUB_WORKSPACE:ro" -v "$BROWSER_EVIDENCE:$BROWSER_EVIDENCE" \
  -e PLAYWRIGHT_MODULE_PATH=/study/tools/node_modules/playwright \
  -e CHROME_EXECUTABLE=/ms-playwright/chromium-1234/chrome-linux64/chrome \
  mcr.microsoft.com/playwright@sha256:c091b21d9fae78c76e85cd4356431e9b018402f172a214fc7d7a5e9a7e29d8ac \
  /study/node "$@"
browser_exit=$?
set -e
docker inspect study-checkpoint-browser > "$BROWSER_EVIDENCE/$phase_name-browser-container.json"
docker rm -f study-checkpoint-browser > /dev/null
exit "$browser_exit"
