---
name: create-task
description: Use when the user asks to create a task from chat/user input (`ui`) or a configured tracker. Clarify blocking ambiguity and produce the single canonical task.json; never create a parallel task.md.
status: draft
---

# Skill: create task

## Purpose

Turn a manual/chat request into a source-aware normalized `task.json` following the project task schema once that schema exists. The skill also performs decomposition, complexity evaluation, type/flow selection, and creates subtasks via CLI.

## Procedure

1. **Identify intent and source.** Determine explicit intent, task kind if known, scope/non-goals, acceptance criteria and verification/oracle refs, constraints, assumptions, open questions, target release, approvals and source attachments/references. Treat requests entered by a user as `source.type: ui`; Jira is `source.type: jira`; other sources keep their source type.

2. **Ask about ambiguity.** Ask the user about ambiguity that blocks safe deterministic setup or acceptance. Do not infer repository, release/branch, owners, priority, requirements, test oracle or technology.

3. **Select task type.** Choose a `task_type` from `doc/config/task-conf/types/*/config.yaml`:
   - `jira-incoming` — входящая задача из Jira (единственный flujo `jira-process`)
   - `feature` — новая функциональность или расширение существующей
   - `bugfix` — исправление дефекта
   - `docs` — только документация/скиллы/конфиги
   - `refactor` — улучшение структуры без изменения поведения
   - `research` — исследование, desk research, сравнение вариантов
   - `planning` — технический план, спецификация, ADR
   - `audit` — аудит документации, кода или архитектуры
   - `scaffold` — создание каркаса задачи

   Прочти `prompt.md` выбранного типа — это стартовый промпт (по принципу скилла), исполняемый при начале работы над задачей этого типа.

4. **Select flow.** Choose a `flow` from `doc/config/task-conf/types/<type>/flows/<flow>/config.yaml` allowed for the selected type (see `arch task flows --type <type>`). The flow is locked to the task and read during execution; its `prompt.md` defines how the agent should carry out the task. Прочти `prompt.md` выбранного flujo.

5. **Evaluate complexity.** Assign `complexity` (low/medium/high/critical) based on scope, number of affected modules, risk, and whether cross-team approval is needed. Use `complexity_default` from the type config as a starting point.

6. **Derive task key.** Require every task to have a four-decimal-digit task number. Derive the key deterministically: Jira `1234` (no prefix), UI/user input `UI-1234`, every other source `<EXPLICIT_PREFIX>-1234`. Ask the user to supply a number or use a separately approved deterministic allocator if one is configured; otherwise stop. Never invent or allocate one yourself.

7. **Create task.json.** Save one `task.json` with fields: `task_key`, `task_number`, `source`, `title`, `kind`, `intent`, `scope`, `acceptance_criteria`, `target_release`, `project_context_refs`, `constraints`, `assumptions`, `open_questions`, `risk`, `authority`, `approvals`, `task_type`, `flow`, `complexity`, `subtasks`, `depends_on`, `phase`, `rollback_plan`, `related_docs`, `related_tests`, `changed_files`, `owner`, `priority`, `stage_history`. Do not author a separate `task.md`.

8. **Decompose into subtasks (if required by type config).** If the type config has `subtask_policy: required`, create subtasks via `arch task decompose <task_key> --subtask-id NNNN --subtask-title "..."` (repeatable). Each subtask gets its own `task.json` and `stage1/`. Subtasks are always manual — no external source binding.

9. **Run CLI validation.** Run `arch task validate <task_key>` and `arch docs paths --check`. Do not claim the task is created/executable if validation did not occur.

## Subtask closure policy

A task with `close_policy: all_subtasks_required` (all type configs) can be closed only when every subtask has `phase: completed`. Use `arch task diagnose <task_key>` to check subtask status and blockers; use `arch task close <task_key>` to close after all subtasks are completed and approval obtained.

## Reading type and flow prompts

- `arch task type-prompt --type <type>` — стартовый промпт типа (как скилл).
- `arch task flow-prompt --type <type> --flow <flow>` — стартовый промпт flujo.

## Must not

- Write to the external tracker unless an explicit approved command/policy exists.
- Use an untrusted native ID directly as a path.
- Decide semantic completeness with regex/CLI heuristics.
- Silently rewrite an original task snapshot after task execution begins.
- Create `task.md` as an alternative to `task.json`.
- Allocate a task number automatically; numbers come from the user or an approved allocator.
