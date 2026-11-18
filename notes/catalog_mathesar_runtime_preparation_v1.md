# Mathesar runtime preparation

User confirmed public open-source systems only; no organizational sandbox is available. Continue the existing twelve-project cohort and its caps, without replacing failures.

Image metadata procedure was published at 7fd8c98a11dec63aebf518669d7d05eb3a85a453 before execution. Both images completed four requests and verified child/config SHA256 identities. No layers were downloaded and no local application started.

- Python 3.14-bookworm linux/amd64 manifest: sha256:cf063ce98ede9b3e88127463b3fa6d1c46d0f85a548345b148e50eaaad36ef86; config sha256:fe7476d53d1226869cb4375bafeff56932c34713cf6048b6325b1c5248b2d648.
- PostgreSQL 17.12-bookworm linux/amd64 manifest: sha256:99d1a998c76487d3abb48b141505bda5dcf8089c0c4cd7be40f75de314fa32f0; config sha256:431b070f8300b219ab7e6597e7ebb158df31767739896f53a936cfc749d8437a.

The checkpoint implementation and protocol now specify stopped-app capture, in-place atomic restore, complete persisted-row hashing, sequence/schema/global checks and unsupported-state failures. Syntax and preparation-hash checks pass. No live PostgreSQL roundtrip has been attempted; this helper is unqualified until exercised within the first ordinary application job.

Five terminal source/helper CI runs succeeded; timing is retained in manifests/catalog-runtime-preparation-ci-accounting-v1.json. These are not application experiments or scientific cases. Catalog application jobs and scientific cases remain zero.

Next implementation work: finish candidate route-order justification and original-schema disposition, instantiate source checkout/build provenance using the original minimal Dockerfile target and pinned Python base, and implement the native bootstrap/create/edit harness plus warm and restored branch orchestration. Use the pinned browser image from development qualification. Publish the complete workflow before its first <=30-minute ordinary job. Building is part of that job's limit. Do not spend the limited application attempts on an incomplete harness. No new user permission is needed for this authorized public/free-runner work.
