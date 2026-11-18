# Viseron persistence mapping after source wave 10

## Evidence and scope

Wave 10, frozen at 27cb9c9ee3398cce34c631fee9ff58e2bf1c05a6, collected all seven scheduled blobs (138,689 decoded bytes) without retry. Viseron has consumed 51 source slots and 434,013 bytes. The collection is closed. These are source observations, not runtime results. The fixed cohort still has two scope exclusions, one exhausted runtime qualification and nine pending workflow mappings; two application jobs and zero scientific cases.

Only public open-source systems will be used, following the user's explicit sandbox preference. No employer system or nonpublic workflow is needed.

## Confirmed storage contract

The original storage constants read POSTGRES_DATABASE_URL and default to postgresql://postgres@localhost/viseron. Plain PostgreSQL URLs are explicitly converted to the shipped psycopg2 driver. The SQLAlchemy engine requests UTC. This confirms the external-database path suggested by the original container initialization scripts; supplying that variable does not require an application patch (wave 10, file 3, lines 14–31).

Storage initialization checks database readiness, creates/stamps a fresh database or upgrades the Alembic revision, and performs startup chores. Those chores set missing end_time values on recordings and motion records. A restart therefore cannot be presumed state-neutral. The camera-free synthetic fixture must verify these tables are empty and compare database state before and after restart; do not exclude timestamps globally (file 1, lines 212–391).

The cleanup manager registers eleven midnight cron jobs with up to one hour of jitter. It does not run those jobs immediately in the inspected start method. Scheduling is not proof that jobs cannot affect a run: retain timestamps and database/filesystem comparisons, and reject unexplained drift (file 5, lines 936–1000).

The JSON encoder serializes datetimes to UTC ISO strings, enums to values and objects through as_dict. Snapshot the original authentication/onboarding/webserver files byte-for-byte while the application is stopped; parsing and rewriting them could change serialization. The webserver cookie secret and browser tokens must be preserved with the same actor (file 6 and prior wave 8 storage/auth sources).

## Restoration design to instantiate before any application run

Use the pinned Viseron image and a separate local PostgreSQL service. One candidate deployment uses the PostgreSQL binaries already shipped in that same image for the support service, recording their actual version; this avoids guessing the server major from the base distribution. No such service has been launched. Publish exact initialization, networking, stop/start and dump/restore commands before dispatch.

Stop Viseron and verify no application database sessions remain. Preserve the full mounted configuration tree, including .viseron authentication and webserver state, plus relevant local storage. Dump the full study database with the matching PostgreSQL tools and record schema, rows and sequences. Restore the database and files while Viseron is stopped, restart the original application, and compare relevant state again. Any generated differences require operation-specific prospective justification; none are presently authorized. Do not assume the earlier Mathesar checkpoint helper is compatible: its PostgreSQL version guard and schema assumptions are specific to Mathesar.

The packaged-source inspector is prepared for the registered runtime job. It checks acquired packaged Python/rootfs files against source hashes, records compiled frontend assets, verifies the declared revision and schema-validator version, and records the PostgreSQL client version. It does not establish compiled-frontend/source byte equivalence or ordinary workflow correctness. It has not run inside the image.

## Pending execution gates

Resolve and freeze candidate ordering, supported text input classes and ordinary values; finish the exact local-only deployment and checkpoint implementation; qualify ordinary native and API production, emitted update equality, warm continuation and both restored branches. No image was pulled locally and no new application job was dispatched in this mapping step. Original source files outside the explicitly inspected regions remain acquired exposure rather than fully reviewed code.
