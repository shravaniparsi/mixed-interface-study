# TestPlanIt instrument correction v2

The single correction allowed by v1 is consumed by this workflow. First run 43090047548 at b9c9f36 installed dependencies, migrated/seeded PostgreSQL, created the synthetic API credential, and served the authenticated model read with HTTP 200. It stopped at the read-only warm-up GET to the version endpoint, which returned HTTP 405. The pinned route exports POST only. No scientific mutation or observer case executed. The archived first attempt and its zero-observation reconstruction are retained.

Correction: accept HTTP 405 only for the GET warm-up of the /versions route, as evidence that this POST-only route compiled. The real model read still requires HTTP success. The warm-up is not a scientific readback, an authorization proof for POST, or a successful mutation. The actual tool still POSTs to the real route; its response, persisted versions and raw database snapshots remain subject to the original checks. Any other HTTP error fails readiness immediately.

The observer, fixture, eight cases, source/dependency pins, field contracts and baselines are unchanged. A new workflow retains the old workflow byte-for-byte. No further application attempt is authorized by this bounded protocol after v2. Runtime or fixture failures are retained as exclusions instead of additional correction cycles.

Source: https://github.com/TestPlanIt/testplanit/blob/294b646af84ca8a7543fa37366e0b84437cd5c4a/testplanit/app/api/repository/cases/%5BcaseId%5D/versions/route.ts .
