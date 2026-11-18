# Application initialization mapping and build attempt

Thirteen frozen initialization/parser files acquired under 6eeac0ea3385d51b296d8666f27c218b001b18e1. All retained blob/envelope hashes verify offline. No application or workflow producer has run.

Original initialization provides GOMODEL_OFFLINE, which disables its own update check, remote model catalog and metadata-only listing while leaving configured external endpoints usable. A future runtime recipe therefore needs both offline configuration and no external providers, OTLP, MCP upstreams or vector stores; offline alone is not an egress firewall.

Initialization constructs shared storage, provider/catalog services, tracking, file/media stores, guardrails, workflows, managed keys, admin handlers, cluster synchronization and response caching. Guardrail saves notify revision state; workflows and guardrails are refreshed together. Startup also seeds the default workflow from configuration. Checkpoint qualification must compare the full relevant database, files, original API views and actor/browser state after restart, including revision/default-workflow effects; merely restoring the guardrail row is insufficient. Ordinary warm/restored comparisons remain mandatory.

The original plugin parser is now available for the prospective source-aware comparison. No replay prediction, success metric, mutation target or repair outcome is inferred from reading it. Further dependency review and executable runtime qualification remain required.

One separately registered build-only attempt was dispatched as GitHub run 44400417320 at freeze 6eeac0ea3385d51b296d8666f27c218b001b18e1. It explicitly permits a bounded full-tree materialization and original real frontend/binary build; it does not authorize application startup. Its terminal outcome must be collected from GitHub, not inferred from dispatch or this note. No retry is authorized by that registration.
