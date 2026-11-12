# Configuration-template contribution decision

Decision: do not expand the current default-template calibration into a claimed new testing method. The mechanism reproduces a useful known fault, but the available implementation does not distinguish itself from ordinary configuration-parameterized assertions.

## Information-matched replay

This retrospective analysis uses the already exposed 24 NetBox cases and adds no application execution or model call. Both programs implement the same manually specified default-precedence rule. One uses recorded runtime metadata; the reference independently reconstructs configured values from configuration request bodies. Their agreement is a rule-equivalence sanity check, not a competitive evaluation of independently developed methods.

| Check | Alerts on 12 faulty-version variants | Alerts on 12 repaired-version variants |
| --- | ---: | ---: |
| Success statuses | 0 | 0 |
| Explicitly requested values | 0 | 0 |
| Recorded runtime-configuration check | 6 | 0 |
| Equally informed parameterized reference | 6 | 0 |
| Reference retaining initial defaults after configuration changes | 7 | 4 |

The two complete checks disagree on zero cases. Their expectations derive from the same historical requirement; neither supplies independent ground truth. The stale reference uses less current information and is not a competent comparator for a superiority claim. Its four repaired-version alerts concern the omitted map, empty map, sibling-only map and partial override after the defaults change. They show an information mismatch in these traces, not a general false-positive rate.

The probe, input schedule and original results remain unchanged. Six violating variants still represent one known defect. Automatic endpoint discovery, metadata binding, semantic inference, generality, human-effort savings and current model performance were not evaluated.

## Relation to existing work

Xu and Legunsen's Configuration Testing explicitly instantiates parameterized tests with configured values and examines their runtime effects (https://arxiv.org/html/1905.12195v2). Our present merge-and-compare rule fits that established principle. ARMeta already supplies executable stateful REST metamorphic tests (https://arxiv.org/html/2605.28321v1). Neither reference alone settles the novelty of an automatic runtime-metadata mapping system, but we have not implemented or evaluated such a system. An unimplemented distinction cannot carry the present contribution.

## Consequence for the active goal

Retain the calibration as development evidence. Do not start a larger independent-input configuration cohort under the claim that dynamic parameter substitution is a new oracle algorithm. More applications could establish applicability of an existing technique, but would not by themselves resolve its methodological novelty.

The original independent-input study and its null result remain closed. The next contribution-design step must specify a nontrivial unresolved mechanism, a competent information-matched baseline and a prospectively evaluable hypothesis before selecting new outcomes. The active goal remains incomplete; this is rejection of one candidate method claim, not rejection of negative results or proof that the research area lacks opportunities.

## Reconstruct

```
python scripts/extension/replay_netbox_information_reference_v1.py --verify
```

Inputs and the replay implementation are hashed in manifests/netbox-information-reference-replay-v1.json; the script also reconstructs the original calibration first. This secondary analysis is separate from prospectively registered application experiments.
