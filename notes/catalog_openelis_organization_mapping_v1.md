# OpenELIS organization candidate: source mapping

Wave 12 was published at eb7f49bc4bfcb35f6508fb871f9d16988483ad3b before acquiring nine scheduled files. All verified: 124,081 new decoded bytes. OpenELIS now has 25 acquired slots and 567,799 bytes. This is source mapping only; no OpenELIS application, schema case or scientific input has run.

## Native transport and state

The acquired OrganizationManagement list links creation to /MasterListsPage/organizationEdit?ID=0 and editing to the same route with an ID. OrganizationAddModify reads /rest/Organization?ID={ID}&startingRecNo=1 and posts JSON.stringify(orgInfoPost) back to that endpoint. The existing Utils.ts helper sends POST application/json with the original browser credentials, X-CSRF-Token and Accept-Language headers. This is an explicit JSON path, unlike the unresolved Meme Search form transport.

The complete orgInfoPost object is larger than the visible name/address fields: it includes id, organizationName, shortName, isActive, lastupdated, commune, village, department, formName, formMethod, cancelAction, submitOnCancel, cancelMethod, mlsSentinelLabFlag, parentOrgName, state, internetAddress, selectedTypes, nested organization, cliaNum, streetAddress, city and email. JavaScript undefined-property omission, parent-organization effects and selected-type effects must be mapped, not replaced with a reduced payload. The original editor and helper have not been runtime-qualified.

The requiredProps helper returns aria-required only. Its RequiredMarker is visual/accessibility presentation. This source alone does not demonstrate native browser required-field enforcement. The form's Save control is type=button, disabled by saveButton state; several field handlers enable it. Any claim of native blocking therefore needs the actual control path and observed actionability, not an inference from an asterisk or aria-required attribute.

## Backend and state boundary

OrganizationRestController accepts @RequestBody @Valid OrganizationForm. Empty/null or zero form ID selects creation; otherwise it loads the existing record and returns 404 if absent. The form carries Jakarta/custom validation, including configuration-dependent OptionalNotBlank, SafeHtml, URL, Email and identifier patterns. The exact validator/context is not yet an executable S baseline. Do not translate frontend markers into S or claim universal requiredness from configuration-dependent annotations.

The save path copies form properties, preserves the stored timestamp when its milliseconds equal the form version, updates/inserts the organization, persists address parts, links organization types and calls fhirTransformService.transformPersistOrganization. This requires mapping FHIR persistence and any network side effects before a local-only runtime/restoration design. PostgreSQL alone cannot yet be assumed to contain all relevant state. OrganizationService also checks active duplicate organizations and creates a FHIR UUID when missing. Stable-ID GET and menu/list methods are acquired but their complete representation still requires review.

Source comments mention historical bug identifiers and timestamp-version behavior. These were incidental source exposure, not a bug/issue search. Do not describe this candidate as blind or infer a new defect from those comments. No issue/PR content was fetched.

## Disposition and remaining work

Retain a synthetic administrative organization candidate, pending complete frontend materialization, earlier workflow-order dispositions, validation configuration, authentication/bootstrap, FHIR service/persistence mapping, executable provenance and restoration design. No patient, clinical or employer data is required or authorized. A locally provisioned supporting FHIR service could be in scope only if its original configuration and state are explicitly mapped; do not silently suppress an original persistence call.

Review scope: targeted controller save/side-effect block, form annotation sections, service insert/update, list navigation links, full required-marker helper and earlier frontend JSON construction/helper sections. The acquired DAO and other large sections are not claimed fully reviewed. This is not a selected or qualified workflow. Mathesar and Viseron remain closed; the cohort still has four application jobs and zero scientific cases.
