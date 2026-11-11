# Generator input boundary preparation

Two data-only bundles preserve the independently authored benchmark's vague and precise description modes. Each contains 106 descriptions and the three pinned OpenAPI specifications, in exactly six JSON files. Requirement records contain only an ID and description. No mutation definitions, application source, golden tests, model traces or released scores are packaged. All three API specification Git blob identifiers were checked against the pinned upstream commit; specification references are internal JSON references.

The builder uses a strict file and field allowlist. Synthetic controls reject added source/result/label files, a mutant field inside a permitted requirement file, duplicate IDs and an extra path outside the bundle. Reconstruct with `python3 scripts/extension/build_restestbench_generator_inputs_v1.py --verify`.

This is preparation, not proof of runtime isolation. A future generator must run with only the selected description-mode bundle mounted and no access to the study checkout, mutation labels, golden tests or released outputs. Its prompt, tools, baselines, model budget and evaluation must be registered before execution. No generator was run or registered by this step. The research process has already seen benchmark labels and results, so this cannot be described as an uncontaminated blind held-out dataset. Public model-training exposure is also not established.

The benchmark remains unqualified for a scientific method comparison pending runtime/golden-test evidence and a specific incremental-value hypothesis. This input boundary does not itself establish novelty. Source material remains subject to the upstream license retained at `evidence/restestbench-source-v1/LICENSE`.
