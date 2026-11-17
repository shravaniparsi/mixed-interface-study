# Isolated framework runtime preparation v2

The v1 setup remains closed and failed. One new preparation attempt uses the same official Node22.22.3 darwin-arm64 archive and exact Angular22.2.3 lockfile dependencies. This is framework-level development, not execution of the PetClinic app (whose package.json requests Node24.x).

Extract only bin/node from the Node archive. Raise the per-file bound from64MiB to128MiB to permit a standalone runtime executable, while retaining512MiB total expanded and64MiB per download bounds. There is4.4GiB free space at registration. Skipping headers/npm reduces disk use; no npm or lifecycle script is needed. This change does not establish the cause of v1 failure.

Preserve verified download digests and sizes before extraction, member metadata and traceback on failure, and a final manifest. Use a fresh directory, no overwrite, no retry or fallback versions. At most10 packages from the prior frozen list, at most15minutes wall time, each network timeout45seconds. No paid calls, remote jobs, application services or framework measurements. The measurement runner and schedule must be frozen separately before executing Angular behavior.
