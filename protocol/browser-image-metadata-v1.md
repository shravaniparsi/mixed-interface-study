# Fixed browser image metadata check

Inspect only the official mcr.microsoft.com/playwright:v1.62.1-noble tag for the currently pinned Playwright1.62.1 runtime. This is deployment engineering, not application sampling. Maximum three sequential registry requests, each at most1MiB and30seconds, total90seconds, no retries or alternative tags/registries. Resolve the tag's OCI/Docker index to exactly one linux/amd64 image and retrieve its configuration if within this request count. Verify digest identities for every referenced object and retain the raw public metadata and failures. Do not download layers, install anything, run a container or dispatch an application experiment.

The output must identify the immutable image digest, architecture, declared layer bytes and image environment when available. A matching tag does not qualify Chromium version, Node version, installed Playwright package or operation in our isolated namespace. Those require a separately bounded smoke qualification before application use. No closed checkpoint attempt is reopened.

Official Playwright documentation states that its image includes browser binaries and system dependencies, while the npm package is installed separately and must match the image version: https://playwright.dev/docs/docker . This replaces neither runtime identity checks nor the existing full scientific objective.
