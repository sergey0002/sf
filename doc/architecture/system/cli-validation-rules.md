---
id: REG-cli-validation-rules
type: rule-set
title: Правила валидации task.json и ограничения перечислений
summary: "Перечисляет все валидируемые поля task.json, принимаемые ими перечисления и условия ошибок, которые применяет CLI."
status: draft
domain: system
related: [ENT-task-input, REG-cli-command-map, DOM-task-lifecycle]
implemented: true
---

# Правила валидации task.json

`validate_task_json()` в `doc/tools/arch/validation.py` валидирует разобранную структуру `task.json` и возвращает список человекочитаемых сообщений об ошибках (пустой, если валидно).
Валидация полностью **конфиг-driven**: все enum'ы, обязательные поля, `allowed_flows`, `complexity_levels` читаются из YAML-конфигов. В Python-коде нет хардкода.
Семантические решения (например, должна ли задача быть декомпозирована) принадлежат агенту/скиллам, а не CLI.

## Источники правил

| Источник | Что задаёт |
|----------|-----------|
| `doc/config/paths.yaml` (секция `project`) | `task_types`, `phases`, `risk_levels`, `source_types`, базовые `task_schema_required_fields` |
| `doc/config/task-conf/types/<type>/config.yaml` | `required_fields`, `allowed_flows`, `complexity_allowed`, `subtask_policy`; `close_policy` описывает процесс закрытия |

## Обязательные поля

Обязательные поля = базовые из `paths.yaml` (`task_schema_required_fields`) + типовые из `task-conf/types/<type>/config.yaml` (`required_fields`). Объединяются без дублей.

Базовые обязательные поля (из `paths.yaml`):

| Поле | Тип | Ограничение |
|------|-----|-------------|
| `schema_version` | строка | должно быть присутствовать |
| `task_key` | строка | должно совпадать с именем директории |
| `task_number` | строка | ровно четыре десятичные цифры (`^[0-9]{4}$`) |
| `source` | объект | `type` ∈ `project.source_types` |
| `title` | строка | должно быть присутствовать |
| `intent` | строка | должно быть присутствовать |
| `scope` | объект | `in` и `out` (если присутствуют) должны быть массивами |
| `acceptance_criteria` | массив | должно быть присутствовать |
| `target_release` | строка | должно быть присутствовать |
| `project_context_refs` | массив | должно быть присутствовать |
| `constraints` | массив | должно быть присутствовать |
| `assumptions` | массив | должно быть присутствовать |
| `open_questions` | массив | должно быть присутствовать |
| `approvals` | массив | должно быть присутствовать |
| `risk` | строка | ∈ `project.risk_levels` |
| `authority` | объект | `allowed`/`forbidden`/`approval_required` (если присутствуют) должны быть массивами |
| `task_type` | строка | ∈ `project.task_types` |
| `flow` | строка | slug, должен быть в `allowed_flows` типа |
| `complexity` | строка | ∈ `complexity_allowed` типа |
| `subtasks` | массив объектов | каждый требует `id`, `title`, `status`, `path` |
| `depends_on` | массив | должен быть массивом, если присутствует |
| `phase` | строка | ∈ `project.phases` |
| `rollback_plan` | строка | null | должна быть строкой или `null` |
| `related_docs` | массив строк | каждая должна совпадать с `TASK_KEY_RE` |
| `related_tests` | массив объектов | каждый требует `test_id` и `location` |
| `research_docs` | массив объектов | каждый требует `id`, `title`, `path`, `source_type`, `source_ref`, `summary`, `status` |
| `changed_files` | объект | `added`/`modified`/`deleted` (если присутствуют) должны быть массивами |
| `owner` | строка | валидируется, если присутствует |
| `priority` | строка | валидируется, если присутствует |
| `stage_history` | массив объектов | каждый требует `stage_id` и `status` |
| `task_id` | строка | валидируется, если присутствует |
| `kind` | строка | валидируется, если присутствует |
| `implementation_plan` | строка | требуется для типов с `required_fields` |
| `current_behavior` | строка | валидируется, если присутствует |
| `evidence` | массив | валидируется, если присутствует |
| `contracts_and_invariants` | массив | валидируется, если присутствует |
| `allowed_files_modules` | массив | валидируется, если присутствует |

