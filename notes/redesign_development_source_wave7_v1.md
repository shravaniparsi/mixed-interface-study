# Guardrail startup and schema mapping

Twenty files (764,977 bytes) acquired at published freeze 8c740aa2cc4a507dfc2f2f196fafc1a746f23790. No application or build has run. Hash verification covers original source acquisition.

The pinned original docs/openapi.json declares OpenAPI 3.0.0, 103 paths and 216 component schemas. It includes admin endpoints but no /admin/guardrails path. The schema comparison is unavailable in this artifact for the candidate operation; do not count this as a false negative or infer that every original schema source is absent. The separate plugin manifest is UI configuration, not this API contract.

header_edit uses pluginapi.ParseConfig, Lines and local header compilation. That shared parser is an outstanding original-source dependency. Startup delegates to internal/app, so read the initializer before asserting absence of external provider calls or background mutations. The acquired configuration provides STORAGE_TYPE/sqlite and SQLITE_PATH, PLUGINS_ENABLED, ADMIN_ENDPOINTS_ENABLED/UI_ENABLED, DASHBOARD_LIVE_LOGS_ENABLED and GOMODEL_VERSION_CHECK_ENABLED. Disabling the last is documented to stop version-check subsystem outbound traffic; it does not prove every subsystem is isolated.

Upstream CI uses pinned Node 22.23.2 and a pinned setup-go action; go.mod asks for Go 1.27.4. The actual frontend dependency lock and build/i18n config are retained. Use original frontend compilation, never frontend-stub. Toolchain availability and successful compilation remain untested.

The frozen repository tree contains 3,182 blobs totaling 40,947,087 declared bytes, exceeding the current 256-path/16-MiB review acquisition limit. A whole-source build cannot be smuggled through that limit as a clone. Before any build, publish an explicit development-only materialization amendment with full-tree identity checks and distinct bounded transfer/build limits, record the broader source exposure and preserve the existing reviewed-source accounting. No such transfer is authorized by this note.

Next scheduled dependency pass covers the original app initializers and shared parser. A build/ordinary qualification recipe will then need fixed flags, build provenance, network isolation, active preparation effort limits, run timeouts and full persistent/process/browser checkpoint scope. No altered inputs or evaluation source have been accessed.
