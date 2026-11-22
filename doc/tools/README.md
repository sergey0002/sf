# Architecture documentation CLI

Small deterministic helper for `doc/architecture/`. It validates structure and references; it does **not** judge truth, select semantically relevant documents, classify content, or author prose. Agents may edit Markdown directly.

## Requirements / invocation

From `simple/`:

```sh
python3 -m pip install -r doc/tools/requirements.txt
python3 doc/tools/arch.py list
python3 doc/tools/arch.py list --domain task-intake
python3 doc/tools/arch.py show CAP-task-intake
python3 doc/tools/arch.py index build
python3 doc/tools/arch.py index check
python3 doc/tools/arch.py validate
python3 doc/tools/arch.py task-key --source jira --number 0042
python3 doc/tools/arch.py task-key --source ui --number 0042
python3 doc/tools/arch.py task-key --source github --prefix GH --number 0042
python3 -m unittest discover -s doc/tools/tests -v
```

Index build is an explicit deterministic write. Other commands are read-only. `index.json` is generated and must not be hand-edited. The CLI requires Python 3.10+ and the pinned-major dependency ranges in requirements.txt.

## Guarantees and limitations

- Safe YAML parsing, duplicate key rejection, JSON Schema Draft 2020-12 validation, unique IDs, local Markdown path existence and `related` ID resolution.
- Index generated in stable ID order and atomically replaced.
- `show` and `list` require exact metadata/ID; they do not search semantically. `task-key` validates exactly four decimal digits and derives Jira/UI/other-source keys; it does not allocate or reserve numbers.
- External links are not fetched. Markdown syntax and semantic completeness are not fully validated. Anchors in local links are not checked. Markdown parsing is deliberately lightweight; review tool limits before treating it as a security boundary.
- Schema and CLI are illustrative contracts, not approved production schemas.
