# Viseron checkpoint implementation contract v1

This freezes helper behavior before application outcomes. It is not an application dispatch registration: exact service/bootstrap commands, browser workflow, branch orchestration and runtime limits must still be published under the cohort qualification protocol. No scientific input has been executed.

## Deployment boundary

The proposed database service and application use the same already pinned Viseron image, config ID sha256:e7b2904341af931c754f815f865c799b0a0ee0a86f5aeff091de57d063e417e7. The database container is study-viseron-postgres, with Docker network mode none. The application is study-viseron and shares that network namespace. This supports loopback PostgreSQL, HTTP and WebSocket traffic without an external route. Browser and support-tool containment must be instantiated in the runtime recipe; a failed browser request alone will not prove network isolation. No application image modifications or package installations are part of the helper design.

## Database checkpoint

scripts/extension/viseron_postgres_checkpoint_v1.py requires the application stopped, database running, both image IDs matching, and the prescribed network modes. It accepts a successful packaged-source inspection report and compares the actual server version with the PostgreSQL client patch version in that pinned image. The client and server come from the same image; no major is inferred from the base OS. Unsupported version formats fail before mutation.

Only the postgres and viseron non-template databases are allowed. The helper rejects other active study-database sessions, large objects, materialized views and foreign tables. It fingerprints every user table, sequence, schema, role, role membership, database/role settings, tablespace and server setting; row values and credentials stay private. Full table rows are sorted only for order-independent comparison, with no field/value/timestamp exclusions. A custom-format full database dump is taken between matching fingerprints. Restore uses the existing database, --clean --if-exists --single-transaction --exit-on-error, followed by an exact fingerprint comparison. Unexpected extra objects therefore cause a mismatch rather than being ignored. Random paired pg_dump restrict/unrestrict transport tokens are removed from schema fingerprints; absent tokens are allowed for versions without that feature, malformed pairs fail.

This is adapted from the earlier Mathesar helper with Viseron-specific identity, database, role, version and network checks. The Mathesar helper never completed an application checkpoint roundtrip. Neither implementation is treated as runtime-qualified through code reuse.

## Configuration-volume checkpoint

scripts/extension/viseron_filesystem_checkpoint_v1.py runs only in a container with a mounted /state volume. Its caller must first prove the application is stopped and mount only that disposable application's configuration volume. Checkpoint and report paths must be disjoint from state and each other, canonical and free of symlinked ancestors. Capture refuses overwrite. Restore verifies both destination entry types and the complete private snapshot before deleting destination contents.

The helper copies all regular files and directories, including hidden authentication, onboarding and webserver-cookie-secret files. It preserves bytes, modes, owners/groups and nanosecond modification times. It rejects symlinks, hard-linked files, special files and extended attributes rather than silently losing unsupported metadata. Directory metadata is restored after children. Access times are not compared because inspection itself reads files; inode numbers and change times cannot be preserved by a file copy and are not claimed restored. No application JSON properties or persisted timestamps are excluded.

Public reports contain entry counts and aggregate state fingerprints only. Snapshot trees and manifests are private runner material and must not be uploaded. They contain authentication data even though the application fixture is synthetic. Retain private browser cookies/localStorage separately, and never publish them.

## Remaining runtime proof

Both helpers require an actual application qualification run. Restoring a stopped volume/database is necessary but insufficient: inspect post-startup database and configuration state, camera-free storage, same actor/token validity, emitted native request equality, warm continuation and both restored continuations. Do not infer process/cache equivalence from file hashes. Unexpected relevant drift fails qualification. No application-level snapshot success or scientific finding is claimed here.

## Development checks

Seven filesystem unit tests cover byte/metadata roundtrip after deletion/change/addition, tampered-checkpoint rejection before destination changes, symlink and hardlink rejection, overlapping paths, extended attributes and overwrite refusal. On local macOS Python the missing os.listxattr API is mocked to return no attributes only for temporary fixtures; the extended-attribute rejection test injects an attribute explicitly. Linux CI uses its real os.listxattr API for fixture inspections. These tests exercise temporary directories without Docker or an application. The PostgreSQL helper is syntax-checked only; SQL and container guards still require registered runtime execution.
