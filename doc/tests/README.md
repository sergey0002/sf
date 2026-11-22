# Environment acceptance tests

Run from `simple/`:

```sh
bash doc/tests/run.sh
```

This runs the architecture CLI's unit tests and the cross-component acceptance tests. No dependencies beyond `doc/tools/requirements.txt` are required.

## Coverage

- exact task-number/key contract: four decimal digits; Jira bare number; UI/user input uses `UI-`; every other source requires an explicit prefix;
- deterministic CLI results and rejection of malformed/missing prefixes;
- current project architecture docs validate and index remains fresh;
- the numbered local task fixture is valid JSON, its directory matches its task key, and no parallel task.md or copied manifest exists;
- skills mention the relevant source/naming and safety constraints;
- task-level smoke test: use the create-task contract and deterministic CLI identity helper to normalize a UI request, verify it, and run the architecture checks.

## Important boundary

These are executable checks of the environment and a local documentation/tooling task, not an end-to-end run of the prompt skills inside an agent runtime. This sandbox contains no product repository, live Jira/chat connector, configured model runtime, acceptance oracle for a product change, reliable product CI or isolated product-code sandbox. Therefore product-task execution through skills cannot truthfully be reported as tested. Once a real repository/task is provided and pilot prerequisites are approved, add a task-specific acceptance oracle and run it in that isolated environment.

Skills are natural-language instructions, not directly executable code here. Their static contract checks catch omissions/drift but cannot prove an agent follows them; that needs a separately approved tabletop walkthrough or runtime evaluation.
