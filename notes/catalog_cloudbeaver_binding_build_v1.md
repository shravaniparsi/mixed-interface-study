# CloudBeaver binding and build findings

All six preregistered wave 32 files were verified at freeze 12a429c9a48fca4cd4e6cb5eb8ea903186e98ba9, adding 40,929 bytes. Cumulative CloudBeaver acquisition is 70 slots and 552,240 bytes. No application was launched and no scientific case was added. Wave 31 publication CI 44317322909 passed.

## Binding resolves the apparent nullable-name gap

The original GraphQL schema declares teamName as nullable String, but WebServiceBindingAdmin routes it through getArgumentVal for both createTeam and updateTeam. WebServiceBindingBase.getArgumentVal obtains the argument and throws DBWebException when the value is null. The interface also marks teamName NotNull. Thus a schema-only interpretation that omitted/null teamName reaches storage is contradicted by the retained binding source. This is source evidence of a server-side check, not an executed rejection or a demonstrated bypass. Description uses getArgument instead. Do not change the registered omit/null policy to target another value after seeing this source; inputs are not yet frozen and no outcomes have run.

Both team create/update methods declare administrator permissions. The shared proxy checks action permissions before invoking the implementation. Authentication/bootstrap and runtime session equivalence are not yet qualified. ExecutorHandlersCollection.before registers a before link, confirming the FormState chain order: format, prepare, validate, submit, subject to original interruption and loaded/changed conditions.

## Build provenance remains unresolved

The backend workflow delegates cloning and Maven setup to dbeaver/github-actions at mutable devel and reads project.deps, then invokes the previously mapped unpinned build script. The frontend workflow also uses that mutable clone action; it requests immutable Yarn installation but does not establish sibling source revisions. Its source declares Node 24.22.1; this declaration has not been executed or independently qualified. The image workflow consumes named build artifacts and tags by branch; it does not identify an immutable dependency-source manifest in the inspected file. Artifact-upload steps in the inspected frontend/backend workflows are commented out. This does not prove no release artifact exists elsewhere.

The current mapping therefore establishes neither a source-matched executable nor a complete runnable comparator. Do not run a guessed dependency combination or infer a natural defect from client-required fields. Retain CloudBeaver as pending while other fixed-cohort mappings proceed; any later deployment must resolve this provenance gap prospectively. Application jobs remain six and scientific cases zero.
