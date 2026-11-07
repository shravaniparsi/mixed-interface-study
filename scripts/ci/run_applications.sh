#!/usr/bin/env bash
set -euo pipefail
: "${STUDY_SUITE:?}" "${STUDY_RUNTIME:?}" "${CI_ARTIFACT_DIR:?}" "${PLAYWRIGHT_MODULE_PATH:?}" "${CHROME_EXECUTABLE:?}"
case "$STUDY_SUITE" in
  quartz-controls)
    : "${JAVA_HOME:?}"
    timeout --signal=TERM --kill-after=20s 480s node scripts/run_quartz_registry.mjs \
      --runtime "$STUDY_RUNTIME/quartz" --java "$JAVA_HOME/bin/java" \
      --registry manifests/quartz-job-generated-pool-v2.json \
      --output "$CI_ARTIFACT_DIR/quartz-controls" --mode controls \
      --playwright-module "$PLAYWRIGHT_MODULE_PATH" --chrome-executable "$CHROME_EXECUTABLE"
    ;;
  quartz-paired-controls)
    : "${JAVA_HOME:?}"
    timeout --signal=TERM --kill-after=20s 480s python scripts/run_quartz_pairs.py \
      --runtime "$STUDY_RUNTIME/quartz" --java "$JAVA_HOME/bin/java" \
      --node "$(command -v node)" --python "$(command -v python)" \
      --registry manifests/quartz-job-generated-pool-v2.json \
      --output "$CI_ARTIFACT_DIR/quartz-paired-controls" \
      --playwright-module "$PLAYWRIGHT_MODULE_PATH" --chrome-executable "$CHROME_EXECUTABLE" \
      --environment-file "$CI_ARTIFACT_DIR/runtime-versions.json" \
      --browser-info "$CI_ARTIFACT_DIR/browser.json"
    ;;
  realworld-integration)
    mkdir -p "$STUDY_RUNTIME/realworld-execution"
    timeout --signal=TERM --kill-after=20s 480s python scripts/run_generated_integration.py \
      --subject "$STUDY_RUNTIME/realworld/realworld-django-ninja" \
      --python "$STUDY_RUNTIME/realworld/venv/bin/python" --node "$(command -v node)" \
      --runtime-root "$STUDY_RUNTIME/realworld-execution" --phase all
    ;;
  *)
    printf 'Unsupported suite: %s\n' "$STUDY_SUITE" >&2
    exit 2
    ;;
esac
