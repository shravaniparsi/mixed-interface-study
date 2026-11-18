# OpenELIS FHIR branch and complete update mapping

Wave 13 was frozen at 1be55f68cc69ee30305d95ad8722598c4ad11aab before acquiring ten original files. All verified, adding 117,919 bytes. OpenELIS now has 35 source slots and 685,718 decoded bytes. Property-template keys were inspected before selected non-credential values were displayed; no private secret store or external endpoint was accessed. No application execution occurred.

## FHIR persistence

transformPersistOrganization is annotated @Async. It transforms an organization and an optional location into FhirOperations, then calls createUpdateFhirResourcesInFhirStore; a FhirLocalPersistingException is logged. A successful HTTP organization save alone therefore cannot prove completion of downstream persistence.

The persistence implementation initializes localFhirClient only when getLocalFhirStorePath is nonblank. Its noStore predicate checks for a null client. The FhirOperations overload delegates to the list overload, which returns an empty transaction-response bundle before constructing/sending a transaction when noStore is true. The source explicitly describes the empty org.openelisglobal.fhirstore.uri mode. This is an original configuration branch, not a proposed stub or application patch. The public property template currently supplies a nonempty store URI; a future empty-store deployment would be a prospectively declared configuration choice, not the template default or evidence about deployments with a configured FHIR store.

Do not yet assume the branch is reachable merely by setting a property: the FhirConfig binding/default resolution still needs review. The organization transformation runs before the persistence no-op and remains asynchronous; its database reads/writes and task completion also need mapping. Original configuration can remove the outbound store transaction only if its actual effective settings are verified. No third-party FHIR service is authorized. The inspected template sets transformOnStartup and subscriber.allowHTTP false; partner/subscriber list keys are empty. Other integration settings remain part of the pending runtime audit.

## Validation

OptionalNotBlankConstraintValidator requires a nonblank value whenever any listed field is in use, and likewise for enabled Boolean configuration properties. It consults useField, not requireField. FormFields constructs DefaultFormFields and provides the resolved in-use/required flags. Exact field values and configuration initialization must accompany any executable validation baseline. The organization name itself has an unconditional NotBlank annotation in the previously acquired form; do not generalize configuration dependence to every field.

## Materialization implementation

scripts/extension/materialize_openelis_organization_update_v1.mjs now maps the 23 properties assigned by the original orgInfoPost construction. It requires a complete original form readback and a persisted positive numeric string ID, preserves the original selected type IDs and nested parent representation, and models one supported text edit with unchanged parent/type selections. Only an edited internetAddress is trimmed, matching its original handler. JSON.stringify semantics preserve null and omit undefined properties rather than converting them into blanks. Original form/version/control metadata is retained; the producer body is not substituted for readback.

This implementation is syntax-checked only. Its settled-effect assumptions, complete readback shape and emitted native request still need runtime qualification. It does not claim support for parent/type edits, all malformed states or every configuration. The workflow and scientific input schedule remain unselected. Next essentials are FhirConfig binding/organization transformation, original bootstrap/authentication and executable provenance, then the bounded ordinary runtime recipe. Earlier candidate-order prefixes remain unresolved. Four cohort application jobs and zero scientific cases remain unchanged.

Review scope: complete small OptionalNotBlank validator, targeted FormFields initialization/accessors, exact organization transform method and FHIR initialization/no-store/transaction overload chain, selected public property keys, and previously acquired frontend state construction/edit handlers. Other portions of the acquired large FHIR files and DefaultFormFields are not claimed fully reviewed.
