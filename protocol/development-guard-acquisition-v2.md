# Guard acquisition implementation correction

Version 1 at e980415 returned class_scope/unsupported for the source component and unknown for all six records. The reason is that its inheritance exclusion also rejected TypeScript implements clauses. Retain v1 output unchanged. Version 2 changes only that exclusion to reject extends, allowing erased interfaces; it adds an interface regression test. This is an engineering correction after a known development failure, not a new independent experiment or outcome-blind validation.

Use the same six exposed records, source hash, manually supplied selection, parser, original replay archive and assumptions. Run v2 once; retain failures and abstentions. No new cases, source reads, backend runs or scientific claims. Freeze this correction and its code before the qualification.
