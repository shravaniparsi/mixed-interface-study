# Final-read correction in the development pilot

Initial run: `realworld-20261107T021733Z`, eight route executions. UI/API failed twice during final DOM verification; the other six executions passed. In both failed traces, creation and meaningful API editing were accepted and the independent API read returned the edited body.

The UI-created workflow had already opened the article hash route. The runner's later `page.goto` targeted the same URL, which did not trigger a fresh article request. The trace showed the earlier article GET returning the original body and no new UI article GET after the update. The 30-second wait therefore did not establish that a new UI read was incompatible with the saved record.

The runner was changed to reload the article page for every route, observe a native article GET, verify its returned fields, then verify the rendered body. The original traces and source snapshots remain intact. The new run, `realworld-20261107T021931Z`, passed all eight executions with the same expected business state. No application code was changed.

Interpretation: the accepted control measures fresh-read compatibility after persistence. It excludes automatic synchronization of a previously open page. The first result is retained as a stale-view observation outside that control's scope, not counted as a confirmed application defect. A future live-tab consistency study would require a separate expected freshness contract and controlled timing.

Independent code review also led to explicit fixture/base-URL environment binding, checks of child exit codes and exact expected state, build hashing and source archiving. The first attempt already recorded correct bases, actor and persisted state; these hardening changes prevent future malformed results from being accepted.
