# OpenELIS empty-store binding and deployment state

Wave 14 was frozen at 7a2556f2401d355a769bc10c6e9b84a8fd851b16 before eight source requests. All verified, adding 32,058 bytes; OpenELIS now has 43 acquired slots and 717,776 decoded bytes. No application, image pull or dependency installation executed.

## Original configuration branch

FhirConfig binds localFhirStorePath with @Value("${org.openelisglobal.fhirstore.uri:}") and a Lombok getter. The fallback is empty. Together with the previously inspected nonblank-client initialization and noStore guard, this establishes a source-supported empty-store path. A future runtime must explicitly provide an empty effective property and verify it overrides the public template's nonempty value. It must also keep remote integrations empty/isolated. This is a configuration-specific study scope; it cannot support claims about FHIR-enabled deployments.

The outbound transformToFhirOrganization method is annotated readOnly and constructs a FHIR Organization, copies the version/name/active state, reads identifiers and organization types, and adds a parent reference where present. transformToFhirLocation constructs a Location with the existing FHIR UUID and organization reference. These inspected methods have no direct organization save/insert/update call. They invoke common reference/facility-identifier helpers, which remain to be mapped; readOnly annotations are not proof that every transitive operation is side-effect free. The asynchronous caller still requires a completion/consistency observation before snapshots. Do not interpret the empty persistence response as a completed asynchronous transformation.

## Original build and startup

The frontend Dockerfile builds the frozen source with node:20.20-alpine, npm ci --legacy-peer-deps and npm run build, then serves dist through nginx:1.27-alpine. It copies a workspace packages directory and the original package lock. The database Dockerfile uses postgres:14.24-bookworm, original dbInit scripts/SQL and its collation entrypoint. The separate proxy Dockerfile uses nginx:1.15-alpine. These are source tag declarations, not resolved digests or verified image availability. No source-to-published-binary equivalence is inferred from them.

The backend entrypoint reads a database password file when present, copies an initial-admin secret into a private Tomcat-readable runtime path, and accepts the installation encryption key from its original installation path when no environment key is supplied. It creates/adjusts log, Lucene, branding, configuration, reporting, module-cache and module-data directories, handles truststore permissions, then drops privileges to tomcat_admin. A prospective runtime must use synthetic local secrets and preserve their state without publishing values. Backend credentials, original TLS/session behavior and effective property loading remain to be fully mapped.

Relevant state therefore cannot yet be reduced to PostgreSQL alone: include or establish quiescence/absence of Lucene, configuration/branding/module data and session-related files. Original schema/seed initialization must be checked for the synthetic administrative fixture. Exact build-image digests and complete deployment commands remain unresolved. No runtime qualification is registered from these tag declarations.

The original frontend Dockerfile contains issue references about dependency migration; the transformation source also contains historical behavior comments. This is incidental source exposure, not an issue search. No linked issue or test-outcome file was fetched, and no blind-source claim is made.

Review scope: FhirConfig binding/client setup, organization outbound transformation and relevant identifier/type helper sections, complete frontend/database/proxy Dockerfiles and backend entrypoint. Package metadata and other transform/configuration methods are acquired but not claimed fully reviewed. The 23-property update materializer remains syntax-checked and unqualified. Four cohort application jobs and zero scientific cases remain unchanged.
