# CloudBeaver declared workflow image metadata

Inspect exactly ghcr.io/dbeaver/cloudbeaver:devel. This reference follows the
retained docker-build-and-push.yml repository/branch tag construction and the
frozen repository metadata's declared default branch, devel. It is not an
assertion that the tag was built from the frozen revision or even exists.

Publish this protocol and collector before requests. Permit one anonymous public
GHCR pull-token request, one tag manifest/index request, at most one linux/amd64
platform-manifest request and one config-blob request. No more than four
requests, 30 seconds each, 120 seconds total. Bounds: 64 KiB token response,
2 MiB tag index, 1 MiB platform manifest, 256 KiB config. No retries, alternative
tags/registries or platform substitutions; retain failures. Verify immutable
manifest/config hashes and inspect revision labels against the frozen source
907171c2f97377a9e2a9ec470d869124f084e5af. A matching label alone still requires
further provenance checks; absence or mismatch remains unqualified.

Do not save the token, print configuration environment or download image layers.
No image, application, dependency install or scientific input is executed. This
metadata route does not authorize guessing missing sibling source revisions.
