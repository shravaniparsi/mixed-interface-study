# Remaining frozen leads: source pins

Source inspection only; no runtime experiment is registered or dispatched for these leads yet. Both are outcome-exposed and belong to the existing finite expansion, not a new sample.

## Fast Dash, lead 5

Issue 191's closure points to d1172129268042725a8bca517175799ed9860989, parent b2a27d5075f9fb6f042681e2eb72ca1587122983. The commit batches eight issues, including coercion, input naming, secret-output handling and dependent-dropdown state. Do not attribute the complete commit's effects solely to the cascade repair, or count unrelated fixes as reproduced bugs.

The report describes parent changes over MCP updating child options but retaining an invalid child value; the UI callback clears the child. A useful control must demonstrate legitimate cascading change, because unconditional preservation would be incorrect. State is an application input mirror across calls, not a durable database. Admission must explicitly decide whether this meets the registered persistent-state observation requirement before a runtime protocol is written. The report's UI comparison is not our measurement.

Sources: [issue](https://github.com/dkedar7/fast_dash/issues/191), [repair](https://github.com/dkedar7/fast_dash/commit/d1172129268042725a8bca517175799ed9860989). No runtime result claimed.

## TestPlanIt, lead 6

Issue 668 links repair 8b10df16fd4d6d629ed5c18882d9bbdc1a67a066, parent 294b646af84ca8a7543fa37366e0b84437cd5c4a. The fix changes packages/mcp-server/src/tools/cases/update.ts and its mocked tests. It reads current tag memberships and creates/deletes disjoint sets, replacing a blanket deleteMany plus create nested write.

The reported failure is primarily a requested-postcondition failure: requested tags disappear. A competent postcondition baseline should catch it. It must not be presented as incremental frame-only detection. Maintainer commentary attributes operation ordering to the host's ZenStack behavior; the adapter repair accommodates that ordering. Runtime admission requires the real host persistence/ordering, not a mock that encodes the expected ordering. Version snapshots should be observed independently if included in the claim.

Sources: [issue and maintainer response](https://github.com/TestPlanIt/testplanit/issues/668), [repair](https://github.com/TestPlanIt/testplanit/commit/8b10df16fd4d6d629ed5c18882d9bbdc1a67a066). Do not touch the reporter's hosted instance or reuse its resource identifiers. Only local synthetic fixtures are in scope.
