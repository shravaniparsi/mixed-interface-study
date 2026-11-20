# Zipline runtime dependency findings v1

Wave 15 at freeze 3a6d6f3633000e62b4bc386f994777b64c5ffbc8 acquired and verified 20 files, 90273 decoded bytes. Cumulative Zipline accounting is 135 paths and 823870 bytes. No application or input ran.

Both original shortening webhooks have guards before network calls: HTTP returns when its onShorten URL is absent; Discord returns when its onShorten configuration or resolved webhook URL is absent, before its metrics lookup and send. The dispatcher invokes both asynchronously. A runtime recipe must verify actual effective configuration and isolate network access; source guards alone are not an observed guarantee of no external effect.

Original task startup always registers four maintenance callbacks and immediately runs each once; an interval of zero only prevents subsequent repeats. Metrics and thumbnail workers are conditional on feature flags. Consequently zero intervals do not qualify a quiescent start by themselves. The four callbacks require source review and observable completion/state gates. No blanket exception for task writes is granted.

The original database layer selects PostgreSQL or PGlite through connection helpers and applies original migrations at startup. Those helpers and initial callback bodies remain to be reviewed. Native bootstrap/authentication must finish before URL controls under a fixed principal. The original package requires Node >=24 and pins pnpm 11.28.8; original workspace install policy and full build output remain unqualified. The original tree has 737 blobs totaling 4408628 bytes; no full-tree build acquisition has yet been authorized.

All findings are source-level feasibility evidence. They neither qualify a causal checkpoint nor add a scientific case. Wave 16 is separately scheduled to resolve the exact remaining fixture dependencies rather than silently invoking them.
