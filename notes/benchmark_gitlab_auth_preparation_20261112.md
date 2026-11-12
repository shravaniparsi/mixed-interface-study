# GitLab authentication preparation

The preceding goal turn made progress: 24 input specifications were frozen at be184b31, and startup qualification was registered at 15ab5131. Unit run 43168206243 passed. Startup run 43168226517 was live during authentication preparation; do not restart it based on an observation timeout.

Four runtime source files were retrieved from WebArena-Verified commit 6473f72db5dcefc97b5725b59e734504edc28a21 and verified against its archived Git tree. Paths and hashes are in evidence/benchmark-gitlab-runtime-source-v1.json. These are environment operations, the login fixture, basic HTTP tests and the entrypoint, not task evaluators. Raw sources remain local and ignored. Automatic approval review rejected publishing the credential-bearing fixture. The revised publication contains only source identities and a probe that fetches the pinned public fixture into memory, checks its hash and neither saves nor logs credentials.

GitLab 15.7.5's extracted API index, lines 203–211, documents session-cookie API authentication. The prepared probe logs in through the native form, verifies /api/v4/user and queries narrow project/user candidates. Application requests and redirects are restricted to the local disposable port; fetching the known public fixture is a separate HTTPS metadata operation. The evidence excludes passwords, cookies and CSRF tokens. Login may update session metadata; the probe performs no business-object writes. Syntax is checked; runtime behavior remains unqualified.

The benchmark entrypoint starts services without reconfiguration for the default URL. Its health implementation includes database, Redis and login-redirect checks. Our frozen startup probe is narrower: HTTP 200 and GitLab OK from /-/health. Passing it does not establish successful database, authentication or workflow qualification.

Next archive startup results and job time, then register bounded authentication qualification if startup succeeds. Current repository identification for the MR task, external README content, reset and native browser controls remain unresolved. No scientific execution is authorized by this preparation.
