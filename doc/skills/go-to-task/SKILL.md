---
name: go-to-task
description: Use when the user asks to resume or execute a known task_key. Validate the exact task snapshot and workspace before choosing relevant project context.
status: draft
---

# Skill: go to task

## Procedure
1. Resolve the exact user-provided `task_key`; require the task number/key form implied by its source (Jira bare four digits, UI `UI-` plus four digits, other sources configured prefix plus four digits). list/show/validate with CLI if those commands are available. Do not search by guessed or fuzzy ID.
2. Read the canonical `task.json` and relevant execution/stage records. Preserve its source-aware identity and do not edit the original input silently.
3. Check repository/worktree/base commit/release mapping and dirty state using deterministic CLI. If repository, target release or branch mapping is missing/ambiguous, stop and ask rather than guess.
4. Select project docs/code/tests semantically. Start with architecture README/index, then load only the directly relevant records and expand context on evidence.
5. Clarify blocking acceptance/oracle/scope ambiguity. Record a stage plan when useful; do not create `task.md`.
6. Execute within the configured isolated workspace and permissions. Use one agent for the current core.
7. Run allowed checks; record exact state, commands, results and evidence. A green command/self-report is not approval.
8. Present diffs and unresolved items for human review. Never push/merge/deploy without the explicit policy/command.

## Task.json traceability fields

When reading `task.json`, load and use these fields for full context:

- `task_id` — internal stable ID (e.g. `ui:0001`, `jira:PROJ-123`); used for long-term identity separate from source key.
- `source.revision` / `source.captured_at` — source revision and snapshot timestamp for provenance.
- `kind` — task type (bug, feature, docs, refactor, security, analysis, scaffold); influences risk and review depth.
- `scope.in` / `scope.out` — what is included and explicitly excluded from the task; negative constraints are binding.
- `allowed_files_modules` — file paths/modules the agent is permitted to touch; anything outside requires owner clarification.
- `source.comments` / `source.attachments` / `source.history` — source-side discussion, files and change history.
- `current_behavior` / `evidence` — current observed behavior and evidence paths before changes.
- `contracts_and_invariants` — API/schema/event contracts and invariants that must remain true.
- `related_docs` — architecture document IDs (ENTITY/*, FLOW/*, ADR-*, CAP-*, DOM-*, VIEW-*, SYS-*) that the task touches; load these before touching code.
- `related_tests` — test IDs with `suite` and `location`/`command`; these are the checks that must pass for the task.
- `changed_files.added` / `changed_files.modified` / `changed_files.deleted` — file paths changed in this task; review these before declaring completion.
- `owner` — the task owner; resolve scope/ambiguity questions with them.
- `priority` — task priority; influences how much investigation effort is justified.
- `risk` — risk tier (low/medium/high/critical); determines review depth and approval requirements.
- `authority` — `allowed`/`forbidden`/`approval_required` actions; CLI must not exceed these.
- `task_type` — task type (research/planning/audit/feature/bugfix/docs/refactor/scaffold); determines depth of analysis and review.
- `phase` — lifecycle phase (intake/planning/execution/verification/completed/blocked); resume from current phase.
- `subtasks` — array of {id, title, kind, status, path}; child tasks decomposed from this task.
- `depends_on` — array of task/subtask keys this task depends on; resolve dependencies before starting.
- `rollback_plan` — description of how to roll back changes if verification fails; required for medium/high/critical risk.
- `stage_history` — executed stages with `stage_id`, `status`, `result` and `evidence_refs`; resume from the last incomplete stage, do not repeat completed work.

## Subtasks

Subtasks live in `doc/tasks/<parent_key>/subtasks/<subtask_id>/` with their own `task.json` and `stage1/`:

- Subtasks are **always manual** — no external source binding (no Jira, no tracker).
- Subtask numbering is unique **only within the parent** (`0001`, `0002`, …).
- Each subtask has `parent_task_key` linking back to the parent.
- Subtasks can have their own subtasks (recursive).
- Use `arch task subtask init <parent_key> <subtask_id>` to create; `arch task subtask validate` to validate; `arch task subtask status` to check state.

## Architectural reflection after task completion

When a task completes, the following must be reflected in architectural documentation:

- **ADR**: if the task made an architecturally significant decision (new component, changed boundary, data model change, security trade-off), create/update an ADR in `doc/architecture/decisions/` following MADR template (Context, Drivers, Options, Decision, Consequences).
- **related_docs**: add IDs of architecture documents that were confirmed affected; each affected ENT-*/FLOW-* doc must be updated to reflect the new behavior.
- **changed_files**: update `changed_files` in `task.json` with actual added/modified/deleted paths; keep accurate and minimal.
- **stage_history**: append a completion entry with `stage_id`, `status: completed`, `result`, and `evidence_refs` (commands, outputs, artifact paths).
- **ENT/FLOW docs**: if domain entities or flows changed, update the corresponding `domains/*/entities/ENT-*.md` or `domains/*/flows/FLOW-*.md` pages; do not leave stale descriptions.
- **related_tests**: link test IDs that were executed as verification evidence; no evidence = inconclusive, not pass.

## Stop conditions
Invalid task schema, dirty/unexpected worktree, unsafe IDs/paths, unresolved release mapping, absent oracle, permission failure, or scope change that requires owner clarification.
