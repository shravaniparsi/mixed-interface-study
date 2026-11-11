# Static mutation applicability qualification

Before inspecting requirement bodies, include every requirement file in the existing pinned inventory (63 FastAPI, 29 NestJS, 14 TodoApp). Parse with the unmodified upstream Requirement parser and apply each listed mutant independently to a fresh temporary copy of its target source from services/<service>/original. Use the unmodified upstream Mutator. Record parse errors, missing targets, application return values, exceptions and whether target bytes changed. Never substitute another mutant or patch a failing source in this pass.

This is a source-level qualification, not a REST service experiment. Application success does not prove that a mutant compiles, changes behavior or is killed by a golden test. Inputs and mutation labels become exposed to this study during qualification; they must not be described as a blind or uncontaminated held-out set. Future generator inputs must be physically isolated from mutation definitions and golden tests.

Resource ceiling: one local pass over all inventory files and their mutants, no dependency installation, no network calls from source code, no generated tests executed, no model calls. Use existing pinned archive bytes and retain a compact input bundle, hashes and complete observations. CI may reconstruct the same source-level qualification; no application jobs are registered here.
