# UI-0017-0002 — Переходы и готовность подзадач

Статус: verification. Выпуск дорожной карты: v0.2.
Источник: `nextplan.md` §21 и §24, пакет P07.
Зависимости: `UI-0016`, `UI-0017-0001`.

## Исходное поведение

`task diagnose` не возвращал `flow_state` и доступные переходы. `task advance`
отсутствовал. Зависимости детей не объявлялись и не проверялись; `ready` и
`blocked` не вычислялись.

## Правила проекта

- `ENT-task-record`: ревизия, идемпотентность и append-only журнал.
- `ENT-flow-definition`: переходы, `flow_state` и готовность детей.
- `REG-cli-validation-rules`: отказ не меняет состояние.

## Шаги

1. Добавить `flow.transitioned`, `flow_state` в `state.json` и `task advance`.
2. Проверять `expected_revision`, повтор `--id`, неизвестное событие и
   неоднозначный переход до записи.
3. Добавить `--subtask-depends-on`, проверку ссылок и циклов до записи.
4. Вычислять `ready`, `blocked`, `blocked_by` в `inspect_subtasks` и сводку в
   `diagnose`.
5. Проверить возврат `verify → fix`, короткий `docs-only`, stale revision,
   повтор события, цикл и отсутствие записи при отказе.

## Соответствие приёмке

AC-1: `test_bugfix_flow_returns_from_verify_to_fix_and_rejects_stale_events`,
`test_docs_only_flow_short_path_without_children`,
`test_subtask_dependencies_compute_ready_blocked_and_cycles`.

## Фактические проверки

Целевые тесты и полный `test_task_identity.py` пройдены.