## Объект `source`

| Подполе | Тип | Ограничение |
|---------|-----|-------------|
| `type` | строка | ∈ `project.source_types` (jira, ui, other) |
| `attachments`, `comments`, `history` | массив | валидируется, если присутствует |
| `native_id`, `provenance`, `revision`, `captured_at` | любой | присутствует в скффолде, не ограничивается, кроме типа |

## Исследовательская папка `research/` — поле `research_docs`

| Подполе | Тип | Ограничение |
|---------|-----|-------------|
| `id` | строка | стабильный идентификатор исследования внутри задачи |
| `title` | строка | человек-читаемое название |
| `path` | строка | должен быть под `doc/tasks/<task_key>/research/` и заканчиваться на `.md` |
| `source_type` | строка | `web` | `code` | `internal` |
| `source_ref` | строка | URL, путь к коду или ссылка на внутренний документ |
| `summary` | строка | краткое суть исследования / гипотезы |
| `status` | строка | `hypothesis` | `confirmed` | `rejected` | `archived` |

## Субтаски и зависимости

| Поле | Тип | Ограничение |
|------|-----|-------------|
| `subtasks` | массив объектов | каждый требует `id`, `title`, `status`, `path` |
| `subtask_policy` | строка (из task-conf) | `required` → subtasks не пуст; `forbidden` → subtasks пуст; `optional` → без ограничений |
| `depends_on` | массив | должен быть массивом, если присутствует |
| `rollback_plan` | строка | null | должна быть строкой или `null` |

## Управление типами и flujo (task-conf)

| Поле | Ограничение |
|------|-------------|
| `task_type` | должен быть зарегистрирован в `doc/config/task-conf/types/*/config.yaml` |
| `flow` | должен быть в `allowed_flows` для выбранного `task_type` |
| `complexity` | должен быть в `complexity_allowed` для выбранного `task_type` |

Поля `steps`, `action`, `output` и `gate` задают порядок работы агента. CLI перечисляет потоки и выдаёт prompts. При закрытии CLI проверяет карточку и непосредственных детей. Если включена политика `case-coverage-v1`, проверяются план, обязательные кейсы и хеши заявленных файлов. Агент сверяет смысл приёмки и одобрение. [Запись доказательств](../domains/task-lifecycle/entities/verification-evidence.md) · [Поток жизненного цикла](../domains/task-lifecycle/flow.md)

## Условия ошибок

- `task.json` не является JSON-объектом → одна ошибка
- Отсутствующее обязательное поле → `task.json: missing required field <имя>`
- Несовпадение `task_key` с директорией → ошибка
- `task_number` не четыре цифры → ошибка
- `source.type` не из `project.source_types` → ошибка
- Неверный `task_type` / `phase` / `risk` → ошибка с указанием поля
- `flow` не в `allowed_flows` типа → ошибка
- `complexity` не в `complexity_allowed` типа → ошибка
- `subtask_policy: required` но `subtasks` пуст/отсутствует → ошибка
- `subtask_policy: forbidden` но `subtasks` не пуст → ошибка
- Неверный элемент `subtasks` (отсутствует `id`/`title`/`status`/`path`) → ошибка
- `depends_on` не является массивом → ошибка
- `rollback_plan` не строка и не null → ошибка
- `task.md` существует рядом с `task.json` → ошибка (правило манифеста)
- `research_docs` элемент с неверным `source_type` / `status` / `path` → ошибка

## Пример валидного скффолда

```json
{
  "schema_version": "draft-0.2",
  "task_key": "UI-0001",
  "task_number": "0001",
  "source": {"type": "ui", "native_id": null, "provenance": "created by arch task init"},
  "task_type": "feature",
  "flow": "standard-implementation",
  "complexity": "medium",
  "phase": "intake",
  "subtasks": [],
  "depends_on": [],
  "rollback_plan": null,
  "implementation_plan": "...",
  ...
}
```
