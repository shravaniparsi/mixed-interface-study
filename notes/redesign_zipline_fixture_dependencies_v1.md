# Zipline fixture dependency findings v1

Wave 16 at freeze 965e6b10e7d665e781f3661f3f2af83b29e59407 acquired and verified all 15 files, 39771 decoded bytes. Cumulative review is 150 paths and 863641 bytes. No runtime occurred.

Original DATABASE_URL supports PostgreSQL and an explicit pglite:///absolute/path form. The embedded implementation has version/pointer handling; do not invent an unsupported SQLite adapter. Original local datasource and database files are separate resources. A later runtime recipe must choose and freeze one supported storage configuration and capture all relevant state.

Initial maintenance can delete expired/max-used invites, expired files, orphaned thumbnails and max-view records. The latter has an original deleteOnMaxViews switch. An empty file/invite fixture and unused URLs are plausible ordinary conditions, but callback completion and state equality must be observed; absence of expected targets alone is not proof of no effect through imported helpers. Metrics/thumbnail feature flags and unset hook URLs must be confirmed in effective settings. Zero repeat intervals still permit initial runs.

The original workspace permits install builds for @parcel/watcher, argon2, esbuild and sharp, and ignores unrs-resolver. Preserve this policy and the original frozen lock. Native setup/login forms are now available for ordinary actor bootstrap; they do not themselves qualify URL continuation. The next bounded action is original build qualification, separately registered before implementation. This source review adds no scientific cases or defect findings.
