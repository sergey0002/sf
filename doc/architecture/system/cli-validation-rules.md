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
| `doc/config/paths.yaml` (секция `project`) | `task_types`, `phases`, `task_statuses`, `risk_levels`, `source_types`, базовые `task_schema_required_fields`, `release` (дефолты релиза и веток) |
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
| `target_release` | строка | должно быть присутствовать; при `project.release.enforce: true` не `unset` |
| `branch` | строка | рабочая ветка задачи; валидное имя git-ветки; при `enforce: true` не `unset` |
| `release_branch` | строка | ветка мерджа; валидное имя git-ветки; при `enforce: true` не `unset` |
| `status` | строка | ∈ `project.task_statuses`, если присутствует; отдельная ось от `phase` |
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
| `subtasks` | массив объектов | каждый требует `id`, `title`, `status`, `path`; запись может содержать `task_type`, `flow`, `complexity`, `estimate_hours` ребёнка |
| `subtask_policy` | строка (из task-conf) | `required` → subtasks не пуст; `forbidden` → subtasks пуст; `optional` → без ограничений |
| `depends_on` | массив | должен быть массивом, если присутствует |
| `rollback_plan` | строка | null | должна быть строкой или `null` |
| `estimate_hours` | число | положительное число часов; ставит агент, CLI проверяет диапазон |

## Политика плана и правила приёмки

`doc/config/task-conf/plan-defaults.yaml` задаёт дефолтные tier'ы и safety floor. `types/<type>/config.yaml` может объявить `plan` и `acceptance.rules`. Разрешение идёт `type → defaults`; `scan --scope task-conf` сверяет выбираемые типы с `paths.yaml task_types`, шаблоны, покрытие complexity и ссылки на правила. `selectable: false` обозначает legacy-тип и не требует записи в `task_types`.

## Релиз, ветка задачи и ветка мерджа

`project.release` в `paths.yaml` задаёт дефолты для новых карточек: `default_branch` (`main`), `default_release` (`0.1.0`) и `branch_patterns` по `source.type` (`jira` → `futures/{task_number}`, `ui` → `bugfix/{task_key}`, `other` → `task/{task_key}`). `task new`/`task init` подставляют их в скаффолд, а `task decompose`/`task subtask init` наследуют значения родителя (UI-0027 AC-5). Инвариант: скаффолд обязан проходить `task validate` сразу после создания — новое обязательное поле требует дефолта в скаффолде, миграции корпуса и теста `init → validate`. Флаг `enforce` включает обязательность полей; контракт Git-операций (подготовка, публикация, интеграция) принадлежит UI-0027.

Правила приёмки декларативны и проверяются общим оценщиком:

| Kind | Параметры | Что проверяется |
|---|---|---|
| `section_present` | `section` | заголовок с этим текстом существует |
| `section_min_items` | `section`, `min` | в разделе не меньше `min` пунктов списка или строк таблицы |
| `link_min` | `section`, `min` | в разделе не меньше `min` ссылок или inline-кода |
| `table_column` | `section`, `column` | в таблице раздела есть колонка |
| `case_min` | `min` | `planned_checks` покрывает не меньше `min` кейсов |
| `command` | `command` | команда присутствует в плане |

