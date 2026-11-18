# Viseron build, authentication and state-boundary mapping

Source wave 9 was published at 66b2778ab51dc8eaf84a442ad1dae19d7927a838 before its eighteen-file acquisition. All eighteen blobs verified. Viseron's total is now 44 scheduled blobs/295,324 decoded bytes. The tracked public build environment contains version/checksum/build settings, including a public Python signing-key fingerprint; its keys were inspected before relevant version values were displayed. No repository/personal secret store was accessed and no credential was identified there.

## Executable candidate

The original amd64 compose target uses roflcoopter/amd64-viseron:dev. Its original build template passes Build.SourceVersion as VISERON_GIT_COMMIT, and the Dockerfile persists that value in the final image environment. Metadata inspection was prospectively published at 268891ba6960f28fbc01788026f5a30502b9c930, then completed using three registry requests without layers or execution. The tag is a direct linux/amd64 manifest:

- Manifest sha256:91c9ffb15859ce05b62792acfacec61c6eaf0de14f9fbe88780c5a8aee2d9a43.
- Config sha256:e7b2904341af931c754f815f865c799b0a0ee0a86f5aeff091de57d063e417e7.
- Declared full source commit 3d77e324d8316033f30acb83058736aa7e468d81 matches the frozen application revision.
- Twenty-one layers total 2,380,806,358 compressed bytes.

This is a matching publisher declaration plus original build-pipeline mapping, not yet a qualified executable. A registered runtime job must verify image identity, relevant packaged backend/rootfs files against acquired source hashes, frontend build provenance and actual runtime dependency versions. Frontend source is compiled into assets and is not copied as source into the final image by the inspected Dockerfile; do not claim bytewise frontend-source verification from the image config alone. No local pull is appropriate on the storage-constrained machine. No application job has started for Viseron.

Original build inputs include amd64 base 1.11.0-noble, OpenCV 4.13.0-noble, FFmpeg 8.1-noble, wheels 1.12-noble, GPAC 2.4.0-noble, Hailo 4.22.0-noble, Node 24.19.0, s6 overlay 2.1.0.2 and go2rtc 1.9.14. These were read from original build configuration; their tags have not separately been resolved and no source rebuild is currently scheduled.

## Browser/authentication contract

The original frontend root uses HashRouter. For a root deployment the candidate page is /#/settings/users, preserving pathname / and API base /api/v1. A direct /settings/users navigation must not be substituted by guessing. Original localStorage token data, client-id base, XSRF cookie/header and the signature cookie are required; do not authenticate an API branch using a different token type or actor.

The original constants define a thirty-minute access-token lifetime. The existing browser helper refreshes missing or near-expiring tokens, while ordinary validation of a valid JWT does not itself save auth data. Restored comparisons must preserve the seed browser context and auth store, verify sufficient token lifetime and record any refresh. Token expiry or refresh is not silently ignored. Native user requests and the source materializer remain unqualified until observed together in ordinary controls.

## Persisted state and services

Default/core components are logger, data_stream, webserver and storage; this does not by itself prove successful camera-free startup. Configuration lives at /config/config.yaml by default. JSON storage lives under /config/.viseron: auth contains users/refresh tokens/personal tokens; onboarding is the persistent completion marker; webserver contains the cookie-signing secret. The latter must be restored along with the auth data or saved browser cookies will not authenticate. Public images live under /config/public_images; temporary downloads under /tmp/downloads are cleared on webserver startup. No images/downloads/cameras are intended in this fixture, but their empty state must be checked.

The original init/run/shutdown scripts explicitly skip embedded PostgreSQL when POSTGRES_DATABASE_URL is supplied. Otherwise PGDATA defaults to /config/postgresql, the installed PostgreSQL major is detected from psql, and original shutdown waits for the app then stops the server. Do not assume the installed database major from the Ubuntu tag alone. Prefer investigating the original external-DB option so app/config state can be stopped while its database remains available for consistent logical snapshots; storage-component connection handling and defaults still need source review before choosing that deployment.

A complete stopped-cluster file backup is another supported PostgreSQL strategy, but it requires the entire cluster and a stopped server during both copy and restoration, not selected table files. See https://www.postgresql.org/docs/current/backup-file.html. No such backup has been executed or qualified here. Logs, process state, storage maintenance and startup effects must be explicitly accounted for before comparisons; no blanket timestamp exclusions or unsupported snapshot assumptions.

## Original schema baseline

scripts/extension/evaluate_viseron_original_schema_v1.py is written but has only been syntax checked. In a future registered original runtime it will verify Voluptuous 0.16.0 and the exact acquired auth-module SHA256, select the actual /auth/create POST route schema, and validate a private request file without calling the mutation. It records acceptance or structural error classes/paths, not request secrets. This is an original executable API-schema baseline, not a translated JSON Schema. Import behavior, dependency versions and agreement with an ordinary API call still require qualification. No scientific producer input has been evaluated by this script.

Review scope: fully reviewed router initialization, constants sections cited above, container PostgreSQL setup/run/shutdown, Viseron launcher and JSON storage helper; targeted relevant sections of build compose/template, original Dockerfile and webserver implementation. Large component/bootstrap/proxy files were acquired but are not claimed fully reviewed. Mathesar stays closed. Remaining tasks are source-to-image provenance, external-storage/default configuration mapping, candidate-order disposition and a complete bounded ordinary runtime recipe.
