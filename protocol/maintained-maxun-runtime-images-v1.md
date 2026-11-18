# Maxun build and persistence image metadata registration

Before any Maxun ordinary-control dispatch, resolve exactly these original-recipe/infrastructure tags in order: node:22, node:22-slim, node:22-alpine, postgres:13, minio/minio:latest. The first three are the already inspected Dockerfile FROM values; the last two are the original Compose persistence services. No alternate tags, repositories or platforms may replace an unavailable result.

Collect registry metadata only, with no layers, install, application start or experimental inputs. For each image permit at most eight requests, 30 seconds per request, two MiB per response and 240 elapsed seconds; the complete five-image collection shares 600 seconds. Run sequentially. Preserve failures; no retries or repeat collection. An initial anonymous 401 may be followed by the standard anonymous pull-token exchange and one authorized request. Tokens are never archived or printed.

Choose the lexicographically first exact linux/amd64 manifest descriptor without a variant, retain the index and descriptor, and verify downloaded manifest/config SHA256 values against descriptors. Verify config OS and architecture. Config blobs may follow at most two HTTPS redirects to docker.com, docker.io or cloudflarestorage.com and their subdomains, without forwarding authorization. Do not archive signed redirect URLs or stringify network exceptions. No other redirects are followed.

Publish this protocol and collector before collection, record their Git freeze, and verify working bytes against that freeze. Outputs are immutable per attempt. Record final platform digests and config metadata; base-image labels do not establish application-source provenance. Maxun application identity must still come from the registered exact-source build and resulting image IDs.

This metadata collection grants no additional ordinary job and does not authorize application execution. The existing two-job, 30-minute qualification limit and $100 ceiling remain unchanged. A separate full execution registration is still required.
