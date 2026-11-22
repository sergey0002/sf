# UI-0017 stage2 — Правки по аудиту сессии

Статус: verification. Выпуск дорожной карты: v0.2.
Источник: `doc/tasks/UI-0017/research/kilo-session-audit.md`, §6 P0–P1.
Снимок: текущее рабочее дерево после stage1.

## Исходное поведение

Аудит выявил расхождение исполняемого flow с объявленными `steps`, отсутствие
синхронизации `subtasks[].status` при закрытии, необязательность таблицы выбора
для типов с несколькими flow, неинформативную ошибку `advance` для legacy-flow и
слабую проверку `event` в replay. Процесс использовал shell-чтение вместо
выделенных инструментов и записывал evidence повторно.

## Правила проекта

- `REG-cli-validation-rules`: явные причины отказа и конфиг-driven проверки.
- `ENT-flow-definition`: порядок `steps` — исполняемый контракт.
- `ENT-task-record`: неизменяемый intent, изменяемые `subtasks` и `stage_history`.
- `ARCH-contract`: сохранять совместимость действующих записей.

## Правки

1. `bugfix/standard-implementation`: порядок `fix → review-implementation →
   architecture-sync → verify → close`.
2. `validate_flow_definition`: `states` совпадает с `steps`, `initial_state` —
   первый шаг, между соседними шагами есть переход, переход вперёд не
   пропускает шаг.
3. `task close`: синхронизирует `subtasks[].status` завершённых детей и запись
   `stage_history` текущей стадии; устаревший `snapshot_files` блокирует
   закрытие и без `case-coverage-v1`.
4. `scan --scope task-conf`: требует `flow-selection.yaml` при нескольких
   `allowed_flows`; таблицы добавлены для `feature`, `refactor`, `planning`.
5. `task advance`: `UNSUPPORTED-FLOW` для flow без `flow-1`.
6. `replay_state`: требует непустые `from`, `to`, `event`, `transition_id`.
7. Журнал decompose принимает запись старого формата без shape-полей.
8. `paths.yaml`: зарегистрирован тип `subtask`, который использует scaffold.
9. `go-to-task` и `doc/AGENTS.md`: план до правок, выделенные инструменты,
   `--brief`, `todowrite`, evidence один раз на финальном снимке.

## Соответствие приёмке

| Критерий | Проверка |
|---|---|
| AC-1: возврат `verify → fix` и короткий docs-путь | `test_bugfix_flow_returns_from_verify_to_fix_and_rejects_stale_events`, `test_docs_only_flow_short_path_without_children` |
| AC-2: явные причины отказа и неизменное состояние | `test_scan_requires_step_consistency_and_selection_table`, `test_advance_reports_unsupported_flow_for_legacy_template`, `test_stale_evidence_blocks_close_without_case_policy` |
| AC-2: согласованная запись при закрытии | `test_close_syncs_subtask_status_and_stage_history` |

## Фактические проверки

Целевые тесты и полный `test_task_identity.py` пройдены. `scan --scope all`,
`docs paths --check`, `index check` и `bash doc/tests/run.sh --brief` пройдены.
