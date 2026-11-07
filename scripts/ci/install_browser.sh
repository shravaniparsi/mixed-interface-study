#!/usr/bin/env bash
set -euo pipefail
: "${RUNNER_TEMP:?}" "${GITHUB_ENV:?}" "${CI_ARTIFACT_DIR:?}"
ci_tools="$RUNNER_TEMP/study-node-tools"
mkdir -p "$ci_tools" "$CI_ARTIFACT_DIR"
cp scripts/ci/package.json "$ci_tools/package.json"
npm install --prefix "$ci_tools" --ignore-scripts --no-audit --no-fund
cp "$ci_tools/package-lock.json" "$CI_ARTIFACT_DIR/node-tools-package-lock.json"
export PLAYWRIGHT_BROWSERS_PATH="$RUNNER_TEMP/study-playwright-browsers"
export PLAYWRIGHT_MODULE_PATH="$ci_tools/node_modules/playwright"
node "$PLAYWRIGHT_MODULE_PATH/cli.js" install --with-deps --no-shell chromium
ci_chromium="$(node scripts/ci/browser_info.mjs --output "$CI_ARTIFACT_DIR/browser.json")"
printf '%s\n' "PLAYWRIGHT_BROWSERS_PATH=$PLAYWRIGHT_BROWSERS_PATH" "PLAYWRIGHT_MODULE_PATH=$PLAYWRIGHT_MODULE_PATH" "CHROME_EXECUTABLE=$ci_chromium" >> "$GITHUB_ENV"
