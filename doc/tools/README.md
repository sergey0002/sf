# Architecture documentation CLI

Small deterministic helper for `doc/architecture/`. It validates structure and references; it does **not** judge truth, select semantically relevant documents, classify content, or author prose. Agents may edit Markdown directly.

## Requirements / invocation

For task commands, output formats and side effects, use the [Arch CLI operator skill](../skills/arch-cli/SKILL.md) and the relevant command's `--help`.

Install as a package to get the `arch` console script:

```sh
python3 -m pip install -r doc/tools/requirements.txt
python3 -m pip install .
arch --version
```

`arch --version` reports the version from `arch.__version__`, which matches the package metadata in `pyproject.toml`. The installed package still reads project files through `--root`.

From the repository root without installing:

```sh
python3 -m pip install -r doc/tools/requirements.txt
python3 doc/tools/arch/__main__.py list
python3 doc/tools/arch/__main__.py list --domain task-intake
python3 doc/tools/arch/__main__.py show CAP-task-intake
python3 doc/tools/arch/__main__.py index build
python3 doc/tools/arch/__main__.py index check
python3 doc/tools/arch/__main__.py validate
python3 doc/tools/arch/__main__.py docs paths --check
python3 doc/tools/arch/__main__.py task-key --source jira --number 0042
python3 doc/tools/arch/__main__.py task-key --source ui --number 0042
python3 doc/tools/arch/__main__.py task-key --source github --prefix GH --number 0042
python3 doc/tools/arch/__main__.py session find --match "фраза" --json
python3 doc/tools/arch/__main__.py session digest <session_id> --json
python3 -m unittest discover -s doc/tools/tests -v
```

All structured commands emit the single JSON envelope `{ok, code, data, errors, hints}`. `task-key` output is available under `data`.

Entry points are the installed `arch` console script, `python3 -m arch` from `doc/tools/`, and direct execution of `doc/tools/arch/__main__.py`. They dispatch to the same `arch.cli.app.run()`.

Index build and task mutations are explicit writes. Inspection, validation and closure preview are read-only. `index.json` is generated and must not be hand-edited. CI runs `index check` before any rebuild and verifies a reproducible rebuild in a separate tree. The CLI requires Python 3.10+ and the pinned-major dependency ranges in requirements.txt.

## Guarantees and limitations

- Safe YAML parsing, duplicate key rejection, JSON Schema Draft 2020-12 validation, unique IDs, local Markdown path existence and `related` ID resolution.
- Index generated in stable ID order and atomically replaced.
- Task records are replaced atomically. `task decompose` validates the whole package before writing and records a journal so an interrupted composite write can be resumed; a pending journal blocks closure until recovery.
- A versioned task record keeps immutable intent in `task.json`, mutable state in `state.json` and an append-only `events.jsonl` journal. `task migrate` is repeatable, `task event` rejects a stale `expected_revision` and repeats an identical `--id` without a second write, and `task replay` rebuilds `state.json` only from a verified journal chain.
- `show` and `list` require exact metadata/ID; they do not search semantically. `task-key` validates exactly four decimal digits and derives Jira/UI/other-source keys; it does not allocate or reserve numbers.
- External links are not fetched. Markdown syntax and semantic completeness are not fully validated. Anchors in local links are not checked. Markdown parsing is deliberately lightweight; review tool limits before treating it as a security boundary.
- Schema and CLI are illustrative contracts, not approved production schemas.
