# UI-0017 — Два контрольных flow и зависимости детей

Статус: verification. Выпуск дорожной карты: v0.2.
Источник: `nextplan.md` §21 и §24, пакет P07.
Зависимости: `UI-0016`.

## Исходное поведение

До изменения CLI загружал `steps` flow и выдавал prompts, но не вычислял
состояния и переходы, не применял таблицу выбора flow и не показывал
готовность детей. `subtasks[].depends_on` не проверялся, а `task decompose`
не принимал зависимости. Схемы `flow-1` и `flow-selection-1` отсутствовали.

## Правила проекта

- `ARCH-contract` и `REG-cli-validation-rules`: структура `task.json`,
  совместимость старых записей и конфиг-driven проверки.
- `ENT-task-record`: неизменяемый intent, ревизия, идемпотентность и журнал.
- `REG-cli-command-map`: имена и границы команд сохраняются.
- `ENT-flow-definition`: новый контракт состояний, переходов и выбора flow.

## Объём

- `doc/config/task-conf/types/bugfix/flows/standard-implementation/config.yaml`
- `doc/config/task-conf/types/docs/flows/docs-only/config.yaml`
- `doc/config/task-conf/types/bugfix/flow-selection.yaml`
- `doc/config/task-conf/types/docs/flow-selection.yaml`
- `doc/architecture/schemas/flow.schema.json`
- `doc/architecture/schemas/flow-selection.schema.json`
- `doc/tools/arch/flows.py`
- `doc/tools/arch/task_record.py`
- `doc/tools/arch/task_ops.py`
- `doc/tools/arch/validation.py`
- `doc/tools/arch/cli/commands/task.py`
- `doc/tools/arch/cli/commands/builtin.py`
- `doc/config/paths.yaml`
- `doc/tests/test_task_identity.py`
- архитектурные документы и записи задачи

## Шаги

1. Описать версионированные `bugfix/standard-implementation` и
   `docs/docs-only`, таблицы выбора и JSON-схемы.
2. Реализовать `task select-flow`, `task advance`, проверку схемы flow,
   `flow.transitioned` в журнале и `flow_state` в состоянии.
3. Реализовать `--subtask-depends-on`, проверку ссылок и циклов до записи,
   `ready`/`blocked`/`blocked_by` в `diagnose`.
4. Добавить fixtures для возврата `verify → fix`, короткого `docs-only`,
   повторного события, stale revision, неизвестного события, конфликта правил,
   цикла и недостижимого состояния.

## Соответствие приёмке

| Критерий | Проверка |
|---|---|
| AC-1: багфикс проходит `verify → fix`; `docs-only` без детей | `test_bugfix_flow_returns_from_verify_to_fix_and_rejects_stale_events`, `test_docs_only_flow_short_path_without_children` |
| AC-2: неизвестный вход, конфликт, циклы и битые ссылки объяснимы; отказ не меняет состояние | `test_flow_selection_reports_unknown_missing_and_conflict`, `test_subtask_dependencies_compute_ready_blocked_and_cycles`, `test_scan_task_conf_reports_unreachable_and_ambiguous_flow`, проверки неизменности `state.json` |

## Фактические проверки

Целевой селектор новых сценариев и полный `test_task_identity.py` пройдены.
`scan --scope task-conf`, `scan --scope docs`, `docs paths --check` и
`index check` пройдены после пересборки индекса. Полный `scan --scope all`
содержит посторонний незавершённый `doc/tasks/UI-0027`, созданный вне этой
задачи; он не входит в scope и не изменялся.

## Закрытие

Зависимость `UI-0016` завершена. После проверки evidence дочерние записи
закрываются, затем закрывается родитель. Внешние действия и публикация не
выполняются.
