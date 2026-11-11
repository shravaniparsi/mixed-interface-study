# Vikunja instrument correction v2

Initial run 43086390320 on study commit 28cd67ca488a4749aeca51c450ae179589e41c64 failed both jobs during Go package setup. Both retained logs report frontend/embed.go:24:12: pattern all:dist: no matching files found. No TestStudyBulkPreservationV1 body executed; no scientific observations exist. Go 1.27.0 installation and source provenance checks succeeded.

The sole allowed correction creates frontend/dist/index.html with a marked backend-only build placeholder before Go compilation. This satisfies the upstream go:embed pattern. The frontend is not a tested channel. No production file, API/MCP path, fixture, observer, declared frame or control changes. The copied Go observer is byte-identical to v1. Both historical/fixed jobs use the same placeholder.

All v1 files and raw failure artifacts remain unchanged. Correction dispatch is v2, with the same two 15-minute jobs. No further attempt is authorized by this finite calibration if another incompatibility occurs. The initial workflow-indexing 404 created no run and is not a scientific attempt; only the actual two-job run is counted.
