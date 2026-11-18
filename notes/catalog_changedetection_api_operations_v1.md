# changedetection.io original API operation mapping

Wave 44 acquired the two scheduled blobs once at freeze
d7bfefa6c6e78af317736ec6b3d41847c5157970. No runtime or scientific case executed.

csrf.js installs jQuery's beforeSend hook and attaches X-CSRFToken to unsafe,
same-origin requests. It does not replace ordinary form submission with JSON.
Its comments describe a prior CSRF initialization-order problem on the separate
AI-summary page; that is incidental prior-fix exposure, not a new finding.

The original api/operations.py declares shared REST/MCP operations. The retained
REST Watch resource imports these operations; the MCP caller has not yet been
inspected, so this review does not claim that all tool paths invoke them. The
operations are substantive server validation, not raw database writes.
create_watch strips internal fields, normalizes/validates URL, invokes common
checks, extracts processor configuration, validates the original CreateWatch
schema and checks watch limits before adding a record. update_watch runs common
checks, rejects null/non-string/blank URLs when supplied, removes internal and
read-only fields, extracts processor configuration, validates UpdateWatch,
rejects unknown fields, merges into the existing watch, validates the merged
interval state, commits and saves processor configuration separately.

The original schema validator is OAS31Validator over a component reference in
the merged API specification, including plugin fields. These original checks
must remain in any future schema/handler baseline. Their source existence is
not an executed rejection or proof that every client invariant is enforced.

The native editor still follows its separate request.form/WTForms route. Its
source performs additional field conversion and may queue an immediate recheck;
full state and ancillary effects therefore cannot be ignored in a comparator.
The inspected CSRF and API-operation dependencies do not supply a complete JSON
request emitted by native Save or prove equivalence of the two routes.

The watch mapping remains pending, with no new target values or altered-input
classes selected from validation details. These findings narrow deployment and
baseline requirements; they do not count as natural incompatibility evidence.
