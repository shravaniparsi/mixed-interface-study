# Zipline fixture-dependency source review v1

Wave 15 established that the original shortening hooks return before sending when webhook URLs are absent. It also established that interval jobs run once at startup even at zero repeat interval. Wave 16 therefore acquires exactly the 15 manifest files: database connection/embedded selection and relation/migration context, local datasource classes, four always-registered maintenance callbacks, server listen behavior, native bootstrap/login forms and the original pnpm workspace install policy.

Resolve the actual initial-job effects on an empty local fixture and on unused URL records before declaring any checkpoint scope. Do not patch task scheduling, suppress validators or assume zero interval prevents the first run. Only original supported configuration may be used. PostgreSQL/embedded storage selection is not fixed by this source wave. Likewise, initial bootstrap is a fixture step distinct from scientific same-actor URL creation/editing, and must finish before those controls.

Apply existing source budget, wave-15 cumulative accounting, exact original revision/blob hashes, one request per file, 30-second timeout and no retry/substitute. No build, install, runtime or scientific input is authorized. Build preparation and any full-tree materialization require an explicit prospective allocation. No evaluation source is acquired.
