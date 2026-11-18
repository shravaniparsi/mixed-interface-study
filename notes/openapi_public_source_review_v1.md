# OpenAPI public frame source review

## First structural batch

All 14 frozen blobs verified. Faster Chat's seven entry/package files were read fully. Frontend App delegates routing and theme state to local modules; index.js starts the server without awaiting models.dev cache initialization and catches its rejected promise. That does not prove the cache implementation cannot block, retry or write state; its implementation is scheduled. init.js restores server/.env from data/.env, creates a key if absent and copies it back to data/.env. This is source evidence of persistence behavior, not successful restoration. No secret value was created or read.

The Faster Chat import/dependency/script ledger records local, external, already-collected and excluded references from the reviewed roots. Local imports and the shared workspace manifest were added before sealing the first batch. The next depth-one batch contains router, theme store, shared package, backend app and modelsdev. Styling is explicitly excluded; theme storage is retained because browser-state equality matters. No runtime, schema variant or provider request occurred.

Bichon's six nongenerated roots were read fully. Cargo specifies a workspace; the Dockerfile packages precompiled architecture-specific server/admin/CLI binaries rather than compiling them, so the image recipe alone cannot establish source correspondence. Server startup initializes data directories, users, context, blob/envelope/attachment managers; it starts periodic tasks and export cleanup, conditionally starts SMTP, then starts HTTP. Shutdown includes those managers and database flush. Exact state locations and quiescence remain unresolved.

Bichon source explicitly describes historical migration and search-index issues. These are incidental prior exposure, not observed defects or candidate cases. Frontend main.tsx handles auth failures through the auth store, supports a Pro SSO callback and instantiates the router with generated routeTree. Query behavior includes production retries/focus refetch, which must remain visible in native control evidence. Generated routeTree has not yet been fully reviewed or inventoried for discovery. Bichon's first batch remains unsealed; it cannot advance to another batch until its complete root import ledger is recorded.

No workflow selected, no application runs, no independent-family certification and no scientific cases. Two engineering candidates cannot by themselves satisfy the previous four-family descriptive threshold.
