# Independent prior-art check, 10 November 2026

The claim-source-verification skill was applied with a separate skeptic in a fresh context. Three technical source pairings were examined. Their positive cores were confirmed after narrowing; one stronger negative inference was rejected. No access block remained. This check does not establish exhaustive novelty.

| Source and inspected scope | Supported claim | Consequence |
|---|---|---|
| NoTamper, CCS 2010; abstract, §§2–3, implementation/evaluation and §5.2 | Extracts client validation constraints and probes server behavior for satisfying and violating inputs | Constraint extraction plus server-acceptance testing is established |
| WARDroid; abstract, §§I–II, VI–VII, opening VIII | Detects Android/API validation inconsistencies; Account DoS follows an API password update into client lockout | A broad claim that prior work ignores post-write client usability is false |
| CRS, arXiv 1204.1216 v3; abstract, §§3.1–3.2, 4.2–4.3.2 | Replays user actions, preserves workflow/parameter dependencies, and uses rendered UI evidence for acceptance | Workflow-aware tampering or UI observations alone cannot carry novelty |

Supporting text retained by the skeptic:

- NoTamper §3: “constructs logical formulas representing the constraint-checking function”; “generates server responses for each one”.
- WARDroid abstract: “blackbox testing of server validation logic to identify inconsistencies”; §VII Account DoS: “This caused the account to get locked out of the app.”
- CRS §3.2: “CRS achieves this by replaying user actions.”

Primary sources:
- https://www.cs.uic.edu/~hinrichs/papers/bisht2010notamper.pdf
- https://cs.uwaterloo.ca/~yaafer/teaching/papers/WARDroid_SP18.pdf
- https://arxiv.org/abs/1204.1216 and https://arxiv.org/html/1204.1216v3

The stronger inference considered during extension planning was that earlier work tested acceptance without subsequent usability. The source check contradicted it: WARDroid's Account DoS case directly demonstrates downstream lockout; its cross-platform content-injection case follows API-submitted content into a website. NoTamper also contains stored-profile XSS inspected during a later administrator login. That inference was rejected before being used in a manuscript.

Ordinary persisted-object reopening, unrelated editing, and saving were not demonstrated in the inspected passages, but this scoped observation is not proof that the literature lacks them. CRS also observes expected subsequent controls and rendered DOM changes, which further narrows any proposed distinction. The broad originality argument is weaker following this check. The production extension therefore tests an empirical comparison and benchmark contribution rather than claiming discovery of the general validation-gap problem.

Metadata caution: the CRS abstract record and v3 heading differ between “Rich” and “Real-world”; the current version identifies ASIA CCS 2014. Do not attribute v3 technical details to the initial 2012 submission without version-specific verification.
