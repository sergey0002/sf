---
name: задокументируй
description: Use only when the user explicitly asks to record confirmed decisions, implementation facts or evidence from the current conversation.
status: draft
---

# Skill: задокументируй

## Procedure
1. Review only available conversation facts, current diff/status and actual command/test outputs. Separate confirmed implemented behavior, accepted decision, proposal/hypothesis and unresolved question.
2. Detect whether an active task/stage exists. If yes, record the session delta in that task/stage and prepare an architecture delta only if canonical behavior/decision changed. If no task exists, update only clearly relevant architecture docs; do not create a task retroactively.
3. Never silently rewrite the original `task.json`. Preserve task/source/stage/commit/test refs.
4. Semantic relevance and wording are agent-owned. Use index-first retrieval and load only affected docs/evidence.
5. Make a minimal Markdown diff. Keep proposals separate from accepted current state. Do not create a document solely to capture chat history.
6. Run architecture CLI structural validation and index check when available. CLI cannot decide that content is semantically true or approved.
7. Report exactly what was changed and which checks actually passed. Never claim tests or human approval without evidence.

## Task.json traceability fields

When recording session results, update `task.json` traceability fields:

- `task_id` — internal stable ID; use for long-term identity separate from source key.
- `kind` — task type (bug, feature, docs, refactor, security, analysis, scaffold); influences risk and review depth.
- `scope.in` / `scope.out` / `allowed_files_modules` — record what was actually changed; verify changes stay within allowed scope.
- `current_behavior` / `evidence` — record observed current behavior before changes; attach evidence paths.
- `contracts_and_invariants` — confirm which contracts/invariants remain true after changes.
- `source.comments` / `source.attachments` / `source.history` — source-side discussion, files and change history.
- `changed_files.added` / `changed_files.modified` / `changed_files.deleted` — actual file paths changed in this session; keep them accurate and minimal.
- `related_tests` — test IDs actually executed, with `suite` and `location`/`command`; do not claim tests that were not run.
- `related_docs` — architecture document IDs that were confirmed affected; add new IDs only when canonical behavior/decision changed.
- `owner` — the task owner; resolve scope/ambiguity questions with them.
- `priority` — task priority.
- `risk` — risk tier (low/medium/high/critical); determines review depth.
- `authority` — `allowed`/`forbidden`/`approval_required`; record which approvals were obtained.
- `task_type` — task type (research/planning/audit/feature/bugfix/docs/refactor/scaffold).
- `phase` — lifecycle phase (intake/planning/execution/verification/completed/blocked); update as work progresses.
- `subtasks` — array of {id, title, kind, status, path}; add child task IDs as they are created.
- `depends_on` — array of task/subtask keys this task depends on.
- `rollback_plan` — description of how to roll back; record when changes are made.
- `stage_history` — append an entry for each executed stage with `stage_id`, `status` (`in_progress`, `completed`, `blocked`), `result` summary and `evidence_refs` (commands, outputs, artifact paths).

Never silently rewrite the original `task.json` input snapshot; append-only amendments are preferred for new decisions.

## Subtasks

Subtasks live in `doc/tasks/<parent_key>/subtasks/<subtask_id>/` with their own `task.json` and `stage1/`:

- Subtasks are **always manual** — no external source binding.
- Subtask numbering is unique **only within the parent** (`0001`, `0002`, …).
- Each subtask has `parent_task_key` linking back to the parent.
- Subtasks can have their own subtasks (recursive).
- When recording session results, update `subtasks` array in parent `task.json` with child IDs and their status.

## Architectural reflection after task completion

When a task completes, the following must be reflected in architectural documentation:

- **ADR**: if the task made an architecturally significant decision (new component, changed boundary, data model change, security trade-off), create/update an ADR in `doc/architecture/decisions/` following MADR template (Context, Drivers, Options, Decision, Consequences).
- **related_docs**: add IDs of architecture documents that were confirmed affected; each affected ENT-*/FLOW-* doc must be updated to reflect the new behavior.
- **changed_files**: update `changed_files` in `task.json` with actual added/modified/deleted paths; keep accurate and minimal.
- **stage_history**: append a completion entry with `stage_id`, `status: completed`, `result`, and `evidence_refs` (commands, outputs, artifact paths).
- **ENT/FLOW docs**: if domain entities or flows changed, update the corresponding `domains/*/entities/ENT-*.md` or `domains/*/flows/FLOW-*.md` pages; do not leave stale descriptions.
- **related_tests**: link test IDs that were executed as verification evidence; no evidence = inconclusive, not pass.

## Must not

- Dump the full transcript into architecture docs.
- Turn hypotheses into facts, or intended work into implemented behavior.
- Add a task without a user request.
- Write to tracker/PR or merge/deploy without explicit permission.
