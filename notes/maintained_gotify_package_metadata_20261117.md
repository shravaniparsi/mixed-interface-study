# Gotify bounded package metadata outcome

The protocol was published at 5c230a550222c1a98775b0bd766dfd613291d7bd before inspection. Exactly five requests were made: anonymous tag (401), anonymous pull token (200, secret body not retained), authenticated tag, linux/amd64 child manifest, and config blob. The last request returned 307; redirects were not followed and the five-request allowance was exhausted. No retry or alternate tag/registry was attempted.

The platform manifest digest is sha256:423faf995a675d5af83b80667c21186d86d33490d199cb5f07c857977b3e3ea3. The child descriptor hash was verified. Configuration bytes and revision labels remain unavailable; this is not evidence of a matching or mismatching image revision. No layers were downloaded or applications started. All non-token response bodies and their hashes are preserved. Token values and authorization headers are not archived.

A source-build path must be registered separately within the existing two-job qualification allowance. The next source schedule uses Gotify's final permitted dependency slot for ui/package.json, required by the already-read Dockerfile/Makefile native UI build path. Its cumulative count reaches 24/24; there is no additional source allowance. Any unresolved dependency beyond that bound stays unavailable. The selected application workflow and fixed inputs are unchanged.
