# Bounded original-source build component

The component is prepared but has not executed. It is not a separate build probe, extra application attempt or complete qualification registration. It may run only inside the future published 30-minute standard hosted qualification job, after the complete network, checkpoint, actor and ordinary-control recipe is instantiated. The original two-attempt project limit remains. A build failure consumes that qualification attempt; do not move it to an uncounted workflow or retry within the job.

## Bound and authorization

build_nginx_runtime_v1.py requires the public study repository's Linux GitHub Actions environment and a versioned registration with qualification_registered status, the frozen application revision, max_job_minutes=30 and the script's SHA256. It verifies that registration against the checked-out study commit and rejects tracked local edits. No complete registration exists yet. This is an execution guard, not evidence of runtime readiness.

All build commands share an 1080-second deadline. Individual commands additionally have recorded limits; none retries. The parent job must reserve time for browser provisioning, startup, ordinary warm/restored branches, evidence and cleanup within 30 minutes. Dedicated named build/inventory containers are removed on exit. A successful build does not qualify the workflow or increase the remaining runtime budget.

## Source and build commands

Fetch exactly application commit 20016b9d91d49c9133f1b4d26ab5a289c72ec1db without tags, check it out detached and compare its complete recursive Git tree against the retained metadata by path, mode, object type and object SHA. The retained tree response labels its root with the requested commit SHA, so that label is not assumed to be the actual root-tree object. Record the actual HEAD^{tree} separately. Verify all 97 acquired source files by byte count and SHA256. Require tracked source to remain unchanged after frontend building; generated untracked locale/dist assets are retained as build outputs. No issue, fix or upstream test is run to choose inputs.

Pull the two previously recorded linux/amd64 base manifests and verify their config IDs. Use the original frontend builder base, CI=true and NODE_OPTIONS=--openssl-legacy-provider for the build container only. Run yarn install --frozen-lockfile, yarn locale-compile and yarn build. Do not run upstream tests or substitute a compiler. This builder environment is not propagated to the application. Build the generated, hash-verified production Dockerfile with BUILD_VERSION=2.0.0, the full frozen BUILD_COMMIT and fixed BUILD_DATE=2026-11-18T00:00:00Z. The four already registered packaging changes remain the only Dockerfile changes.

Record resulting image identity, original lock identities, installed package versions and complete file/symlink inventories for frontend build artifacts/dependencies and the installed /app tree. The inventory has 100,000-entry and 2-GiB file-byte bounds and runs with networking disabled and an overridden entrypoint, without importing or starting the application. Verify actual humps/Formik and Ajv/ref-parser/better-sqlite3/Knex/Objection versions. Record Node, Yarn and dpkg package identities. Full file inventories retain installed dependency content hashes; this remains a recorded build, not a claim of independently reproducible apt/package availability.

Command exit codes, elapsed times, exact arguments and log hashes/byte counts are written incrementally. Preserve a failed build and its last completed stage. Raw build evidence stays private until the parent workflow deliberately selects public artifacts; this component neither logs into Docker Hub nor reads or prints credentials. No container application entrypoint, API request or schema input is executed here.

## Validation scope

Five local fixture tests check exact Git-tree/source acceptance and rejection of wrong revisions, missing tree entries, altered modes/object IDs and modified acquired working files. Node/Python syntax checks pass. They do not test network fetching, Docker, dependency installation, production compilation, installed artifact inventory or application runtime. Those remain gates of the bounded qualification attempt.
