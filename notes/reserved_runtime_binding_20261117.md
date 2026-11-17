# Second dependency frontier: runtime and HTTP bindings

Freeze 37abdaeba5409c817c48976f0f6a810e512418d0 preceded retrieval. All 26 scheduled files matched pinned blob identities. Cumulative additional-source use is 13 files for Booklore, five for book-social-network, six for Restaurant-App, seven for Celerio and eleven for Kanban; all remain within 24 per project. No app execution or experimental outcome was observed.

Reviewed Booklore controller confirms collection GET/POST and item PUT under /api/v1/admin/oidc-group-mappings, protected by the application's admin predicate. A local admin setup and whether the configuration UI needs a live OIDC provider remain unqualified. Controller presence alone does not establish an operable workflow.

Reviewed Restaurant BaseService confirms JSON POST to the category base URL, PUT and GET by ID, with the supplied authorization header. Its development environment names local API and identity endpoints at ports 5000 and 5100. Native category actor/runtime still need binding.

Reviewed Kanban Dockerfiles specify Maven/JDK 8, Node 12.7, an Angular production build and nginx; compose specifies PostgreSQL 9.6. These are source-declared tags, not immutable image identities. The backend properties set context-path /api; the development frontend points to localhost:8080 without that prefix. The build uses --prod, so environment.prod.ts and angular build replacement/proxy settings must be inspected before concluding a mismatch or changing configuration. Original Springfox 2.9.2 suggests Swagger 2 may be emitted; schema dialect support must be established rather than treating a missing OpenAPI 3 baseline as method success. Task serializer's TODO assignment remains part of the equivalence requirements.

Celerio runtime properties use Maven-filtered database settings and an H2 demo profile. Its Dockerfile expects a prebuilt JAR plus database file. No old floating Docker tag is accepted as proof that it represents the selected commit. Build packaging and source-matched artifacts remain to be established.

This is partial source review, not final admission or complete inspection of every collected file. The remaining ordinary-control adapters and project-specific execution freezes are still required. No scientific case or independent defect is credited.
