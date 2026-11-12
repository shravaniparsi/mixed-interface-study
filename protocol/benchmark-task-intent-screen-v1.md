# Prospective static task-intent screen

Purpose: assess whether the pinned external task corpus contains independently authored write-task descriptions suitable for a later continuation protocol. This is a descriptive inventory, not selection for application execution, proof of novelty or a defect search.

Input is the exact WebArena-Verified dataset archived in benchmark-frame-screen-v1. No task intents or evaluator bodies have been inspected by this study's metadata screen before this file. Earlier literature examples and the first search-returned task example are incidental exposure; do not claim complete blindness. No evaluator labels, agent success logs or issue reports may inform the screen.

Process every task in task_id order, preserving all 812 records and grouping by intent_template_id and sites. Inspect only task_id, sites, intent_template_id, intent_template and intent. Mark lexical creation candidates when the template contains whole words create, add, post, publish, register, submit, or open. Mark lexical change candidates for edit, update, change, rename, modify, revise, or set. A template may be both. Match case-insensitively. Store all matches, nonmatches and template multiplicity. These lists are intentionally permissive: 'open' may describe navigation, and 'post' may be a noun. They are not validated operation labels.

Do not discard nonmatches as semantically nonwritable. Do not infer that two tasks share the same record or fixture merely because they mention the same entity class. Report only corpus coverage and candidate lists. A later human-readable source review must establish API availability, independently meaningful creation/edit goals, compatible actor/record assumptions, and a preservation obligation before any scientific selection. If task templates do not supply these, the benchmark is not a ready-made continuation dataset.

No application execution, new model calls or paid resources are authorized by this screen. Do not inspect the eval field or modify the closed cohorts.
