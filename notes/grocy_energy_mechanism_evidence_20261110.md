# Grocy exploratory energy mechanism evidence

Pinned Grocy 4.7.1; ordinary actor; fresh application and browser for each branch. Registered replication run 42894136994, source f48b8a8ab183f0f484b15260983ac036cc859f5c. Proof: manifests/grocy-energy-results-v1.json. Raw archive: results/grocy-energy-v1-ci-42894136994.

| Producer energy | Pairs | API rename | Native rename |
| --- | ---: | --- | --- |
| omitted | 3 | null preserved | null becomes 1 |
| explicit null | 3 | null preserved | null becomes 1 |
| explicit zero | 3 | zero preserved | zero preserved |

The API continuation supplies the full mutable record, changing only the name. The native continuation loads the product, changes the same name and saves through the actual form. For omitted/null inputs, the loaded energy field already contains the string 1. Readback after native save contains numeric 1; calories is the only additional changed business field. All non-energy starting fields and fixtures match across conditions within each repetition. Branch order reverses in repetition two.

Pinned source supplies a consistent explanation: views/productform.blade.php passes product calories into the optional numberpicker, and views/components/numberpicker.blade.php substitutes 1 when isset(value) is false. PHP null fails that predicate. The input counterfactual distinguishes null from zero. No source-patch intervention has been performed, so the evidence does not isolate this code path experimentally from every possible interacting path.

This is one repeated exploratory mechanism discovered during earlier control auditing, not six independently sampled defects or a prospective boundary discovery. A maintainer API example supports null as a real API representation; preservation as a product requirement and novelty remain separate questions. The bounded prior-issue review is recorded in notes/grocy_energy_prior_issue_check_20261110.md. Confirmed natural-defect count remains zero pending adjudication. No further repetitions are requested by these positive outcomes.
