# Retrospective information-matched reference replay

This is a secondary analysis of the already exposed 24 NetBox calibration cases, not a prospectively collected cohort. It adds no application executions, model calls, independent bugs or blind labels. Both observed version outcomes are known before defining this comparison.

Compare five deterministic checks on identical response, readback and database observations: success status only; preservation of explicitly supplied custom fields; the recorded runtime-configuration check; an ordinary parameterized reference using the configured defaults and explicit-argument precedence; and a reference retaining only the phase-zero defaults. The latter is an information-deprivation diagnostic, not a competent state-of-the-art baseline.

Construct the parameterized reference's default values from the recorded configuration-creation/update request bodies, independently of the probe's stored expected dict. Use presence-based explicit-argument precedence: null, false and zero are supplied values and must not be replaced. Restrict checks to the three registered defaulted fields and supplied sibling. Apply the same semantic rule to both versions. Verify all original calibration evidence first. Preserve each per-case comparison and differences at response/readback/database stages.

The complete reference is not independent ground truth: the default-precedence rule comes from the same exposed historical requirement. Equality would demonstrate no additional detection over this equally informed rule on these traces, not universal equivalence of all tools. A difference needs diagnosis, not automatic credit to the new method. Stale-reference disagreements on the repaired version demonstrate the effect of the selected stale values in this case, not a population false-positive rate.

Stop after all archived cases. Do not add cases, repair the application, change templates to increase a difference, or claim automatic extraction or reduced manual effort. Use this analysis to decide whether further configuration-template experiments have a substantive methodological justification.
