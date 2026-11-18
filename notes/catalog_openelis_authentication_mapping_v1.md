# OpenELIS original authentication and initialization mapping

Wave 15 was published at bd79716b7f28aef947d93b2010012a03fd21dcb1 before eleven original source requests. All verified, adding 102,819 decoded bytes. OpenELIS now has 54 acquired slots and 820,595 bytes. No login, application runtime or scientific input executed.

## Original form authentication

Login.jsx submits loginName and password as application/x-www-form-urlencoded to serverBaseUrl + /ValidateLogin?apiCall=true with browser credentials included. On HTTP 200 it assigns window.location.href to /. SecurityConfig's form-login chain names the same endpoint/parameters, uses its original success/failure handlers, migrates the session on login and exempts ValidateLogin from CSRF. Other stateless/basic-auth chains in that class are not substitutes for this original native actor.

LoginPageController exposes /session, reports whether the original session is authenticated, includes the local user ID/login name and adds a CSRF token when present. The previously acquired mutation helper reads localStorage CSRF and sends X-CSRF-Token. The frontend configuration file and exact session-to-localStorage initialization still need review before an API mutation helper is admitted; do not infer the serialized CSRF property name solely from its Java setter.

The success handler populates UserSessionData, a timeout, timezone and permitted pages. It can persist a password-expiry notification. Thus re-login can change session identity and database state; it is not a neutral substitute for restored browser/server session state. No general timestamp or notification exclusion is authorized. Tomcat context.xml specifies SameSite=strict cookies and its datasource. It contains no explicit session-manager persistence configuration, so restart survival is not established from that file alone.

scripts/extension/openelis_native_login_v1.mjs is a syntax-checked, unexecuted original-control helper. It fills the source-identified native fields, clicks the original button, waits for the original navigation, compares the complete form payload/response and checks the original /session response. Its returned envelopes/storage remain private because they contain authentication material. It does not bootstrap an account, launch a browser or qualify restoration. The actual deployed frontend/backend URL mapping remains to be supplied from original configuration.

## Initialization and scope

The main OpenELIS-Global.sql is declared 863,876 bytes in the frozen tree, above the registered 256-KiB acquisition cap. It was not fetched, split or accessed through another source. Small initialization helpers and build orchestration were acquired, but their full effects and the contents of the larger seed remain unverified. No clinical-table emptiness or synthetic-only database claim is made. A future runtime proposal must explicitly address fixture scope and original administrator initialization before use. The acquired LoginUserServiceImpl password/profile methods do not by themselves establish the initial-admin environment-variable consumer.

The shared FHIR helper sets a temporary ID only on an in-memory resource when missing. createFacilityIdentifier reads the facility-organization service and constructs an Identifier, with no direct persistence in the inspected method. That underlying service remains an essential unresolved dependency for the asynchronous transformation boundary; do not claim a full transitive side-effect audit.

Review scope: native login submission/field identifiers, the form-login security chain, session response, success-handler session/notification path, complete short Tomcat context, targeted FHIR common helpers and build target declarations. Other large security/controller/helper sections and acquired initialization helpers are not claimed fully reviewed. Existing incidental source-fix exposure remains disclosed. The organization candidate is not selected or runtime-qualified. Cohort totals remain four application jobs and zero scientific cases.
