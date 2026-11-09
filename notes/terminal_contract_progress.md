# Terminal contract implementation progress

The common v2 policy and driver are implemented, and Quartz integration is now qualified on four hosted ordinary-control branches. Run 42538228610 passed at commit 855207afa50509560f637ff47b035cb48e113c37; independent reconstruction matches its ledger. All 411 hosted tests passed. See [the qualification note](quartz_terminal_integration.md) for scope, evidence and limitations.

P1's common contract and Quartz integration are complete. Source-shaped fixtures cover negative terminal outcomes and flagged follow-ups; the live application qualification covers ordinary controls. P2 must bind the full retained corpus, including RealWorld and PetClinic, to qualified extractors. P3 batching, P4 timing scope and P5 final freeze remain open. No untouched boundary variants were executed.
