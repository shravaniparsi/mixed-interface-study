# Nginx Proxy Manager AccessList source mapping

Wave 18 was published at eafd433896ae4d04ceb90d995c6b4e4e7fda74ad before thirteen requests. All source hashes verified, adding 41,689 bytes. Nginx Proxy Manager now has 38 acquired slots and 155,961 decoded bytes. No application runtime, input schedule or scientific case executed. The previously mapped AccessList modal remains a candidate, not a qualified workflow. Earlier unresolved cohort mappings remain pending.

## Complete native transport

AccessListModal initializes five form properties from the expanded readback: name, satisfyAny, passAuth, items and clients, using empty arrays only for falsy items/clients. Its submit logic validates item/client presence and duplicate usernames; removes items whose username?.trim() equals the empty string; projects item username/password and client directive/address; and passes the payload through useSetAccessList. The exact optional-chain comparison must be retained: null/undefined usernames are not equivalent to an empty string in that predicate. No altered state was executed.

useSetAccessList selects create/update from the ID. updateAccessList removes id/createdOn/modifiedOn and PUTs the remaining data; createAccessList POSTs its input. base.ts prefixes /api, serializes JSON through humps.decamelizeKeys, uses the original AuthStore bearer token, and camelizes response keys. Thus matching requires the original key transformation and persisted-readback initialization, not just a hand-written subset or the producer body. Original humps semantics/version, AuthStore, form-field state propagation and native ordinary request equality remain to qualify.

## Persistence and state

The backend create handler inserts the list, item rows and optional clients, refetches expanded rows, builds the htpasswd file, may generate proxy-host configs, writes an audit record and returns masked data. Update can replace item/client rows, writes an audit record, rebuilds the file, regenerates referencing host configuration and reloads nginx. An unused list may avoid some host work but not automatically the update reload. No nginx substitute or fake reload is admitted.

Readback maskItems sets every item password to the empty string and emits a hint. Update interprets a falsy password as retaining the named user's existing password. This is an intentional contract difference that the complete comparator must preserve. Password omission/null producer classes cannot be assumed preserved in native form state after readback masking. Input eligibility and unsupported classes must be settled before outcomes; no input selection or defect claim is made here. The underlying database state, audit effects, generated htpasswd files, nginx config and lifecycle need a registered restoration recipe.

## Original schema

The original API uses Ajv's 2020 implementation with coerceTypes=true, strict=false, allowUnionTypes=true and a native IPv6 format. The schema loader dereferences swagger.json through the original ref parser. POST requires name; PUT requires at least one property; both reject additional properties and reference original common/component definitions. common.json, swagger.json and exact installed dependency versions are unresolved. A generic JSON-schema check with different coercion/default behavior would not qualify S. API validation source comments about error formatting are incidental exposure, not followed fixes.

Review scope: complete base.ts request/response path through PUT, original validator/loader, targeted create/update/get/maskItems paths, POST/PUT request schemas, and previously acquired modal/hook/form wrapper. Acquired model/setup files are retained but not claimed fully reviewed. Original nginx-value safety checks and other helpers remain to map. No version, bootstrap or deployment claim follows from source acquisition alone.