Дополнительно правило может иметь `when` (флаг карточки или список флагов, например `[contract_change, storage_change]`) и `applies_to` (tier'ы). Без `applies_to` правило действует на `standard` и `full`; floor-правила из дефолтов действуют на всех tier'ах. Правила типа дополняют floor, а не заменяют его. Неизвестный `kind` или ссылка на неизвестное правило — ошибка конфигурации. Смысл оракула CLI не оценивает: он подтверждает только объявленную структуру и называет файл, раздел и правило.

План без маркера `<!-- plan-tier: ... -->` не оценивается правилами типа: карточки без `estimate_hours` сохраняют прежнее поведение.

## Управление типами и flujo (task-conf)

| Поле | Ограничение |
|------|-------------|
| `task_type` | должен быть зарегистрирован в `doc/config/task-conf/types/*/config.yaml` |
| `flow` | должен быть в `allowed_flows` для выбранного `task_type` |
| `complexity` | должен быть в `complexity_allowed` для выбранного `task_type` |

Поля `steps`, `action`, `output` и `gate` задают порядок работы агента. CLI перечисляет потоки и выдаёт prompts. При закрытии CLI проверяет карточку и непосредственных детей. Если включена политика `case-coverage-v1`, проверяются план, обязательные кейсы и хеши заявленных файлов. Агент сверяет смысл приёмки и одобрение. [Запись доказательств](../domains/task-lifecycle/entities/verification-evidence.md) · [Поток жизненного цикла](../domains/task-lifecycle/flow.md)

## Версионированный flow {#flow-schema}

Flow с `schema_version: flow-1` дополнительно проверяется по `schemas/flow.schema.json` и графовым инвариантам. Остальные flow читаются в прежнем формате.

| Условие | Ошибка |
|---|---|
| `initial_state`, `terminal_states`, `states` или `transitions` отсутствуют или имеют неверный тип | `flow <type>/<flow>: ...` |
| `initial_state` или `terminal_states` ссылаются на недекларированное состояние | точное имя состояния |
| `from` или `to` перехода ссылаются на недекларированное состояние | `transitions[N]: from/to must reference a declared state` |
| Состояние недостижимо из `initial_state` | `state 'x' is unreachable from 'initial'` |
| Два перехода имеют одинаковые `from` и `event` | `ambiguous transitions ...: id1, id2` |
| ID состояния или перехода повторяется | duplicate id |
| `steps` и `states` расходятся | `step 'x' is not declared in states` / `state 'x' has no declared step` |
| `initial_state` не первый шаг | `initial_state ... must be the first step` |
| Переход пропускает шаг вперёд | `transition 'id' skips steps: a -> c` |
| Нет перехода между соседними шагами | `missing transition from step 'a' to 'b'` |

Порядок `steps` — исполняемый контракт: happy path обязан совпадать с ним, обратные переходы (`verify → fix`) допустимы. `scan --scope task-conf` проверяет все flow типов. `task advance` повторно разрешает переход по `flow_state` и событию, поэтому неоднозначный или неизвестный переход отклоняется без записи. Для flow без `schema_version: flow-1` команда возвращает `UNSUPPORTED-FLOW` с подсказкой добавить версионированное определение.

## Таблица выбора flow {#flow-selection}

`types/<type>/flow-selection.yaml` с `schema_version: flow-selection-1` содержит типизированные факты и правила. `task select-flow` возвращает ID правила, flow и основание. Неизвестный факт даёт `UNKNOWN-FACT`, отсутствующий обязательный факт — `MISSING-FACT`, совпадение нескольких правил — `CONFLICT` с их ID. Fallback допускается только один и применяется после проверки остальных правил. Если тип объявляет больше одного `allowed_flows`, таблица обязательна: `scan --scope task-conf` сообщает об отсутствующем файле.

## Зависимости и готовность детей {#subtask-readiness}

`subtasks[].depends_on` содержит ID непосредственных детей. `task diagnose` и `task close` проверяют ссылки, циклы и вычисляют для каждого ребёнка `readiness`:

| Значение | Условие |
|---|---|
| `completed` | фаза ребёнка `completed` и применимые evidence прошли |
| `ready` | все объявленные зависимости `completed` |
| `blocked` | есть незавершённая зависимость (`blocked_by`), отсутствующий/битый ребёнок или цикл |

`task decompose` проверяет граф всего пакета до записи: неизвестная зависимость или цикл отклоняют пакет без создания каталогов и без изменения родителя.

## Закрытие и evidence {#closure-evidence}

`task close` атомарно фиксирует результат: объявленные дети с `phase: completed` получают `subtasks[].status: completed`, а текущая стадия — запись `stage_history` со `status: completed`. Эти поля изменяемы; immutable intent не затрагивается.

Если `verification.json` содержит `snapshot_files`, устаревший снимок блокирует закрытие (`evidence <stage>: snapshot is stale: <path>`) и для задач без `case-coverage-v1`. Задача без evidence закрывается по остальным предусловиям. `diagnose --dry-run` показывает те же блокировки.

## Версионированная запись

Legacy-запись без `record_version` валидируется по общим правилам; её `phase`
хранится в `task.json`.

Для записи с `record_version` дополнительно проверяются:

| Условие | Ошибка |
|---|---|
| `record_version` не равен поддерживаемой версии | `unsupported record_version` |
| `intent_digest` отсутствует или не совпадает с текущими intent-полями | `intent fields changed since migration; intent is immutable` |
| `flow_version` отсутствует | `flow_version is missing for a versioned record` |
| `state.json` отсутствует | `record: state.json is missing; run arch task replay` |
| `state.json.flow_state` не строка/null или не совпадает с журналом | `record: ...` |
| `flow.transitioned` нарушает цепочку `from` | `EVENT ...` |
| `state.json` не совпадает с пересчитанным журналом | `record: state.json does not match events.jsonl; run arch task replay` |
| `state.json.intent_digest` или `flow_version` расходятся с `task.json` | `record: ... does not match task.json` |
| `events.jsonl` содержит частичную строку, неизвестный тип, разрыв ревизии или цепочки `prev_digest`/`digest` | `EVENT ...` |

`task migrate`, `task event` и `task replay` возвращают структурированную ошибку
и exit 5 на конфликт ревизии или ключа идемпотентности, не изменяя запись.
Повреждённый журнал не материализуется как успешное состояние.
[Запись задачи](../domains/task-lifecycle/entities/task-record.md)

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

## Реестр номеров

`doc/config/task-registry.json` — CLI-owned данные; `task new`, `task init`, `task registry add` и `task registry sync` пишут его, остальные команды только читают.

- `schema_version` отсутствует или не равен `1` → ошибка
- `tasks` не массив → ошибка
- Элемент без `task_key`/`task_number` или с невалидным ключом → ошибка
- `task_number` не совпадает с номером в `task_key` → ошибка
- Дубль `task_key` или номера в одном семействе источника → ошибка, запись не меняется
- `task-key --next` для источника кроме `ui` → ошибка
- Конфликт при регистрации существующего ключа с другим номером → ошибка
- Ошибка записи реестра в `task new` → созданный каталог задачи удаляется
- `task registry check` при расхождении → exit 1, файл реестра не изменён
- `task registry sync` при `number_mismatch` → ошибка, реестр не изменён
- `task registry sync` для каталога с невалидным именем или без `task.json` → каталог пропускается

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
