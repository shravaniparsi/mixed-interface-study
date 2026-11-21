# Fresh-session feasibility build audit: preparation cycle 1

This is a development preflight, not an application pass. The old evaluation remains closed.

## Completed checks

The new standalone source verifier fetched all three pinned commits and compared each checkout against the frozen recursive tree, including content, size and executable mode. It reconstructed each root Git tree and compared it with the fetched commit's tree. Zipline: 737 files; Shlink backend: 788; official client: 175. The real-Git fixture tests reject modified content, executable-mode changes, extra files, symlinks, unsafe paths, duplicate entries and inconsistent subtrees. Receipts: `results/fresh-session-source-preflight-v1/`.

The cached Zipline ZIP was streamed without extraction. Both archive digests and all 64,235 inventory entries passed, including internal symbolic-link targets. This proves the retained bundle's identity, not fresh-session execution. No dependency installation or application startup occurred.

The four original Shlink Docker base tags answered manifest HEAD requests successfully. The recorded digests are availability observations; a build must record and verify the actual resolved materials. No layers were downloaded.

## Build chain and expected changes

Zipline's original package script calls `scripts/build.ts`, which uses `scripts/index.ts` and `scripts/lint.ts`: formatting check, oxlint, TypeScript, tsup, Vite client and two SSR builds. No `--skip` option is permitted. The verified bundle already contains the generated build outputs and package/lock/workspace identities. Reuse it. Original dependency install scripts permitted by the workspace include parcel watcher, argon2, esbuild and sharp; the runtime contains their built outputs. No replacement dependency installation is planned.

Shlink client: original Dockerfile invokes `npm ci`, then `node --run build`; the nested build performs TypeScript, Vite and `scripts/replace-version.mjs`. Vite emits the client and service worker into `build/`. The version script changes the generated index JavaScript when VERSION is set. These are generated-output changes, not permission to modify package.json or package-lock.json. Preserve both original and final manifests and resolved dependency inventories. The nginx stage copies the original nginx configuration, installs the original servers-from-environment entrypoint, and initializes servers.json. At startup that entrypoint writes the declared disposable server configuration. Treat servers.json as generated configuration containing a disposable API key; redact it before publishing evidence.

Shlink backend: original Dockerfile compiles extensions, resolves Composer production dependencies, removes `composer.*` and the Docker source directory, replaces the declared version placeholder, and downloads RoadRunner. There is no tracked composer.lock. Consequently a source commit alone does not identify the runtime. The packaging recipe must retain the resolved lock and installed package/source inventory before cleanup and retain the RoadRunner binary identity. Any observation-only modification to packaging commands must be declared and retained as an exact diff; no handler, validation, UI or persistence logic may change. A build that discards those observations cannot pass G3. Installed dependency source references used by the event, configuration and native-control audits must agree with the reviewed versions, or the gate remains unavailable.

Original backend bootstrap makes data/cache, data/locks, data/log, data/proxies and data/temp-geolite, reads supported environment settings, runs the original installer with database-cache clearing and an optional initial API key, and execs RoadRunner. These paths and generated database/configuration effects belong in the observer scope. RoadRunner has an in-memory jobs pipeline. Disabling pub/sub, Mercure, RabbitMQ, Matomo and GeoLite by supported settings is source-supported, but the installed dispatch library and effective configuration still need verification before declaring no background jobs. A quiet timer does not establish queue completion.

## Fresh-session adaptation requirements

The historical Zipline runner restores browser storage and contains nine producer inputs. It must not be dispatched or copied wholesale. The new runner must use the ordinary-only matrix and log in through the original native UI in a newly created browser context for each branch.

Zipline's original login calls saveSession with overwriteSessions=false. The source inserts one UserSession with a random ID and a creation timestamp; it does not overwrite all prior sessions. Authentication bookkeeping must be checked as a specific insertion tied to the same actor, with the remaining persistent state compared explicitly. Do not remove the entire session table from comparisons. Original middleware reads token/session identity and actor privileges; same actor is verified separately from session identity.

Shlink's official client delegates its forms to the locked web-component dependency. Its source-reviewed controls use the original URL and Title inputs and Save. The backend key, client key and persistent author-key relation must agree. Fresh client contexts intentionally begin without saved browser state; supported servers.json bootstraps the disposable server selection. No synthetic replacement editor is allowed.

## Remaining implementation, in order

1. Complete both deployment recipes and observers, with explicit expected bootstrap/authentication/background effects and retained dependency identities.
2. Implement fresh browser adapters and an independent scorer reading raw request/persistence evidence. Add corrupted-evidence fixtures for wrong record, missing persistence, duplicate writes and wrong edited fields.
3. Complete one integrated review of both systems. G1 and G2 stay pending until these requirements are satisfied; source verification alone does not close them.
4. Only then dispatch the bounded ordinary jobs. Keep any new Shlink runtime job-local to avoid paid large-artifact storage. Publish only sanitized, size-capped evidence with seven-day retention. Record elapsed runner time, including setup and failures.

The frozen matrix contains 24 Zipline branches and 12 Shlink branches: every selected target in all three repetitions, each with untouched and no-op-repair arms. Pair order is fixed by the published seed, and first-arm counts are balanced. Native creation and each field's valid replacement/reset checks are additional required controls. No invalid-input schedule is imported.

Preparation deadline remains 2026-11-23 03:23:28 UTC, 48 hours after first publication. At most two implementation/review cycles, five application-related jobs, 180 application runner minutes and one shared technical correction. No new paid spend is authorized. Failure to finish the required harness by that deadline is a preparation failure, not a reason to extend it or launch incomplete experiments.
