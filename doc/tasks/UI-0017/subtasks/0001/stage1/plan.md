# UI-0017-0001 — Формат flow и статические проверки

Статус: verification. Выпуск дорожной карты: v0.2.
Источник: `nextplan.md` §21 и §24, пакет P07.
Зависимости: `UI-0016`.

## Исходное поведение

Flow YAML не имел версии, состояний и переходов. `scan --scope task-conf`
проверял только наличие prompt и порядок шагов, поэтому недостижимые состояния,
неизвестные ссылки и неоднозначные пары `from`/`event` не диагностировались.
Таблица выбора flow отсутствовала.

## Правила проекта

- `REG-cli-validation-rules`: конфиг-driven проверки и явные причины отказа.
- `ENT-flow-definition`: формат `flow-1` и `flow-selection-1`.
- `REG-cli-command-map`: новая команда `task select-flow`.

## Шаги

1. Добавить `schema_version`, `initial_state`, `terminal_states`, `states` и
   `transitions` в два контрольных flow.
2. Добавить `flow.schema.json`, `flow-selection.schema.json` и таблицы выбора.
3. Реализовать семантическую проверку ссылок, недостижимости и неоднозначности
   в `flows.py`; подключить её к `scan --scope task-conf`.
4. Реализовать `task select-flow` с `UNKNOWN-FACT`, `MISSING-FACT` и `CONFLICT`.

## Соответствие приёмке

AC-1: `test_flow_selection_reports_unknown_missing_and_conflict` и
`test_scan_task_conf_reports_unreachable_and_ambiguous_flow`.

## Фактические проверки

Целевые тесты и `scan --scope task-conf --brief` пройдены.
