---
id: ENT-flow-definition
type: entity
title: Версионированный flow и таблица выбора
summary: "YAML-описание состояний, переходов и правил выбора flow, которое CLI проверяет и применяет к задаче."
status: draft
domain: task-lifecycle
related: [ENT-task-record, FLOW-task-lifecycle, REG-cli-command-map, REG-cli-validation-rules]
implemented: true
---

# Версионированный flow и таблица выбора

## Назначение

Flow фиксирует начальное и конечные состояния, объявленные состояния и
переходы по событиям. Таблица выбора применяет типизированные факты к
стабильным правилам и возвращает flow вместе с основанием. Запущенная задача
хранит `flow_version`, поэтому правка YAML не меняет доступные переходы задним
числом.

## Концептуальное содержание

Flow с `schema_version: flow-1` содержит `initial_state`, `terminal_states`,
`states` и `transitions`. Переход имеет `id`, `from`, `event`, `to` и
необязательный `when`. `task diagnose` показывает текущий `flow_state` и
доступные переходы, `task advance` применяет одно событие. `scan --scope
task-conf` проверяет ссылки, недостижимые состояния и неоднозначные пары
`from`/`event`.

Если объявлены `steps`, их порядок — исполняемый контракт. `states` совпадает
с ID шагов, `initial_state` — первый шаг, между соседними шагами есть переход,
а переход вперёд не пропускает шаг. Обратные переходы (`verify → fix`) остаются
допустимыми. Так документация и `task advance` не расходятся.

Таблица `types/<type>/flow-selection.yaml` содержит `facts` и `rules`. Правило
без `fallback` требует непустой `when`; fallback допускается один и применяется
после проверки остальных правил. `task select-flow` возвращает `rule_id`, flow и
основание, а при неполном или конфликтующем входе — явную причину. Тип с
несколькими `allowed_flows` обязан иметь таблицу; иначе `scan` сообщает об
отсутствующем файле.

```yaml
schema_version: flow-1
id: docs-only
type: docs
initial_state: architecture-context
terminal_states: [close]
states: [architecture-context, change, validate, close]
transitions:
  - id: docs.context.ready
    from: architecture-context
    event: context.ready
    to: change
```

`subtasks[].depends_on` связывает непосредственных детей. `diagnose` и `close`
вычисляют `ready`, `blocked` с `blocked_by` или `completed`. `task decompose`
проверяет неизвестные ссылки и циклы до записи.

При закрытии `subtasks[].status` завершённых детей и текущая запись
`stage_history` синхронизируются, а устаревший `snapshot_files` блокирует
закрытие даже без `case-coverage-v1`.

## Инварианты

- Переход применяется только из текущего `flow_state` и по объявленному событию.
- `expected_revision` защищает от записи поверх изменившегося состояния; повтор
  того же `event_id` с тем же содержимым не создаёт вторую запись.
- Неизвестное событие, конфликт правил выбора и цикл зависимостей не меняют
  задачу.
- `flow_version` в записи задачи остаётся неизменным после миграции.

## Evidence

Реализация: `doc/tools/arch/flows.py`, `doc/tools/arch/task_record.py`,
`doc/tools/arch/task_ops.py`, `doc/tools/arch/validation.py`. Проверки:
`doc/tests/test_task_identity.py` (выбор flow, возврат `verify → fix`, короткий
`docs-only`, готовность детей и диагностика схемы).
