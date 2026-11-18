# OpenELIS bootstrap policy and declared image provenance

The wave-17 source schedule and image-metadata protocol were published at 65c338e16e3ce1864b37152e70c9b56f9e4b74e5 before collection. All six source blobs verified (12,249 bytes), bringing OpenELIS to 67 acquired slots and 875,507 bytes. No application job or scientific input ran.

## Original bootstrap policy

LoginUserService declares the default login name admin. PasswordValidationFactory uses the configured PasswordRequirments value, choosing MINN by default, HAITI for that value and CDI for that value. CDI delegates to Haiti. Minnesota requires at least eight characters, its allowed alphabet, and three of four character categories. Haiti requires at least seven, its allowed alphabet and a special character. A future ephemeral password containing uppercase, lowercase, digits and an exclamation mark, at least eight ASCII characters and within the original bootstrap byte limits, can satisfy all three acquired implementations. Generate it privately for the isolated runner; no existing credential or default password is needed. Configuration and actual acceptance still require runtime verification. Do not infer the unimplemented username-substring check from the Minnesota source comment.

The native-login helper now observes a nonempty session user ID and csrf field and waits for the original App.jsx initialization to put that same token in localStorage. It does not inject a token. Syntax checking does not establish native execution or administrator-role qualification.

ThisLaboratoryServiceImpl.find reads the recorded site-information ID, falling back to the facility short name. record inserts the site-information setting when absent, returns without a write when the ID already matches, and updates it otherwise. This narrows one startup write path but does not remove the separate organizationService.save in facility initialization. No full-state restoration equivalence is inferred.

## Declared image route

The three original develop image references resolved to linux/amd64 metadata. Backend: sha256:4aca00a8b5d5fbc58960cefc2224eeef27d768351a57b9446096fb3b2cb0df79 (616,240,344 compressed layer bytes). Frontend: sha256:8893cfb9f7e72de75cbc66f138617ca815d8a38fa1c0d77fed2141336a8cf5d0 (57,073,932 bytes). Database: sha256:2f13f5b8a98b1cfc34e0cda6ee583a581d682d23a447fde2277dd8fe72f89499 (152,338,666 bytes). These are metadata observations, not downloaded layers or executed applications.

None declares org.opencontainers.image.revision. Therefore this metadata route does not qualify them against frozen source cd4bfc60218866536f3a855a563e6930e0faabd3. Missing labels do not prove the images differ from that source or that the project is irreproducible. Do not follow newer tags or revise the frozen source to obtain a match. A separately registered original-source build remains possible but must supply exact source and dependency/build evidence within the original runtime limits. Image provenance, the oversized seed's fixture scope and supported state restoration remain prerequisites. This project is pending, not a qualified null or an observed defect.

## Accounting

Eleven additional terminal unit-check runs were collected in catalog-openelis-preparation-ci-accounting-v1. All succeeded; total reported run duration is 1,347,000 ms and reported billable milliseconds are zero. These records exclude application jobs and previously retained unit runs. They are not an invoice or a claim that the entire research project cost zero. The $100 ceiling and free standard-runner restriction remain.

## Supported session-restoration option to evaluate

The official Tomcat 10.1.61 [Manager reference](https://tomcat.apache.org/tomcat-10.1-doc/config/manager.html), consulted on 2026-11-18, documents StandardManager pathname as null by default and enabling persistence with a nonempty pathname. persistAuthentication defaults to false. This supports investigating explicit server configuration rather than presuming restart persistence. It does not identify the version in the unqualified application image, establish Spring Security session serialization, or qualify the ordinary restored branch. Any configuration choice must be registered before runtime, with the actual Tomcat version pinned and checked. No configuration has been applied.
