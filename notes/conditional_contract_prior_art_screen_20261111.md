# Screening conditional-contract inference before a method comparison

This is a primary-source screening note, not a manuscript-ready independent claim verification or an executed baseline comparison. No paper results are imported into our dataset. The purpose is to avoid registering a method whose only proposed novelty is an established mechanism.

* [AutoFrame, arXiv:1808.08751v4](https://arxiv.org/abs/1808.08751v4), abstract, describes automatic frame inference for object-oriented languages. Merely inferring fields that may change is not a defensible new principle for our work. This does not establish equivalence to inferring intended business effects of remote partial updates.
* [Stateful Testing, arXiv:1108.1068v2](https://arxiv.org/abs/1108.1068v2), abstract, describes generating tests to violate dynamically inferred contracts, both to expose code errors and to discard unsound inferred contracts. Thus challenging an inferred rule with additional stateful executions is already established. The author-hosted paper was also located at https://se.inf.ethz.ch/people/ypei/download/stateful_testing.pdf .
* [Improving Dynamic Specification Inference with LLM-Generated Counterexamples, arXiv:2604.10761v1](https://arxiv.org/abs/2604.10761v1), abstract, explicitly studies LLM-generated tests intended to invalidate inferred assertions. Adding an LLM counterexample generator is therefore insufficient as a novelty claim. The full HTML paper is accessible at https://arxiv.org/html/2604.10761v1 . Its implementation and experimental conditions still need detailed comparison before selecting a competent baseline.

No quantitative superiority, applicability to every REST service, or absence of relevant prior work follows from this screen. The approaches operate in different settings; a REST-specific extension might be useful but must identify a concrete capability or measured advantage beyond these established principles. Artifact executions and independent source–claim review remain undone for these newly screened papers.

## Decision for this project

Do not register a paid comparison with a claim of novelty based solely on (1) frame inference, (2) inferred conditional postconditions plus challenging tests, or (3) adding LLM-generated counterexamples. Our current manual-contract ablation already shows that deriving intended conditional effects, rather than simply allowing a field to change, is necessary on the development records. It does not show that we can derive those effects automatically, or that a resulting method would outperform competent alternatives.

The open method gate is therefore substantive: specify the extra semantic information recovered, its independent source, how it changes a prediction or test, and which existing approach lacks that measured capability under matched inputs and budget. A complete manual contract remains an information-rich reference, and natural-language test generation using the same requirement text remains a required practical comparator. A benchmark qualification pass, even if all golden tests pass, cannot close this method gate.

The already registered valid-service qualification is unchanged. No new model calls, application jobs, corpus expansion or finding-driven repetitions are authorized by this screening note.
