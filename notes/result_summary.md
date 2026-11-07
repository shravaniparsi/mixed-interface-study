# Current result summary

The expanded development batch is the current evidence record: notes/development_findings.md and results/development-batch-v2/summary.json.

Two applications, seven workflow templates, 44 locally registered case variants, 86 independent main replay branches. Only 40 branches reach downstream continuations: 19 API and 21 UI. An additional 22 diagnostic branches are separate repetitions, not new samples.

Supported findings: one known PetClinic API-contract-valid name blocks a later native UI address edit while the custom API edit succeeds; one RealWorld duplicate-title partial update returns a nonpersisted reference, detected by both API and native UI read continuations. The latter reproduced with controls including actual native UI updates. Neither finding is established as previously unknown, and maintainers have not confirmed these particular traces.

Two PetClinic whitespace cases remain policy-ambiguous. An empty RealWorld reference is a shared preflight anomaly, not observed UI detection. Eight main branches have prefix HTTP500; four RealWorld branches also have unreadable follow-up responses and failed unchanged-state checks. These are separate unresolved observations.

Native application baseline suites remain 92 + 58 RealWorld and 248 + 88 PetClinic. Selector/registry unit suite 34 passed; five additional generator-to-registered-input checks passed. No selector comparison, held-out study, injected-fault study or agent run has occurred. Extra cash expenditure $0.
