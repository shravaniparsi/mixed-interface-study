# Request dependency baseline input fit

IDL represents declared input dependencies, including conditional, relational and grouped-presence constraints. Its documented OAS extension is operation-level x-dependencies (https://isa-group.github.io/IDL/docs/idl/quick-start/). RESTest's current README says version 2 is a rewrite incompatible with 1.x, and points to release 1.6.0 for the older tool (https://github.com/isa-group/RESTest). Do not attribute older IDL-based behavior to the current implementation without qualification.

The already frozen specification has no x-dependencies on POST /api/register or POST/PUT /api/admin/users. This is missing declared input, not proof that no dependencies exist. Adding our frontend-derived confirmation condition would change the baseline's information and still would not make a frontend-only confirmation field an API obligation. An IDL-backed comparator is a viable candidate only with sourced dependency input and a qualified implementation; it is not yet executed or qualified here. Existing schema and source replay baselines remain available. No solver, hosted reasoner or API operation was executed.

The next reference-feasibility step reads all fixed matching development tests rather than selecting only favorable assertions. Independent intended correctness remains unresolved.
