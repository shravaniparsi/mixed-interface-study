# OpenELIS session and startup mapping, wave 16

Seven original files were scheduled and published at 804f5d21caff9c19f4d4a5a33d87113c7161b1a0 before acquisition. All seven verified, adding 42,663 bytes. Cumulative OpenELIS acquisition is 61 slots and 863,258 bytes. No application ran and no scientific case was executed.

## Authentication and session

The original frontend config uses /api/OpenELIS-Global as serverBaseUrl. Previously acquired App.jsx lines 305–311 request /session and store jsonResp.csrf in localStorage CSRF when authenticated. UserSession exposes getCSRF; the frontend establishes the consumed lowercase field spelling, which still requires runtime observation. The native-login helper has not yet qualified frontend token readiness or administrator role.

UserSessionData implements Serializable and holds scalar identity, timeout, administrator and lab-unit fields. This establishes serializability for that value only, not every session attribute or successful Tomcat persistence. Both packaged and compose-mounted server configurations declare the OpenELIS context and disable automatic deployment; neither contains an explicit Manager declaration. Server session restoration remains unqualified.

CreateAdminUserTask runs at PostConstruct in daemon context. It creates an administrator only if neither default nor nondefault administrator exists. It reads the original initial-password file property, bounds file size at 256 bytes and password UTF-8 length at 72 bytes, applies the configured password validator, hashes the password and inserts the user with a five-year expiry. This maps the environment-backed secret-file consumer identified in the original entrypoint. The exact default username constant and effective configured password policy remain to be resolved before provisioning. No checked-in credential was fetched or displayed.

## Startup persistence is material

FhirFacilityOrganizationServiceImpl initializes on ContextRefreshedEvent and also lazily from facility getters when its cached organization is absent. Initialization resolves the facility, reuses an existing UUID or generates one, builds a resource, invokes local/remote FHIR synchronization, and calls syncToOpenElisDb through the daemon executor. That method sets facility organization properties, calls organizationService.save and thisLaboratoryService.record. Thus the inspected transformation dependency is not transitively read-only, and disabling the FHIR store does not remove this database write.

Local synchronization skips a blank local store URI. Remote synchronization skips a null/empty list and individual blank entries. A future isolated deployment must verify effective configuration and enforce its local-only network boundary. A database restore followed by application restart is not presumed to reproduce the warm starting state: facility writes, their audit/version consequences, caches and session state need an explicit supported recipe and ordinary comparisons. No broad timestamp or facility-row exclusion has been admitted. The inspected code is evidence of operations, not evidence that a runtime mismatch has occurred.

The packaged server XML contains an incidental source comment about duplicate deployment/imports/jobs. It was retained; no issue or fix was followed. The oversized SQL seed remains outside the source cap and its contents unresolved. No claim of synthetic-only initialized tables is made. Image provenance, fixture scope, full state restoration and runtime controls remain prerequisites. This is source mapping, not a defect finding or Q1 evidence.

Review scope: complete config, session bean, session-held value and administrator task; targeted facility getters, sync methods and initialize path; server deployment/context sections. Uninspected sections are not represented as fully audited.
