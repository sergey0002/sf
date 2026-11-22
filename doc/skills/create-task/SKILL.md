---
name: create-task
description: Use when the user asks to create a task from chat/user input (`ui`) or a configured tracker. Clarify blocking ambiguity and produce the single canonical task.json; never create a parallel task.md.
metadata:
  status: draft
---

# Skill: create task

## Purpose

Turn a manual or configured tracker request into a normalized `task.json` validated against the current project YAML. Use [doc/AGENTS.md](../../AGENTS.md) for the command entry point and source precedence. Creating a card ends with a verified plan and intended checks. Start implementation when requested.

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

6. **Derive task key.** Require every task to have a four-decimal-digit task number. Derive the key deterministically: Jira `1234` (no prefix), UI/user input `UI-1234`, every other source `<EXPLICIT_PREFIX>-1234`. Use the number or range authorized by the owner, the [number registry](../../architecture/system/task-number-registry.md), or an approved allocator if configured. If none provides an assignment, prepare the plan and request the number. Never invent or allocate one yourself. Check the registry and disk before writing, for every key in a batch.

7. **Create task.json.** Save one `task.json` with fields: `task_key`, `task_number`, `source`, `title`, `kind`, `intent`, `scope`, `acceptance_criteria`, `target_release`, `project_context_refs`, `constraints`, `assumptions`, `open_questions`, `risk`, `authority`, `approvals`, `task_type`, `flow`, `complexity`, `subtasks`, `depends_on`, `phase`, `rollback_plan`, `related_docs`, `related_tests`, `changed_files`, `owner`, `priority`, `stage_history`. Do not author a separate `task.md`.

8. **Plan and decompose.** Give each acceptance criterion an `AC-N` with an observable result and a check or reviewer. Put steps in `stage1/plan.md`. When planned checks need recording, start `stage1/verification.json` with `status: not_run` and no executed results. Add children for independently verifiable outcomes; obey the type's `subtask_policy`. Record `depends_on` with exact task or child keys. Check duplicates, missing references and cycles before writing. Use `arch task decompose <task_key> --subtask-id NNNN --subtask-title "..."` for scaffolding. The current command can write part of a batch before a later conflict, so preflight all IDs and paths. Complete each child's own record and plan.

9. **Validate and register.** Validate the parent with `arch task validate <task_key>` and each immediate child with `arch task subtask validate <parent> <id>`. Cross-check the parent's child paths against the files. Update the number registry and run `arch docs paths --check`. Report keys and any unresolved blockers. Claim implementation or test results only when separately verified.

## Subtask closure policy

Use [go-to-task](../go-to-task/SKILL.md) for readiness checks and closing an implemented task.

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
