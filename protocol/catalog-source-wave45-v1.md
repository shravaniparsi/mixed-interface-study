# Source wave 45: OpenELIS original database initialization

Acquire five scheduled configuration/entrypoint blobs at the frozen OpenELIS
revision. The retained database Dockerfile copies dbInit, including an SQL seed
whose declared 863,876 bytes exceed the source-file cap. Do not fetch, split,
partially read or substitute that seed. Inspect the original Liquibase wiring,
base changelog, database settings and collation wrapper to determine whether
another source-supported fresh-database path exists and what it requires.
Do not assume that skipping the seed preserves a supported deployment.

Bind all forty-four prior source ledgers. Preserve 256 source slots/8 MiB per
project, 256 KiB per decoded file, 512 KiB per response, one 30-second request per
scheduled blob, no retry and no alternate reference. No database, SQL, migration,
application, dependency installation or clinical fixture is executed.
