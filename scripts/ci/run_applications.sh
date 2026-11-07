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
  realworld-capture-controls)
    mkdir -p "$STUDY_RUNTIME/realworld-execution" "$CI_ARTIFACT_DIR/realworld-legacy-controls"
    python scripts/validate_realworld_capture.py --prepare --artifact-root "$CI_ARTIFACT_DIR" --generated-root "$STUDY_RUNTIME/realworld-execution"
    timeout --signal=TERM --kill-after=20s 180s python scripts/run_generated_integration.py \
      --subject "$STUDY_RUNTIME/realworld/realworld-django-ninja" \
      --python "$STUDY_RUNTIME/realworld/venv/bin/python" --node "$(command -v node)" \
      --runtime-root "$STUDY_RUNTIME/realworld-execution" --phase controls
    timeout --signal=TERM --kill-after=20s 240s python scripts/run_realworld_boundaries.py \
      --subject "$STUDY_RUNTIME/realworld/realworld-django-ninja" \
      --python "$STUDY_RUNTIME/realworld/venv/bin/python" --node "$(command -v node)" \
      --runtime-root "$STUDY_RUNTIME/realworld-execution" \
      --registry manifests/realworld-boundary-registry-v1.json \
      --output-root "$CI_ARTIFACT_DIR/realworld-legacy-controls" \
      --candidate article-valid --candidate comment-body-valid --candidate profile-bio-valid \
      --candidate article-update-unique-partial --candidate comment-native-control --candidate profile-native-control
    python scripts/validate_realworld_capture.py --artifact-root "$CI_ARTIFACT_DIR" --generated-root "$STUDY_RUNTIME/realworld-execution"
    ;;
  realworld-integrity-controls)
    mkdir -p "$STUDY_RUNTIME/realworld-execution" "$CI_ARTIFACT_DIR/realworld-legacy-controls"
    python scripts/validate_realworld_integrity.py --prepare --artifact-root "$CI_ARTIFACT_DIR" --generated-root "$STUDY_RUNTIME/realworld-execution"
    timeout --signal=TERM --kill-after=20s 180s python scripts/run_generated_integration.py \
      --subject "$STUDY_RUNTIME/realworld/realworld-django-ninja" \
      --python "$STUDY_RUNTIME/realworld/venv/bin/python" --node "$(command -v node)" \
      --runtime-root "$STUDY_RUNTIME/realworld-execution" --phase integrity-controls
    timeout --signal=TERM --kill-after=20s 240s python scripts/run_realworld_boundaries.py \
      --subject "$STUDY_RUNTIME/realworld/realworld-django-ninja" \
      --python "$STUDY_RUNTIME/realworld/venv/bin/python" --node "$(command -v node)" \
      --runtime-root "$STUDY_RUNTIME/realworld-execution" \
      --registry manifests/realworld-boundary-registry-v1.json \
      --output-root "$CI_ARTIFACT_DIR/realworld-legacy-controls" \
      --candidate article-valid --candidate comment-body-valid --candidate profile-bio-valid \
      --candidate article-update-unique-partial --candidate comment-native-control --candidate profile-native-control \
      --candidate article-body-omitted --candidate comment-body-omitted --candidate profile-username-empty
    python scripts/validate_realworld_integrity.py --artifact-root "$CI_ARTIFACT_DIR" --generated-root "$STUDY_RUNTIME/realworld-execution"
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
