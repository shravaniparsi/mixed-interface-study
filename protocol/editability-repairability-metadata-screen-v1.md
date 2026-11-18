# Redesign metadata feasibility screen v1

Purpose: determine whether the retained catalog contains a plausible population
for the author-approved editability/repairability question. This is not selection
of another cohort or replacement of the failed twelve-project study. No source,
issue, README, runtime or application outcome is fetched. Publish this protocol,
collector and input bindings before computing the counts.

Use only the original 1,362 retained catalog YAML entries at revision
114743487b2cfd1a9c68deff3511c11c3b307695. This is a new, API-advertising stratum
of an already exposed metadata frame, not a newly discovered or blind population.
Explicit API advertising better aligns with API production than a Docker label
alone, but does not establish a writable JSON API, UI, workflow or reproducibility.
It undercovers projects with undocumented APIs; report that selection bias.

Parse once with installed Ruby 2.6.10/Psych 3.1.0 safe_load, Date/Time scalar
classes only, aliases disabled, 30-second timeout. Reuse the original pinned
metadata schema, HTTPS GitHub-root URL, Docker label, no third-party dependency,
license allowlist and fork/alias checks. Do not widen them after counts are seen.
Apply the existing evaluator with the union of all non-metadata-only exposure
classes as prior references. This conservatively excludes exact names, shared
owners and matching catalog names/stems. Require the repository itself to have
only_catalog_metadata_references_in_available_index classification. That label
still does not rule out missing history or establish lineage independence.

Additionally require description to be a string with standalone case-insensitive
word API (regex word boundaries). Do not count API in the project name, source
URL, category, related product or external documentation as a substitute. Retain
all failed predicates for all entries, deduplicate passing repositories, and
report the exact passing list and owner count. Do not rank, choose a sample,
acquire new source or evaluate altered inputs at this stage. All passing entries
remain workflow eligibility and ancestry unknown.

Preserve failures and empty/small candidate populations. No added keywords,
refreshed revision, substitute catalog or successive resampling is authorized
by this screen. Any further population decision requires scientific justification
and a prospective selection/qualification protocol, not a search for positives.
