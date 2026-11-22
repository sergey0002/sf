# Environment acceptance tests

Run from the repository root:

```sh
bash doc/tests/run.sh
```

This runs the architecture CLI's unit tests and the cross-component acceptance tests. No dependencies beyond `doc/tools/requirements.txt` are required. The default command is read-only with respect to `doc/architecture/index.json`: it validates the existing index and never rebuilds it in the checkout.

For agent runs, use `bash doc/tests/run.sh --brief`. It checks the existing index without rebuilding it and emits one success line with the checked areas. On failure it reports the failed step, exit code and captured diagnostics.

Use `bash doc/tests/run.sh --index-only` to check index freshness and rebuild reproducibility. It fails before any rebuild when the committed index is stale, then builds the index twice in separate temporary trees with `PYTHONHASHSEED=0` and `PYTHONHASHSEED=12345` and requires both results to be byte-identical to `doc/architecture/index.json`. `bash doc/tests/run.sh --gate` combines those index checks with the full test suite and path validation. It is the mandatory local gate: CI/CD pipelines and Git-hosted workflows are prohibited in this project (see the manifest).

Use `bash doc/tests/run.sh --in-copy [mode]` when the checkout cannot run the gate directly. It copies the project to a temporary tree, runs the requested mode (`--gate` by default) and leaves the checkout unchanged.

During iteration, run the exact test selector from the task plan. To explore a related group, use `python3 -m unittest discover -s doc/tests -p 'test_*.py' -k decompose -v` and confirm the selected tests ran. Use the compact full suite once the checked inputs are stable. [Recording a result on that snapshot](../architecture/domains/task-lifecycle/entities/verification-evidence.md#сбор-результата-через-cli)

## Coverage

- exact task-number/key contract: four decimal digits; Jira bare number; UI/user input uses `UI-`; every other source requires an explicit prefix;
- deterministic CLI results and rejection of malformed/missing prefixes;
- current project architecture docs validate and index remains fresh;
- a built wheel installs outside the checkout, exposes the `arch` console script, reports the package metadata version and reads project resources through `--root`;
- a stale index fails the local gate before any rebuild, the checkout stays unchanged, and two rebuilds with different hash seeds are byte-identical;
- an environment-dependent rebuild is rejected even when a single rebuild matches the committed index;
- `task evidence` records and re-checks results for a subtask key, not only for a parent task;
- the numbered local task fixture is valid JSON, its directory matches its task key, and no parallel task.md or copied manifest exists;
- skills mention the relevant source/naming and safety constraints;
- task-level smoke test: use the create-task contract and deterministic CLI identity helper to normalize a UI request, verify it, and run the architecture checks;
- lifecycle writes: decompose refuses an invalid package or collision before writing, resumes an interrupted composite write from its journal, and refuses a different package while the journal is pending;
- addressable contracts: explicit anchors survive file moves and heading renames, slug anchors remain compatible, fenced fake anchors are ignored, oversized sections are rejected instead of truncated, search ranking and archive/reference scopes are deterministic, `check-links` catches broken anchors and root escapes, `context` follows declared links only and distinguishes `not_run`/`passed`/stale evidence, snapshot deltas contain only changed items, and `impact` reports changed sections plus declared consumers without treating text similarity as proven impact.

## Important boundary

These are executable checks of the environment and a local documentation/tooling task, not an end-to-end run of the prompt skills inside an agent runtime. This sandbox contains no product repository, live Jira/chat connector, configured model runtime, acceptance oracle for a product change, reliable local product gate or isolated product-code sandbox. Therefore product-task execution through skills cannot truthfully be reported as tested. Once a real repository/task is provided and pilot prerequisites are approved, add a task-specific acceptance oracle and run it in that isolated environment.

Skills are natural-language instructions, not directly executable code here. Their static contract checks catch omissions/drift but cannot prove an agent follows them; that needs a separately approved tabletop walkthrough or runtime evaluation.
