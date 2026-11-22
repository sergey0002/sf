# Stage 1 plan — simple software-factory scaffold

**Task:** `UI-0001`  
**Input:** `../task.json` (draft schema version; not validated by a final task schema)  
**Basis:** root manifesto and `doc.architecture.md`; unresolved project choices remain open.  
**Outcome:** completed as a documentation/tooling example, not an operational factory.

## Actions

- [x] Create `simple/` project root and root README, without copying the manifest.
- [x] Create domain-first `doc/architecture/` sample from manifest-backed facts; explicitly record unknowns.
- [x] Add capabilities, glossary, entities/data boundaries, flows and system views needed to explain current design.
- [x] Add `doc/tools` Python architecture CLI with list/show/index/validate and unit tests.
- [x] Add tool-neutral `doc/skills` drafts for `create task`, `go to task`, `задокументируй`.
- [x] Keep task input in one `task.json`; use this stage plan rather than creating task.md.
- [x] Add `doc/tests/` acceptance suite covering task-number/source-prefix rules, fixture consistency, architecture-doc integrity and static skill contracts.
- [x] Run CLI validation/index generation and all 13 automated tests; exact commands/results recorded in [verification.json](verification.json).
- [x] Review generated artifacts against AC-1–AC-5; product-task runtime testing remains blocked by missing repository/oracle/CI/sandbox and is not claimed.

## Boundaries

No product code changes, no provider/tracker/CI/repository selection, no final task schema, no merge/deploy, no code scanner, no multi-agent implementation and no empirical pilot. If a check requires an unavailable dependency, report it rather than claiming success.
