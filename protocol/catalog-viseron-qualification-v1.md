# Viseron original ordinary qualification attempt 1

This prospectively instantiates one qualification job under catalog-application-qualification-v1.md, using catalog-viseron-ordinary-recipe-v1.md and the frozen five-case schedule. Only ordinary controls execute here. Maximum two qualification jobs for this selected project remains unchanged: this job plus at most one narrowly registered infrastructure/instrument correction. No alternate workflow, scientific mutation, retry, or outcome-driven variant is authorized by this registration.

## Executable and tooling

Workflow .github/workflows/catalog_viseron_ordinary_v1.yml runs on standard public ubuntu-24.04 with a 30-minute job cap. Application image is roflcoopter/amd64-viseron@sha256:91c9ffb15859ce05b62792acfacec61c6eaf0de14f9fbe88780c5a8aee2d9a43, config sha256:e7b2904341af931c754f815f865c799b0a0ee0a86f5aeff091de57d063e417e7. Prior metadata ties its declared full commit to the frozen source and original build pipeline. Inspect previously acquired packaged backend/rootfs source hashes and compiled asset inventory before app startup. Compiled frontend/source byte equivalence is not claimed; ordinary emitted controls must agree with the acquired frontend contract. Any source mismatch fails the attempt.

Use the frozen Playwright image sha256:c091b21d9fae78c76e85cd4356431e9b018402f172a214fc7d7a5e9a7e29d8ac, config sha256:fee853fafa59550d162cef52bca02d907694b44ebf6ef9fb075bcc0c65d8dedb, Node 20.20.2, Playwright 1.62.1 and Chromium 151.0.7922.34, with the existing lock and explicit executable hash. No package upgrade or browser fallback. Dependencies/images are provisioned once before isolation: 90-second npm cap and 180 seconds per image pull, no retries. DockerHub secrets are used only by docker login. No local image pull or application execution.

## Services and isolation

qualify_viseron_ordinary_v1.py contains exact commands. PostgreSQL uses the original image's installed binaries, discovered from psql's reported major, and runs as its postgres OS user. Initialize a fresh cluster with local/host trust only within Docker network none, listen on loopback, create database viseron, and record/verify the server patch version against the same pinned-image package report. There are no published host ports. The support service entrypoint starts only PostgreSQL; the application retains the original image /init entrypoint and unmodified application files.

The application shares the database's isolated network namespace, uses its supported POSTGRES_DATABASE_URL=postgresql://postgres@127.0.0.1/viseron and TZ=UTC, and mounts the disposable named config volume. Its original configuration is webserver with auth enabled via an empty auth mapping; no camera/hardware/inference configuration is provided. Browser runs in that same isolated namespace, at http://127.0.0.1:8888 using the original nginx entry point. Verify actual container network modes, image IDs and absence of published ports, not just requested command flags.

Local HTTP and WebSocket use is expected. Record external browser request attempts as hashed URLs but do not use unresolved request events as evidence of network escape or qualification failure. Kernel/container isolation is the criterion; this is explicitly different from the earlier closed Mathesar request-terminal-state gate. Do not reopen Mathesar. Page errors and token refreshes invalidate the ordinary phase. No third-party application-side connection is allowed. Package provisioning before app startup is separately recorded and is not an application workflow side effect.

## Fixed phase sequence

The original-runtime envelope is 1200 seconds; database readiness 45 seconds, app readiness 90 seconds, each browser phase 150 seconds. Readiness checks poll only their existing service, not recreate or restart it after timeout. The workflow adds a 1230-second outer runtime timeout within its job cap.

1. Native producer: fresh services, original UI onboarding, ordinary native Add User, exact emitted create-body match, full persisted readback by stable ID, stopped-state inspection.
2. Warm control: fresh services, original UI onboarding, ordinary API create, native edit before any app restart, exact emitted update equality and complete readback, stopped-state inspection.
3. Seed: fresh services, original UI onboarding, ordinary API create, save private actor/browser/target state, stop app, capture database and configuration-volume checkpoints.
4. Native restored branch: restore both checkpoints while app is stopped, start original app, verify same seeded actor and target, perform original native edit, stop app and inspect complete persisted state.
5. API restored branch: restore the identical checkpoints, start original app, verify same seeded actor and target, execute the full materialized update using the preserved browser auth context, stop app and inspect complete persisted state.

Use the originally frozen display-name edit. Readback verifies all seven target fields and unchanged unrelated properties. Check exact HTTP method, path, body and all observed request headers across the restored pair; hash authorization/cookie/XSRF values in the public representation, preserve raw envelopes only privately. Different missing headers remain differences. Do not silently relax mismatches. The ordinary schema helper evaluates only the ordinary body; it must accept without changing that body and agree with successful actual creation.

Independent producer/warm/seed installations generate different UUIDs and salted credentials. Keep those in evidence, compare complete target/actor semantics other than generated UUID, and compare the exact ordinary update body. Do not claim identical independent-installation full state. The restored pair must share exact seed identity and full relevant persistence state. Warm semantic agreement is not a substitute for matched restored state or a proof of general process/cache equivalence.

## State and operation-specific differences

Use the published database and filesystem helpers. Capture/restore has no filesystem metadata exclusions. Both branches must have identical restored database fingerprints and complete restored filesystem fingerprints. Both post-continuation database states must match. Original startup chores can modify open motion/recording end times: require both public.motion and public.recordings to be empty at every stopped-state inspection. Confirm /tmp/downloads and /config/public_images contain no files after each browser phase.

For post-operation configuration comparison only, preserve and report these differences rather than equating them:
- The exact file viseron.log may differ in bytes/hash/mtime because it is the original diagnostic log (source wave 9 constants, VISERON_LOG_PATH). Keep mode, owner, presence and type checks. No other log file or rotation pattern is exempted.
- .viseron/auth file mtime and .viseron directory mtime can differ because original Storage.save writes a temporary file and atomically replaces the auth file (source wave 8 Storage). Require identical auth bytes/hash, size, permissions, ownership and all other entry metadata.

Every other file/property remains in comparison. No persisted application timestamp or JSON field is removed. Unexpected extra files, rotated logs or metadata differences fail the qualification instead of being added to the exception list after outcomes. Filesystem inventories publish hashes and metadata, not file contents. These specific post-operation rules are now frozen before runtime; they do not weaken exact snapshot restoration.

## Evidence, validation and disposition

Public evidence includes image/package checks, schema result, phase reports, hashed request secrets, containment checks, full table/sequence fingerprints, hashed configuration inventories, command exit statuses, readiness results and terminal outcome. Raw logs, auth stores, database dumps, browser storage and request headers remain in a private runner directory excluded from upload. Errors retain their stage/type and message hash; raw errors stay private. No raw credential or token may be published for diagnosis. verify_viseron_ordinary_v1.py reconstructs comparisons from retained public evidence; green CI alone is insufficient.

Local pre-dispatch checks: Python compilation, JavaScript syntax, Ruby standard-library YAML parse, seven filesystem helper tests (the macOS xattr caveat remains) and four state-comparison tests. The seven filesystem tests also passed native Linux in CI 44278143401. These checks do not qualify the application. Publish this protocol, workflow and all scripts before dispatch; retain the commit and run ID. Preserve all failures and costs. Ordinary qualification contributes zero scientific cases; only a later explicitly registered scientific execution can use the frozen inputs.
