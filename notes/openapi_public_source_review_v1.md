# OpenAPI public frame source review

## First structural batch

All 14 frozen blobs verified. Faster Chat's seven entry/package files were read fully. Frontend App delegates routing and theme state to local modules; index.js starts the server without awaiting models.dev cache initialization and catches its rejected promise. That does not prove the cache implementation cannot block, retry or write state; its implementation is scheduled. init.js restores server/.env from data/.env, creates a key if absent and copies it back to data/.env. This is source evidence of persistence behavior, not successful restoration. No secret value was created or read.

The Faster Chat import/dependency/script ledger records local, external, already-collected and excluded references from the reviewed roots. Local imports and the shared workspace manifest were added before sealing the first batch. The next depth-one batch contains router, theme store, shared package, backend app and modelsdev. Styling is explicitly excluded; theme storage is retained because browser-state equality matters. No runtime, schema variant or provider request occurred.

Bichon's six nongenerated roots were read fully. Cargo specifies a workspace; the Dockerfile packages precompiled architecture-specific server/admin/CLI binaries rather than compiling them, so the image recipe alone cannot establish source correspondence. Server startup initializes data directories, users, context, blob/envelope/attachment managers; it starts periodic tasks and export cleanup, conditionally starts SMTP, then starts HTTP. Shutdown includes those managers and database flush. Exact state locations and quiescence remain unresolved.

Bichon source explicitly describes historical migration and search-index issues. These are incidental prior exposure, not observed defects or candidate cases. Frontend main.tsx handles auth failures through the auth store, supports a Pro SSO callback and instantiates the router with generated routeTree. Query behavior includes production retries/focus refetch, which must remain visible in native control evidence. Generated routeTree has not yet been fully reviewed or inventoried for discovery. Bichon's first batch remains unsealed; it cannot advance to another batch until its complete root import ledger is recorded.

No workflow selected, no application runs, no independent-family certification and no scientific cases. Two engineering candidates cannot by themselves satisfy the previous four-family descriptive threshold.

## Faster Chat second batch

All five files in wave 2 were collected once after published freeze 2e1b4eb2fbfa0d1b99809360bf49e44b16d837ad and read fully. The router establishes /, /admin, /chat/$chatId, /folder/$folderId, /gallery, /import, /invite/$token, /login and /settings. ProtectedLayout calls checkSession and renders a shared sidebar. The earliest root route delegates to IndexRouteGuard; it must be resolved before treating /admin as the first eligible resource. No route is yet a selected workflow.

Backend app.js mounts auth, admin, provider, model, file, chat, settings, version, image, import, folder and memory routers. It installs body-limit, security headers, error handling and CORS. Production allowed origin comes from APP_URL; this configuration must be preserved rather than bypassed to make API/native controls pass. Mounted routers are eager imports, so their startup dependencies cannot simply be assumed irrelevant.

modelsdev.js stores its cache and timestamp in module memory. Failed initialization schedules up to five delayed retries (starting at 30 seconds with exponential delay); an interval refresh also runs. Request timeout and interval values come from the shared package. This source evidence refines the earlier nonblocking-start observation: startup tolerance does not establish a quiescent snapshot or absence of further network attempts. No request to models.dev was made by this study. Native theme state uses persist with theme-store-v3 and six selected browser preferences; theme JSON is fetched as a local asset. Browser-state restoration must include that store.

The complete reviewed import ledger includes static and literal dynamic route imports and the shared package export. All local bindings in this batch were queued; no resource was chosen for likely discrepancies. Wave 3 prospectively schedules the 27 depth-two files in lexical order, taking Faster Chat to 39 scheduled files of its 96-file cap. Bichon's original batch remains unsealed. No application job, experimental input or qualified comparison occurred.

## Faster Chat third batch: collection and initial review

All 27 frozen files were collected once after verifying remote main at d21cdec38656eff1f826a050e9e4fe2153707823 and local schedule equality with that commit. Every file matched its scheduled byte length and Git blob hash. The collection manifest records SHA256 hashes and cumulative byte accounting; the observed queue remains unsealed. No failed requests or replacements occurred.

Full content review so far covers wave-3 indices 1, 2, 5, 12, 13, 16 and 17 only: IndexRouteGuard, MainLayout, Admin, useAuthState, shared index, admin router and auth router. The remaining 20 files and complete import-disposition ledger are pending. No next batch is authorized by this partial review.

The root route is a state-changing navigation gate, not a form: a first administrator with no chats and unseen onboarding is directed to /admin?tab=connections after marking onboarding seen. Otherwise it navigates to an existing chat or invokes chat creation with an empty object. The onboarding helper and chat hooks remain unresolved dependencies. This matters for baseline state and makes treating the initial page load as inert incorrect; it is not a validation defect. MainLayout also renders UpdateBanner, whose behavior remains unresolved.

/admin gates on administrator role and renders Users, Customize, Models and Connections lazy-loaded tabs. The users API creates username/password/role and exposes role and password updates; these fields do not establish the required pair of nonsecret, nonidentity text properties. No other admin tab has yet been resolved, so neither /admin nor the downstream chat route is selected or excluded as a whole.

The auth router supports local first-user registration as administrator, then requires an invite for later registration. It uses session cookies (secure in production), rate-limit storage, password hashing, audit logs and last-active updates. The frontend auth store delegates to authClient and clears the query cache on logout. Native setup UI, database implementation, session middleware and actual runtime behavior remain unresolved. A possible local setup route is source evidence only, not a successful login.

The shared index re-exports constants, types, data and utility modules. Their relevance must be inventoried before queue discovery is sealed; no implicit completeness is claimed. No runtime, external model call, experimental input or qualified scientific case occurred.
