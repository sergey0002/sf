---
title: "Аудит UI-0029, спецификация *.flow.json (v2.0) и системный аудит sf под большие базы и слабые модели"
description: "Мастер-спецификация UI-0029 (v2.0): разграничение task-conf и архитектурных флоу, схема arch-flow.schema.json, связка CLI + flow-audit + Zero-Archaeology Capsule, глубокое сравнение SDD/агентных технологий 2025–2026 и сквозной аудит пробелов системы sf для работы на больших кодовых базах и слабых моделях с минимальным расходом токенов и риском багов → 0."
status: draft
version: "2.0"
date: "2026-11-23"
git_rev: "f8cb406"
arch_version: "0.2.0"
tags: [flow, json-schema, decision-tree, state-machine, sdd, dmn, ui-0029, architecture, token-efficiency, weak-models, harness-engineering]
related:
  - UI-0029
  - UI-0028
  - UI-0030
  - UI-0031
  - UI-0032
  - ARCH-contract
  - ADR-0001
  - CAP-addressable-contracts
  - CAP-role-model-routing
  - VIEW-quality
  - VIEW-open-constraints
  - ENT-flow-definition
  - ENT-verification-evidence
  - FLOW-create-task
  - FLOW-task-lifecycle
  - FLOW-execute-task
  - FLOW-cli-task-lifecycle
  - FLOW-cli-subtask-lifecycle
  - FLOW-verify-task
  - FLOW-document-session
  - FLOW-kilo-session-audit
---

# Аудит `UI-0029`, спецификация `*.flow.json` (`v2.0`) и итоговый аудит системы `sf`

**Назначение документа:** единая рабочая спецификация для обсуждения, доработки и переоформления задачи `UI-0029` (*Стандарт описания flow: каталог, дерево решений и проверка расхождений*), дополненная глубоким сравнением технологий агентной разработки (2025–2026) и сквозным аудитом всей архитектуры `sf` относительно её четырёх глобальных целей: **(1) большие кодовые базы (`100K–1M+ LOC`), (2) надёжное исполнение даже на слабых/малых моделях, (3) минимальный расход токенов на принятую задачу, (4) риск багов, стремящийся к нулю (выше `OpenSpec`, `Spec Kit`, `Kiro` и аналогов)**.  
**Снимок проверки:** `f8cb406` (`arch 0.2.0`), `2026-11-23`.

> **Зафиксированные вводные владельца:**
> 1. **Никаких игрушечных репозиториев** (`orders / billing / shipping`) — ни в качестве пилота, ни в качестве суррогата продукта. На текущем этапе разрабатываемым продуктом репозитория `sf` является сама программная фабрика (`arch` CLI, хранилище архитектуры и задач, контур верификации и аудита сессий). Все схемы, проекции и проверки отрабатываются и принимаются на реальных процессах самой `sf`, но проектируются с запасом под целевые продуктовые монорепозитории `100K–1M+ LOC`.
> 2. **Чёткое разграничение двух видов `flow`:**
>    - **Task Flows (`doc/config/task-conf/`)** — конфигурация маршрутов и шагов выполнения задач агентом (`flow-1`: `standard-implementation`, `docs-only`, `research-first` и т.д.). В `UI-0029` **не меняются**.
>    - **Архитектурные Flows (`doc/architecture/**/FLOW-*`, `type: flow`)** — **деревья решений и жизненный цикл процессов, работающих внутри системы**. Именно для них в `UI-0029` вводится строгий JSON-канон, и все реальные архитектурные флоу `sf` должны быть переведены на этот формат.

---

## Содержание

1. [Разграничение: Task Flows (`task-conf`) vs Архитектурные Flows (`doc/architecture/`)](#1-разграничение-task-flows-task-conf-vs-архитектурные-flows-docarchitecture)
2. [Полный аудит текущей постановки задачи `UI-0029` и её подзадач `0001–0003`](#2-полный-аудит-текущей-постановки-задачи-ui-0029-и-её-подзадач-00010003)
3. [Ревизия всех 8 существующих `FLOW-*` в `doc/architecture/` и план их миграции](#3-ревизия-всех-8-существующих-flow--в-docarchitecture-и-план-их-миграции)
4. [Аудит полноты JSON-модели из `UI-0029`: что покрыто и чего не хватает](#4-аудит-полноты-json-модели-из-ui-0029-что-покрыто-и-чего-не-хватает)
5. [Ресерч по энциклопедиям `data/` и лучшим практикам SDD (2025–2026)](#5-ресерч-по-энциклопедиям-data-и-лучшим-практикам-sdd-20252026)
6. [Предлагаемый формат `*.flow.json` (версия `v2.0` схемы `arch-flow.schema.json`)](#6-предлагаемый-формат-flowjson-версия-v01-для-итеративной-доработки)
7. [Детерминированные проверки CLI, граница ответственности и контракт графового индекса](#7-детерминированные-проверки-cli-граница-ответственности-и-контракт-графового-индекса)
8. [Целевая структура переработанной задачи `UI-0029`, инвентарь файлов и запреты](#8-целевая-структура-переработанной-задачи-ui-0029-инвентарь-файлов-и-запреты)
9. [Открытые вопросы и точки решений для дальнейшей проработки](#9-открытые-вопросы-и-точки-решений-для-дальнейшей-проработки)
10. [Флоу как связующий каркас архитектуры и цикл их пополнения/использования (`OpenSpec`, `Spec Kit`, `EventCatalog`, `sf`)](#10-флоу-как-связующий-каркас-архитектуры-и-цикл-их-пополненияиспользования-openspec-spec-kit-eventcatalog-sf)
11. [Четырёхуровневый контроль полноты и непрерывная защита от устаревания (Anti-Drift Fitness Functions)](#11-четырёхуровневый-контроль-полноты-и-непрерывная-защита-от-устаревания-anti-drift-fitness-functions)
12. [Симбиоз CLI и агента при расследовании кода (`flow-audit`) и критерии декомпозиции границ флоу](#12-симбиоз-cli-и-агента-при-расследовании-кода-flow-audit-и-критерии-декомпозиции-границ-флоу)
13. [Сравнительный анализ технологий агентной разработки (2025–2026) и механика достижения глобальных целей `sf`](#13-сравнительный-анализ-технологий-агентной-разработки-20252026-и-механика-достижения-глобальных-целей-sf)
14. [Итоговый сквозной аудит `flowjson.md` и всей системы `sf`: пробелы, риски и детальный план доработок (`GAP-FLOW-01..05`, `GAP-SYS-01..07`)](#14-итоговый-сквозной-аудит-flowjsonmd-и-всей-системы-sf-пробелы-риски-и-детальный-план-доработок-gap-flow-0105-gap-sys-0107)
15. [Сводный реестр стандартов, материалов `data/` и внешних исследований SDD (2024–2026)](#15-сводный-реестр-стандартов-материалов-data-и-внешних-исследований-sdd-20242026)

---

## 1. Разграничение: Task Flows (`task-conf`) vs Архитектурные Flows (`doc/architecture/`)

*(Факт проекта + вывод аудита)* В `sf` слово `flow` исторически обозначает два принципиально разных слоя. Смешение этих слоёв стало главной причиной ошибок как в существующих Markdown-файлах `FLOW-*`, так и в постановке `UI-0029`:

| Ось сравнения | Конфигурационные Task Flows (`task-conf`) | Архитектурные системные Flows (`doc/architecture/`) |
|---|---|---|
| **Назначение** | Как агент ведёт карточку задачи по шагам конвейера от `intake` до `close` | Как устроены процессы, ветвления решений и переходы состояний в самой системе |
| **Место хранения** | `doc/config/task-conf/types/<type>/flows/<flow>/` | `doc/architecture/domains/<domain>/flows/` |
| **Текущий формат** | YAML со схемой `flow-1` + `flow-selection.yaml` + `prompt.md` + `stepsprompt/*.md` | Сейчас: разнородный ручной Markdown (`type: flow`); целевой в `UI-0029`: JSON-канон + генерируемый `.md` |
| **Документ-контракт** | [flow-definition.md](doc/architecture/domains/task-lifecycle/entities/flow-definition.md) (`ENT-flow-definition`) | [architecture-contract.md](doc/architecture/system/architecture-contract.md) §5.5E + будущий ADR `UI-0029` |
| **Что является узлом** | Рабочий этап агента (`architecture-context`, `change`, `verify`, `close`) | Узел решения (`decision` с факторами и `hit_policy`), ветка (`branch`) и состояние сущности (`state`) |
| **Команды CLI** | `arch task types`, `select-flow`, `flow-steps`, `flow-prompt`, `advance`, `scan --scope task-conf` | `arch list --type flow`, `docs search`, `docs read`, `docs context`, `docs impact`, будущий `docs flow` |
| **Связь с кодом и тестами** | Проверяется на связность состояний/промптов внутри `task-conf` | Трассирует конкретные ветки поведения на модули кода (`refs.code`), контракты (`refs.contracts`) и оракулы (`refs.tests`) |
| **Входит в `UI-0029`?** | **Нет (`scope.out`)** — механизм `flow-1` уже реализован и работает | **Да (`scope.in`)** — полная стандартизация формата, CLI-анализа и миграция всех системных флоу `sf` |

### Почему в текущей редакции `UI-0029` произошла подмена объекта

В [doc/tasks/UI-0029/task.json](doc/tasks/UI-0029/task.json) верно записано исходное намерение: *«флоу описывают продукт, а не маршрутизацию работы фабрики»*. Однако при декомпозиции автор карточки забыл, что **для репозитория `sf` разрабатываемым продуктом является сама система `sf`**, и сделал три ошибочных шага:
1. Ввёл параллельный тип `product-flow` вместо замены формата канонического типа `flow`.
2. Прямо запретил проверять и внедрять формат на самой `sf` (*«Пилот строится в отдельном временном Git-репозитории; не использовать поведение `sf` как предмет пилота»* — [doc/tasks/UI-0029/stage1/plan.md](doc/tasks/UI-0029/stage1/plan.md)), придумав искусственный магазин `orders / billing / shipping`.
3. В подзадаче `0001` (`CASE-2`) заклеймил реальный процесс `FLOW-create-task` как «непереносимую процедуру фабрики» и вывел миграцию существующих `FLOW-*` за пределы задачи.

**Следствие такого подхода:** после затрат 40 часов (`complexity: high`) в репозитории `sf` осталось бы **0 реальных JSON-флоу** и **все 8 старых невалидируемых `FLOW-*.md`**, в то время как соседняя задача [UI-0028](doc/tasks/UI-0028/task.json) образцово переводит в JSON все реальные термины глоссария `sf` и генерирует из них `glossary.md`.

---

## 2. Полный аудит текущей постановки задачи `UI-0029` и её подзадач `0001–0003`

### 2.1. Диагностика карточек и планов через `arch` CLI (фактический статус на `f8cb406`)

*(Факты проекта, воспроизводимые командами `arch`)* Карточка `UI-0029` и все три её подзадачи сейчас **не проходят проверки готовности планов и подзадач**:

| Объект | Команда | Результат | Причина отказа / замечание |
|---|---|---|---|
| `UI-0029` | `arch task validate UI-0029` | `exit 0` | Базовые поля JSON заполнены корректно. |
| `UI-0029` | `arch task diagnose UI-0029 --json` | **`acceptance_plan_ready: false`** | Блокер в `close_blockers`: `acceptance stage1: plan.md: command 'arch validate --brief' required by rule command` (дублируется дважды). |
| `UI-0029/subtasks/0001` | `arch task subtask validate UI-0029 0001` | **`exit 1`** | `[VALIDATION] acceptance stage1: plan.md: command 'arch validate --brief' required by rule command`. |
| `UI-0029/subtasks/0002` | `arch task subtask validate UI-0029 0002` | **`exit 1`** | Та же ошибка: после влития `UI-0032` правило типа требует явного присутствия `arch validate --brief` в плане при заданном `estimate_hours`. |
| `UI-0029/subtasks/0003` | `arch task subtask validate UI-0029 0003` | **`exit 1`** | Та же ошибка. |
| Подзадачи `0001–0003` | осмотр `task.json` + [UI-0030](doc/tasks/UI-0030/task.json) `AC-3` | Legacy-долг | У всех трёх карточек указано `"task_type": "subtask", "flow": null` вместо предметных типов (`docs`, `feature`, `refactor`) с разрешённым `flow`. |

### 2.2. Дефекты архитектуры, границ и трассируемости внутри `UI-0029`

1. **Отсутствие спецификации самой JSON-схемы в плане:** в `UI-0029/stage1/plan.md` (66 строк) нет ни одного примера структуры JSON, типов полей, правил обязательности или формул инвариантов (ср. `UI-0028/stage1/plan.md` на 350 строк с полными JSON-примерами и алгоритмами ранжирования).
2. **Конфликт типов документов (`product-flow` vs `flow`) и забытая `schemas/bodies/flow.json`:**
   - В `doc/config/paths.yaml` в `project.document_types` уже объявлен тип `flow`, а в `doc/architecture/schemas/bodies/flow.json` лежит мёртвая body-схема Markdown-флоу (которую `body_validation.py` из-за бага даже не исполняет).
   - Введение второго типа `product-flow` раскалывает модель типов пополам вместо перевода единого типа `flow` на JSON-канон.
3. **Не решена связь с `index.json` и человекочитаемым слоем (`ADR-0001`):**
   - Текущий `ArchitectureStore.load_documents()` (`doc/tools/arch/store.py`) читает только `*.md`. Если положить в `doc/architecture/` только сырой `.json` без генерации производного `.md`, флоу исчезнут из человекочитаемой навигации в Git/просмотрщике и потребуют переделки `index.schema.json`.
   - Паттерн `UI-0028` решает это чисто и единообразно: **`<slug>.flow.json` — единственный редактируемый источник, `<slug>.md` — детерминированно генерируемое представление в `generated_files`** (с YAML frontmatter `type: flow`, таблицами решений и диаграммами Mermaid), проверяемое через `build / check`.
4. **Пропущен обязательный ADR в составе работ и критериях приёмки:**
   - Перевод канона флоу с ручного Markdown на JSON меняет решение `ADR-0001` и `ARCH-contract` §5.5E. В `UI-0029` нет ни отдельного `AC` на выпуск `ADR-0003-...`, ни соответствующего `CASE` в `verification.json`.
5. **Неполный контекст задачи (`related_docs`, `project_context_refs`, `depends_on`):**
   - В `UI-0029` указаны только 2 флоу из 8 (`FLOW-create-task`, `FLOW-verify-task`). Остальные **6 документов `FLOW-*`**, а также `ENT-flow-definition`, `ADR-0001`, `VIEW-data`, `REG-cli-command-map`, `REG-cli-validation-rules` и `SPEC-cli-implementation` не объявлены и не попадают в `arch docs context --task UI-0029`.
   - Поле `depends_on` пусто (`[]`), хотя `assumptions` явно опирается на `UI-0031` и `UI-0032`, а открытая `UI-0030` (`AC-3`) напрямую изменяет файлы `doc/tasks/UI-0029/subtasks/*`.
6. **Пропуски в маршрутах скиллов (`0003`):**
   - В `0003/stage1/plan.md` забыты `doc/skills/architecture-docs/SKILL.md` (главный скилл обновления архитектуры!), `doc/skills/arch-cli/SKILL.md` и `doc/skills/plan-task/SKILL.md`.
   - В `AC-5` и `CASE-8` фигурирует несуществующий в `doc/AGENTS.md` голосовой триггер «задокументируй флоу» вместо согласованной работы существующих скиллов `document-session` («задокументируй») и `architecture-docs`.

---

## 3. Ревизия всех 8 существующих `FLOW-*` в `doc/architecture/` и план их миграции

*(Факты проекта + вывод аудита)* В `doc/architecture/` сейчас числятся 8 документов с `type: flow` (все в `status: draft`, причём 6 из 8 нарушают даже старую `schemas/bodies/flow.json`). Детальный разбор показывает, что под одной меткой `type: flow` в них смешаны **(а) реальные системные процессы с деревьями решений**, **(б) пересказ шагов агента из `task-conf`** и **(в) справочники аргументов CLI и SQL-запросов**:

| № | ID и текущий путь | `implemented` | Что реально находится внутри сейчас | Целевое действие при миграции в `UI-0029` |
|---|---|---|---|---|
| 1 | `FLOW-create-task`<br>`domains/task-intake/flows/create-task.md` | `false` (фактически `task new/init` реализованы) | Таблица ветвлений `P1..P4` (трекер / уточнение в чате / `task new` / `task init`), отказы при коллизиях и правила `AC → CASE` | **Перевести в `create-task.flow.json` (`FLOW-create-task`)**: формализовать факторы (`ambiguity`, `key_mode`, `collision`), атомарность записи карточки + `task-registry.json`, связать с `task_ops.py`, `validation.py` и `test_task_identity.py`. Включить сюда же операционные ветки `init` из `FLOW-cli-task-lifecycle`. Методические советы по написанию `CASE` перенести в скилл `create-task` / `plan-task`. |
| 2 | `FLOW-task-lifecycle`<br>`domains/task-lifecycle/flow.md` | `false` (ядро реализовано в `task_ops.py` и `flows.py`) | Смесь: верхняя половина пересказывает шаги агента и таблицу типов `task-conf`; нижняя половина описывает системные процессы `select-flow`, `diagnose`, `advance`, `migrate/replay`, `close` | **Разделить и перевести ядро в `task-lifecycle.flow.json` (`FLOW-task-lifecycle`)**: смоделировать узлы решений `select-flow` (правила/конфликт/недостающий факт), `advance` (`expected_revision`, идемпотентный `event_id`, возврат `verify → fix`), `diagnose` (`COLLECT` блокировок) и `close` (`--dry-run` vs боевое закрытие). Пересказ агентных шагов оставить в `task-conf` и `go-to-task`. |
| 3 | `FLOW-execute-task`<br>`domains/task-lifecycle/flows/execute-task.md` | `false` | Линейный пересказ 6 этапов работы одного агента (`Прочитать → Контекст → Планировать → Реализовать → Верифицировать → Ревью`) + условия остановки | **Убрать дублирование с `task-conf` и `FLOW-task-lifecycle`**: системные условия остановки (грязное дерево, отсутствие оракула, непройденные проверки) перенести guard-ветками в `FLOW-task-lifecycle` и `FLOW-verify-task`, а сам документ пометить `superseded_by: FLOW-task-lifecycle` (либо вывести из `type: flow`), чтобы не дублировать `standard-implementation`. |
| 4 | `FLOW-cli-task-lifecycle`<br>`domains/task-lifecycle/cli-task-lifecycle.md` | `true` | Справочник 4 команд CLI (`task init`, `validate`, `workspace`, `status`) и раскладки папок | **Не является отдельным бизнес/системным флоу:** ветки решений и кодов отказа `init / validate / workspace` перенести в `FLOW-create-task` и `FLOW-task-lifecycle`, а справочник сигнатур команд консолидировать в `REG-cli-command-map` / `SPEC-cli-implementation`. |
| 5 | `FLOW-cli-subtask-lifecycle`<br>`domains/task-lifecycle/cli-subtask-lifecycle.md` | `true` | Описание иерархии `subtasks/<NNNN>/`, рекурсии, `subtask init / validate / status` и правил выбора типа ребёнка | **Преобразовать в полноценный `subtask-lifecycle.flow.json` (`FLOW-subtask-lifecycle`)**: дерево решений декомпозиции и готовности детей (`subtask_policy: forbidden/optional/required`, пакетный `task decompose` с проверкой неизвестных ID и циклов `depends_on` до записи, расчёт `ready | blocked | completed`, синхронизация при `close`), связанный с `UI-0030` и `task_ops.py`. |
| 6 | `FLOW-verify-task`<br>`domains/execution-verification/flow.md` | `false` (механика снимков и `case-coverage-v1` реализована) | 6 шагов запуска проверок на снимке и список путей отказа (нет оракула, смещение состояния, таймаут, отказ одобрения) | **Перевести в `verify-task.flow.json` (`FLOW-verify-task`)**: формализовать дерево решений оракула (`acceptance.py`): политика `case-coverage-v1` vs базовая, проверка `plan-policy` (`acceptance_plan_ready`), свежесть SHA-256 `snapshot_files` (`ok | stale | missing`), исходы проверок и блокировка переходов. |
| 7 | `FLOW-document-session`<br>`domains/execution-verification/flows/document-session.md` | `false` | Готовое дерево решений из 3 веток (`P1`: есть задача, `P2`: нет задачи, `P3`: неясные доказательства) | **Прямой перевод в `document-session.flow.json` (`FLOW-document-session`)** с явными факторами (`active_task`, `evidence_clarity`, `canon_changed`), постусловиями неизменности исходного `task.json` и связями со скиллом `document-session` и гейтами `validate / check-links`. |
| 8 | `FLOW-kilo-session-audit`<br>`domains/execution-verification/flows/kilo-session-audit.md` | `true` | **Гибрид на 22,2 КБ:** процедура `arch session find / digest / events` + 140 строк описания схемы `kilo-session-digest-v1` и bash/SQL-скриптов к `kilo.db` | **Разделить на два чистых документа:** (1) процесс и ветвления поиска/разбора сессии (`1 кандидат / >1 кандидатов / 0 кандидатов → exit 20 vs exit 0 / ошибка SQLite → exit 1`, обрезка `timeline` с сохранением `tool_calls`) перевести в **`kilo-session-audit.flow.json`**; (2) схему JSON-ответа и SQL-рецепты вынести в `SPEC-kilo-session-audit` (`type: implementation-spec`) или `runbook`. |

### 3.2. Какие системные процессы самой `sf` сейчас вообще не покрыты `FLOW-*` (слепые зоны ядра)

Сверка всех **32 Python-модулей** в `doc/tools/arch/` и всех **5 доменов** в `doc/architecture/domains/` выявляет две крупные слепые зоны, без закрытия которых карта флоу самой `sf` была бы неполной:
1. **Домен `project-knowledge` сейчас имеет 0 документов `type: flow`**, хотя именно в нём работают два самых нагруженных процесса фабрики:
   - **индексация, валидация контрактов и скан целостности** (`store.py` — 250 строк, `validation.py` — 909 строк, `body_validation.py` — 169 строк, `sections.py` — 155 строк, `cli/commands/builtin.py` — `index build/check`, `validate`, `docs paths --check`, `docs check-links`, `scan`) → целевой **`FLOW-docs-validation-and-indexing`**;
   - **поиск, точечное чтение, сборка контекста задачи и расчёт влияния** (`doc_ops.py` — 1322 строки, второй по размеру модуль во всём репозитории!) → целевой **`FLOW-docs-retrieval-and-impact`** (и при влитии `UI-0028` сюда же подключается расширение запросов через `glossary.py`, либо выделяется **`FLOW-glossary-lifecycle`**).
2. **Движок выбора и продвижения маршрутов задач `doc/tools/arch/flows.py` (560 строк)** (`select-flow`, `flow-steps`, `advance` с `expected_revision`/`event_id`, `replay` `events.jsonl`): старый `FLOW-execute-task` пересказывал промпты агента, вместо того чтобы описать реальное детерминированное дерево решений самого движка `flows.py`. В целевой модели этот движок формализуется либо как каскад узлов внутри `FLOW-task-lifecycle`, либо как отдельный компактный **`FLOW-task-flow-execution`** (заменяющий старый `FLOW-execute-task`).

### 3.3. Полная матрица покрытия всех 32 модулей `doc/tools/arch/` и 5 доменов `sf`

Эта таблица задаёт эталон **100% наблюдаемости кодовой базы `sf`** для будущей команды `arch docs flow coverage`: каждый файл в `doc/tools/arch/` либо привязан к конкретному `*.flow.json`, либо явно классифицирован как чистая инфраструктурная прослойка без доменных ветвлений (`exempt_infrastructure`):

| Домен / класс | Целевой `*.flow.json` (статус) | Покрываемые модули `doc/tools/arch/` и команды CLI | Связанные `ENT-*` / `CAP-*` / `REG-*` |
|---|---|---|---|
| **`task-intake`** | **`FLOW-create-task`** (`implemented: true`) | `task_ops.py` (`new`, `init`), `task_registry.py` (`init`, `add`, `check`, `sync`), `identity.py`, `validation.py#parse_task_key`, `cli/commands/task_key.py` | `CAP-task-intake`, `REG-task-number-registry`, `REG-cli-validation-rules`, `ENT-task-input`, `ENT-task-record` |
| **`task-lifecycle`** | **`FLOW-task-lifecycle`** (`implemented: true`) | `task_ops.py` (`validate`, `workspace`, `status`, `diagnose`, `doctor`, `close`, `migrate`, `baseline`), `task_record.py`, `plan_policy.py`, `cli/commands/task.py` | `ENT-task-record`, `ENT-stage-artifact`, `REG-cli-validation-rules` |
| **`task-lifecycle`** | **`FLOW-task-flow-execution`** (`implemented: true`, заменяет `FLOW-execute-task`) | `flows.py` (`types`, `flows`, `select-flow`, `flow-steps`, `advance`, `event`, `replay`) | `ENT-flow-definition`, `CAP-single-agent-execution` |
| **`task-lifecycle`** | **`FLOW-subtask-lifecycle`** (`implemented: true`) | `subtask.py`, `task_ops.py` (`decompose`, `subtask init/validate/status`) | `ENT-task-record`, `UI-0030` |
| **`execution-verification`** | **`FLOW-verify-task`** (`implemented: true`) | `evidence.py`, `acceptance.py`, `task_ops.py` (`evidence`, проверка SHA-256 снимка и `case-coverage-v1`) | `ENT-verification-evidence`, `ENT-stage-artifact` |
| **`execution-verification`** | **`FLOW-document-session`** (`implemented: true`) | Оркестрация скилла `document-session` поверх `validate`, `index check`, `docs check-links` | `CAP-doc-integrity`, `ARCH-contract` |
| **`execution-verification`** | **`FLOW-kilo-session-audit`** (`implemented: true`) | `session_audit.py` (1222 строки), `cli/commands/session.py` (`find`, `digest`, `events`) | `SPEC-kilo-session-audit` (выделяемый из гибрида) |
| **`project-knowledge`** | **`FLOW-docs-validation-and-indexing`** (`implemented: true`, **новый**) | `store.py`, `body_validation.py`, `sections.py`, `validation.py` (архитектурные гейты), `cli/commands/builtin.py` (`index build/check`, `validate`, `docs paths`, `docs check-links`, `scan`), `arch_flows.py` (`validate/build/check/coverage`) | `CAP-project-knowledge`, `CAP-doc-integrity`, `CAP-addressable-contracts`, `ARCH-contract` |
| **`project-knowledge`** | **`FLOW-docs-retrieval-and-impact`** (`implemented: true`, **новый**) | `doc_ops.py` (1322 строки: `search`, `read`, `toc`, `tree`, `related`, `context`, `impact`), `arch_flows.py` (`show`, `refs`, двухкольцевой радар), интеграция с `glossary.py` (`UI-0028`) | `CAP-project-knowledge`, `CAP-addressable-contracts`, `GLO-system` |
| **`model-routing`** | **`FLOW-role-model-routing`** (`implemented: false`, `status: "draft"`) | Плановый домен (`CAP-role-model-routing` имеет `implemented: false`); runtime-модулей в `doc/tools/arch/` пока нет — отслеживается в `flow coverage` как `planned_domain` | `CAP-role-model-routing` |
| **`exempt_infrastructure`** *(не требуют своих `FLOW-*`)* | Белый список `flow_coverage.exempt_globs` в `doc/config/paths.yaml` | `__init__.py`, `__main__.py`, `constants.py`, `fs_atomic.py`, `project_config.py`, `schema.py`, `cli/__init__.py`, `cli/app.py`, `cli/errors.py`, `cli/output.py`, `cli/commands/{__init__,base,registry}.py` | Низкоуровневые утилиты ввода-вывода, констант и обёрток CLI без самостоятельного бизнес-процесса |

---

## 4. Аудит полноты JSON-модели из `UI-0029`: что покрыто и чего не хватает

### 4.1. Почему текущий набросок в `UI-0029` покрывает только ~35–40% задачи

В `UI-0029` (`AC-1`, `AC-2`, `stage1/plan.md`) предложено хранить флоу как плоский набор веток `FLOW-ID#branch-id` с полями `условия`, `участники`, `вход`, `исход`, `постусловия`, `применимость`, `происхождение` и типизированными ссылками, а на чтении строить проекции `--view decisions | transitions | refs`.

Между структурой хранения и обещанными проекциями есть **прямой структурный разрыв**:
1. **Невозможность честной таблицы решений (`--view decisions`):** если условие ветки записано свободной строкой (а не значениями типизированных входных факторов с явной политикой выбора `hit_policy`), CLI не может ни выстроить столбцы условий таблицы решений, ни математически проверить две главные болезни любого дерева решений — **пропущенные случаи (`gaps` / неполнота)** и **противоречивые пересечения веток (`overlaps` / неоднозначность)**.
2. **Невозможность честного графа жизненного цикла (`--view transitions`):** если у ветки нет явных состояний `from_state → to_state` (и узлов каскадных переходов), CLI не может построить ни автомат состояний сущности, ни петли возврата/повтора, не прибегая к запрещённому угадыванию по тексту.

### 4.2. Детальная матрица оценки по 12 критериям

| № | Критерий описания деревьев решений и жизненного цикла | Есть в текущей `UI-0029`? | В чём дефицит и к каким сбоям он ведёт |
|---|---|---|---|
| 1 | **Адресация и версионирование** (`schema_version`, `id`, `branch.id`, `applicability`) | **Да** | Описано на уровне требований, но без JSON Schema и правил совместимости с `index.json`. |
| 2 | **Типизированные входные факторы ветвления (`factors`)** | **Нет** | Без перечня осей решения (`enum`, `boolean`, диапазоны) условия разных веток пишут разными словами одно и то же; невозможна автопроверка полноты покрытия комбинаций. |
| 3 | **Политика срабатывания правил (`hit_policy`)** | **Нет** | В реальных процессах `sf` есть **разные** режимы: `task init` выбирает ровно одну ветку (`UNIQUE`), `select-flow` использует правила + `fallback` (`PRIORITY`/`FIRST`), а `task diagnose` собирает **все** сработавшие блокеры сразу (`COLLECT`). Без `hit_policy` эти режимы неотличимы. |
| 4 | **Многошаговая каскадность (`decisions[]` / узлы дерева)** | **Нет** | Реальный процесс редко решается в один плоский шаг: сначала шлюз валидации входа, затем шлюз состояния/блокировок, затем запись. В плоском списке приходится копировать все ранние условия в каждую последующую ветку (комбинаторный взрыв). |
| 5 | **Природа решателя (`decision_maker`)** | **Частично** | Перечислены `участники`, но не разделено главное для агентной фабрики: вычисляется ли развилка **детерминированным кодом** (`deterministic`), **суждением агента** (`agent_judgment`) или **решением владельца** (`human_approval`). |
| 6 | **Жизненный цикл и состояния сущностей (`lifecycle`)** | **Нет** | Не объявлены целевые сущности (`ENT-*`), множество состояний (`initial`, `intermediate`, `terminal`) и переходы `from → to`. Нельзя проверить ни достижимость состояний, ни отсутствие «мёртвых тупиков». |
| 7 | **Мутации, атомарность и откат (`effects`, `atomicity`, `rollback`)** | **Нет** | Критично для процессов записи (`task new`, `decompose`, `close`, `glossary build`): какие ресурсы меняет ветка (`read_only` vs `atomic` vs `compensated`) и гарантируется ли побайтная неизменность файлов при отказе (`state_unchanged_on_disk: true`). |
| 8 | **Идемпотентность и защита от гонок (`idempotency`, `concurrency_guard`)** | **Слабо** | Упомянут «повтор, когда применим», но нет структуры ключа идемпотентности (`event_id`), поведения при повторе с тем же/другим payload и проверки ревизии (`expected_revision` / SHA-256 снимка). |
| 9 | **Таймауты и политика повторов (`retry_policy`, `timeout`)** | **Слабо** | Нет структурированных полей условия повтора (`retry_when`), лимита попыток/времени (`max_attempts`, `timeout`) и ветки эскалации при исчерпании. |
| 10 | **Сквозные инварианты и явные исключения (`invariants`, `not_included`)** | **Нет в JSON** | Обязательные по `ARCH-contract` и энциклопедиям `data/` глобальные инварианты процесса и секция `Not Included` выпали из `AC-1`. |
| 11 | **Полнота графа типизированных ссылок (`refs`)** | **Частично** | Учтены `rules`, `contracts`, `code`, `tests`, `tasks`, но пропущены ссылки на **сущности (`ENT-*`)**, **соседние/вызываемые флоу (`FLOW-*`)**, **скиллы (`doc/skills/*`)** и **термины глоссария (`TERM-*` из `UI-0028`)**. |
| 12 | **Наблюдаемый машинный выход и статус оракула (`exit_code`, `error_code`, `oracle_status`)** | **Частично** | В ветке нет явных полей `exit_code` / `error_code` и формального перечисления `oracle_status` (`verified | missing_oracle | manual_only`), по которому CLI отличает проверенную ветку от пробела тестирования. |

---

## 5. Ресерч по энциклопедиям `data/` и лучшим практикам SDD (2025–2026)

### 5.1. Синтез практик из локальных энциклопедий `data/` и документов проекта

*(Рекомендации справочного слоя `data/`)*:

1. **Каркас флоу АШОСС** ([data/machinedocs-encyclopedia/Документация/Флоу.md](data/machinedocs-encyclopedia/Документация/Флоу.md)):
   - Машиночитаемый документ потока обязан фиксировать пять элементов: **Акторы**, **Шаги** (в порядке зависимостей), **Ошибки** (error paths обязательны наравне с happy path), **Состояния** (state machine) и **Границы** (`Not Included`). Типичные антипаттерны: описание только happy path, отсутствие `Not Included` и вымышленные имена шагов вместо реальных команд/модулей/событий.
2. **Триада представлений потока** ([data/sdd-encyclopedia/Флоу/Стандарты описания флоу.md](data/sdd-encyclopedia/Флоу/Стандарты описания флоу.md)):
   - Разные вопросы требуют разных проекций одного процесса: **Activity / Flowchart** (шаги и шлюзы `XOR / AND / OR`), **DMN 1.4+** (таблицы решений для сложных ветвлений) и **UML State Machine / Statecharts** (состояния, события и `guards`). При этом хранить картинки запрещено — диаграммы генерируются в виде текста Mermaid/PlantUML, чтобы обновляться детерминированно вместе с моделью.
3. **Связь флоу с сущностями и инвариантами** ([data/machinedocs-encyclopedia/Документация/Сущности.md](data/machinedocs-encyclopedia/Документация/Сущности.md)):
   - Любой stateful-флоу опирается на доменные сущности (`Identity`, `Attributes`, `Invariants`, `Lifecycle`) и словарь терминов с `technical_mapping`. Политика `NO ASSUMPTIONS`: пробелы и открытые вопросы фиксируются явно, а не додумываются.
4. **Связка EARS + BDD Specification by Example** ([data/sdd-research/02-стандарты-и-форматы-требований.md](data/sdd-research/02-стандарты-и-форматы-требований.md), [data/sdd-research/09-bdd-исполняемые-спеки.md](data/sdd-research/09-bdd-исполняемые-спеки.md)):
   - EARS задаёт однозначную структуру правила ветки (`WHILE <состояние> + WHEN <триггер> + IF <ошибка/условие> → SHALL <наблюдаемый исход>`), а BDD связывает каждое правило с конкретными проверяемыми примерами (`CASE`), предупреждая об главной ловушке ИИ-разработки: *«агент, пишущий одновременно и спецификацию/тест, и код без независимого оракула, кодирует одно и то же заблуждение в обоих местах»*.
5. **Собственная формула таблицы переходов и отказоустойчивости проекта** ([data/machinedocs-encyclopedia/Практики/Исследование software factory — пробелы и готовые практики.md](data/machinedocs-encyclopedia/Практики/Исследование%20software%20factory%20—%20пробелы%20и%20готовые%20практики.md) §5, [nextplan.md](nextplan.md) §21.4):
   - В собственном исследовании репозитория уже сформулирован эталон строки жизненного цикла:
     `from | event | guard | actor | action | artifact/evidence | to | retry/stop/owner`, дополненный требованиями фиксировать ключ идемпотентности, защиту ревизии, реакцию на устаревший снимок (`stale input`) и путь восстановления после частичного сбоя.

### 5.2. Внешние индустриальные стандарты и практики SDD 2025–2026 гг.

*(Внешние первичные источники)*:

| Стандарт / практика (2025–2026) | Ключевые механизмы модели данных | Что берём в JSON-формат `sf` | Чего сознательно НЕ тащим (анти-оверинжиниринг) |
|---|---|---|---|
| **OMG DMN 1.6 & агентный SDD** ([OMG DMN 1.6](https://www.omg.org/spec/DMN/1.6/PDF), [Camunda DMN Reference](https://github.com/camunda/skills/blob/main/skills/camunda-dmn/references/decision-tables.md), [Trisotech Hit Policies](https://www.trisotech.com/dmn-hit-policy-explained/), [UiPath SDD `PILOT-8674`](https://github.com/UiPath/skills/pull/3944)) | Типизированные `inputs` с `allowedValues`; явный `hitPolicy` (`UNIQUE`, `ANY`, `PRIORITY`, `FIRST`, `COLLECT`); статическая проверка полноты (`0 gaps`) и непротиворечивости (`0 overlaps`, нет замаскированных правил); разделение детерминированных таблиц и `Rules That Need Reasoning` (`agent` / `human`). | Поля `factors[]` (`allowed_values`), `hit_policy`, `decision_maker` (`deterministic \| agent_judgment \| human_approval`) и детерминированный статический анализатор полноты и пересечений в `arch validate`. | Полный язык выражений FEEL и XML-схему DMN: для архитектурных флоу достаточно конечных доменов значений (`enum`/`boolean`/именованных предикатов). |
| **W3C SCXML & XState v5/v6 JSON Statecharts** ([XState v6 JSON & State Contracts](https://stately.ai/docs/xstate/v6/xstate-v5-to-v6), [Safety-Net State Machine Contracts Spike #475](https://github.com/codeforamerica/safety-net-blueprint/issues/475), [xstate-python](https://github.com/JovaniPink/xstate-python)) | Чистая JSON-сериализация состояний (`initial`, `intermediate`, `choice`, `terminal`), типизированные схемы входов/событий, именованные декларативные `guards` (без JS-кода в JSON!), `timeout` / `onTimeout` на состояниях. | Блок `lifecycle` (`states`, `initial_states`, переходы `from → to`, `state_unchanged_on_disk`), узлы решений `decisions[]` (аналог `choice`-состояний) и декларативные `when`-условия. | Исполняемый акторный рантайм, вложенные параллельные ортогональные регионы Харела и встроенный скриптовый код внутри JSON. |
| **OpenAPI Arazzo v1.0.1 / v1.1.0 (май 2026)** ([Arazzo v1.1.0](https://spec.openapis.org/arazzo/latest.html), [Arazzo Guide](https://www.analystengineering.com/articles/arazzo-api-workflows-for-analysts)) | Многошаговые сценарии с явными `inputs`, проверяемыми критериями успеха `successCriteria`, структурированными `onSuccess` / `onFailure` (`goto`, `retry` с `retryAfter`/`retryLimit`/`criteria`, `end`) и композицией через ссылку на другой `workflowId`. | Явные `postconditions` (аналог `successCriteria`), структурированный `retry_policy` и композиция процессов через `next: {decision \| flow}` без копипасты соседних флоу. | HTTP-специфичную привязку параметров заголовков/тел запросов (`$response.header...`), так как флоу `sf` описывают и CLI, и файловые, и доменные процессы. |
| **CNCF Serverless Workflow / Open Workflow v1.0–1.1** ([Open Workflow DSL Reference](https://github.com/serverlessworkflow/specification/blob/main/dsl-reference.md), [CNCF SDK](https://pkg.go.dev/github.com/cncf/wg-serverless-workflow/sdk/go/pkg/apis/serverlessworkflow)) | Узлы ветвления `switch` (`when` + `default`) и блоки отказоустойчивости `try / catch` (фильтрация ошибок, `retry`, компенсирующие действия `do`). | Явное описание `effects` (`mutates`, `atomicity: read_only \| atomic \| compensated`, `rollback`) и типизация кодов ошибок (`error_code`, `exit_code`). | Собственный оркестратор исполнения задач и jq/JSONPath-трансформации payload на каждом шаге. |
| **Spec-Anchored SDD 2026** ([SDD 2026 Maturity Model](https://dev.to/krlz/spec-driven-development-in-2026-what-it-is-the-tooling-and-how-teams-actually-use-it-2fk2), [Augment SDD Guide](https://www.augmentcode.com/guides/what-is-spec-driven-development), [Spec-Kit Governance #2614](https://github.com/github/spec-kit/discussions/2614)) | Три уровня: `Spec-First` (одноразовая спека, устаревает), `Spec-Anchored` (живая спека + тесты ловят дрейф), `Spec-as-Source` (код целиком генерируется). При обновлении обязательна сохранность стабильных ID («sticky IDs»). | Уровень **`Spec-Anchored`**: стабильные адреса `FLOW-ID#branch-id`, двусторонняя сверка с кодом/тестами, `oracle_status` и запрет молча перевыпускать ID веток. | Попытку генерировать Python-код из JSON-флоу (`Spec-as-Source`) — код остаётся в `doc/tools/arch/`, а JSON служит проверяемой картой и оракулом связности. |

---

## 6. Предлагаемый формат `*.flow.json` (версия `v0.1` для итеративной доработки)

### 6.1. Модель хранения и производных файлов (единый паттерн с `UI-0028`)

Чтобы сохранить полную совместимость с `ADR-0001`, `index.json`, просмотрщиком Markdown и Git-ревью, предлагается **та же архитектура «JSON-канон + детерминированные generated-представления», что принята в `UI-0028` для глоссария**:

| Артефакт | Путь | Роль | Редактируется вручную? |
|---|---|---|---|
| **Канонический JSON флоу** | `doc/architecture/domains/<domain>/flows/<slug>.flow.json` | Единственный источник истины структуры процесса, его состояний, факторов, веток решений и типизированных ссылок | **Да** (агентом через файл или точечные команды CLI, со строгой проверкой схемой и инвариантами) |
| **JSON Schema архитектурного флоу** | `doc/architecture/schemas/arch-flow.schema.json` | Схема Draft 2020-12 для всех `*.flow.json` (заменяет мёртвую `schemas/bodies/flow.json` и **не перезаписывает** существующую `schemas/flow.schema.json`, которая уже занята под `task-conf` `flow-1`!) | **Да** (при изменении версии контракта) |
| **Производный Markdown-документ** | `doc/architecture/domains/<domain>/flows/<slug>.md` | **Generated view**: содержит стандартный YAML frontmatter (`id`, `type: flow`, `domain`, `status`, `implemented`, `related`, `terms`) для `index.json`, таблицы решений, сгенерированные диаграммы Mermaid (`flowchart` + `stateDiagram-v2`), инварианты, `Not Included` и ссылки | **Нет** (`generated_files` в `paths.yaml`; ручная правка блокируется `arch docs flow check` и `--gate`) |
| **Индекс ветвлений и обратный граф** | `doc/architecture/flows.index.json` | **Generated graph index**: плоский каталог всех `FLOW-ID#branch-id`, состояний, факторов и полный обратный граф `referenced_by` (`by_entity`, `by_contract`, `by_term`, `by_code`, `by_test`, `by_mutated_path`, `by_flow`, `by_task`) | **Нет** (пересобирается `arch docs flow build`, идемпотентен побайтно) |

**Почему это решение снимает сразу все архитектурные трения и конфликты схем в `sf`:**
1. Не нужно плодить дублирующий тип `product-flow` — тип остаётся единым каноническим `type: flow`.
2. **Сохранность существующих схем репозитория:**
   - В `doc/architecture/schemas/flow.schema.json` уже живёт схема конфигурационных маршрутов задач (`schema_version: "flow-1"`, `Title: "Versioned task flow definition"`). Выделение `doc/architecture/schemas/arch-flow.schema.json` исключает конфликт имён.
   - `doc/architecture/schemas/index.schema.json` имеет `additionalProperties: false`, тогда как `document.schema.json` — `additionalProperties: true` (тот же факт, что зафиксирован в `UI-0028` §4.4). Поэтому `<slug>.md` бесшовно индексируется в общий `index.json` без правки `index.schema.json`, а весь граф ветвлений и обратных связей живёт в отдельном `doc/architecture/flows.index.json`.
3. Существующие команды `arch list --type flow`, `arch show`, `arch docs toc`, `arch docs read` продолжают работать с `<slug>.md` без поломки обратной совместимости, а графовые команды читают `*.flow.json` и `flows.index.json`.
4. Любой человек в Git или встроенном просмотрщике видит наглядные таблицы решений и диаграммы Mermaid, которые **гарантированно не расходятся** с JSON-моделью (поскольку проверяются в `--gate`).

### 6.2. Структура документа `*.flow.json` по слоям

Один файл `<slug>.flow.json` состоит из пяти компактных логических блоков:

1. **Шапка документа (совместимая с `document.schema.json` и `index.json`):**
   - `schema_version`: `1` (целое число версии формата);
   - `id`: `FLOW-<slug>` (например, `FLOW-create-task`);
   - `type`: константа `"flow"`;
   - `domain`: домен из `paths.yaml` (`task-intake`, `task-lifecycle`, `execution-verification`, `project-knowledge`, `model-routing`, `system`);
   - `title`: человекочитаемый заголовок;
   - `summary`: короткое условие загрузки (*«Загружать при изменении…»*);
   - `status`: `"draft" | "current" | "accepted" | "deprecated" | "superseded"`;
   - `superseded_by`: `FLOW-*` или `null` (обязателен при `status == "superseded"`);
   - `implemented`: `boolean`;
   - `applicability`: объект границ применимости (`cli_version`, `platform`, `feature_flags`, `notes`);
   - `provenance`: откуда подтверждена модель (ревизия/задача/аудит).

2. **Контекст, участники и границы (блок АШОСС):**
   - `actors[]`: `{id, kind: "human" | "agent" | "system" | "external", title, role}`;
   - `preconditions[]`: предусловия запуска процесса;
   - `invariants[]`: утверждения, которые обязаны сохраняться **на всех ветках** (включая ветки отказа!);
   - `not_included[]`: явные границы того, чего этот процесс **не делает** (`Non-goals`).

3. **Жизненный цикл процесса и сущностей (`lifecycle`):**
   - `mode`: `"stateful" | "stateless"`;
   - `target_entities[]`: массив `ENT-*` (для `stateful` — минимум 1 сущность; для read-only `stateless` может быть `[]`);
   - `initial_states[]`: начальные состояния (для `stateful`);
   - `states[]`: `{id, kind: "initial" | "intermediate" | "terminal", title, invariants?: []}`;
   - `idempotency`: `{strategy: "none" | "keyed" | "content_hash" | "state_guard", key?: string, on_duplicate: string}`;
   - `concurrency_guard`: описание механизма защиты от параллельной/устаревшей записи (`expected_revision`, проверка SHA-256 снимка, проверка коллизии до записи или `"none"`).

4. **Факторы ветвления (`factors[]`):**
   - Типизированный словарь входных переменных, от которых зависят решения в этом флоу:
     `{id, title, type: "enum" | "boolean", allowed_values: [...], source?: string}`.
   - Если в процессе есть числовые пороги или сложные условия (например, `bytes <= max_bytes` vs `bytes > max_bytes`), они сводятся к конечному разбиению (`enum`: `["within_budget", "exceeds_budget"]`) с точным предикатом в `description` — это сохраняет **100% разрешимость конечной проверки полноты и пересечений** без внедрения сложного парсера формул!

5. **Узлы решений и ветки (`decisions[]` → `branches[]`):**
   - Процесс может состоять из одного или нескольких последовательных/каскадных узлов `decisions[]`:
     - `id`: идентификатор узла решения (например, `intake-gate`, `diagnose-collect`, `close-gate`);
     - `title`: название развилки;
     - `entry_states[]`: в каких состояниях `lifecycle.states` управление входит в этот узел;
     - `evaluated_factors[]`: подмножество `factors[].id`, которые проверяются именно на этом узле (чтобы не тянуть лишние оси из других шагов!);
     - `hit_policy`: `"UNIQUE" | "ANY" | "PRIORITY" | "FIRST" | "COLLECT"`:
       - `UNIQUE` (рекомендуемый дефолт) — ровно одна ветка на любую комбинацию `evaluated_factors`, любые пересечения и дыры — ошибка валидации;
       - `FIRST` / `PRIORITY` — упорядоченные guard-правила с явным замыкающим случаем;
       - `COLLECT` — срабатывают **все** подходящие правила, а их результаты агрегируются в список (точный паттерн `arch task diagnose` и `arch scan`!);
     - `output_priority[]`: упорядоченный список исходов (обязателен только для `hit_policy == "PRIORITY"`);
     - `branches[]` (каждая ветка глобально адресуется как `FLOW-ID#<branch.id>`):
       - `id`: уникальный внутри флоу стабильный `kebab-case` идентификатор;
       - `title`: краткое имя ветки;
       - `decision_maker`: `"deterministic" | "agent_judgment" | "human_approval"`;
       - `when`: словарь `{ "<factor_id>": "<value>" | ["<v1>", "<v2>"] | "*" }` для каждого фактора из `evaluated_factors`;
       - `steps[]`: краткие атомарные действия внутри ветки (если больше одного шага);
       - `transition`: `{from: string | string[], to: string, state_unchanged_on_disk?: boolean}` (для `stateful`);
       - `effects`: `{mutates: string[], atomicity: "read_only" | "atomic" | "compensated" | "best_effort", rollback?: string}`;
       - `retry_policy` *(опционально)*: `{retry_when: string, max_attempts?: int, timeout?: string, on_exhausted: string}`;
       - `outcome`: `{kind: "ok" | "blocked" | "error" | "retry" | "finding", exit_code?: int | null, error_code?: string | null, summary: string, postconditions: string[]}`;
       - `next` *(опционально)*: `{kind: "end" | "decision" | "flow", target?: string}` — куда идёт процесс дальше (завершается, переходит во второй узел `decision` этого же флоу или передаёт управление в соседний `FLOW-*`);
       - `oracle_status`: `"verified" | "missing_oracle" | "manual_only"`;
       - `refs`: типизированные ссылки `{rules?: [], contracts?: [], entities?: [], flows?: [], skills?: [], terms?: [], code?: [], tests?: [], tasks?: []}`.

### 6.3. Черновик JSON Schema (`doc/architecture/schemas/arch-flow.schema.json`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sf.local/schemas/arch-flow.schema.json",
  "title": "Architectural System Flow (Decision Tree + Process Lifecycle)",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "id",
    "type",
    "domain",
    "title",
    "summary",
    "status",
    "implemented",
    "actors",
    "invariants",
    "not_included",
    "lifecycle",
    "factors",
    "decisions"
  ],
  "properties": {
    "schema_version": { "const": 1 },
    "id": { "type": "string", "pattern": "^FLOW-[a-z0-9][a-z0-9-]*$", "minLength": 7, "maxLength": 96 },
    "type": { "const": "flow" },
    "domain": { "type": "string", "pattern": "^[a-z][a-z0-9-]*$" },
    "title": { "type": "string", "minLength": 3 },
    "summary": { "type": "string", "minLength": 10 },
    "status": { "enum": ["draft", "current", "accepted", "deprecated", "superseded"] },
    "superseded_by": { "type": ["string", "null"], "pattern": "^FLOW-[a-z0-9][a-z0-9-]*$" },
    "owner": { "type": ["string", "null"] },
    "implemented": { "type": "boolean" },
    "applicability": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "cli_version": { "type": "string" },
        "task_schema": { "type": "string" },
        "scope_note": { "type": "string" }
      }
    },
    "provenance": { "type": "string", "minLength": 1 },
    "actors": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "kind", "role"],
        "properties": {
          "id": { "type": "string", "pattern": "^[a-z][a-z0-9_-]*$" },
          "kind": { "enum": ["human", "agent", "system", "external"] },
          "title": { "type": "string" },
          "role": { "type": "string", "minLength": 3 }
        }
      }
    },
    "preconditions": { "type": "array", "items": { "type": "string", "minLength": 1 } },
    "invariants": { "type": "array", "minItems": 1, "items": { "type": "string", "minLength": 3 } },
    "not_included": { "type": "array", "minItems": 1, "items": { "type": "string", "minLength": 3 } },
    "lifecycle": {
      "type": "object",
      "additionalProperties": false,
      "required": ["mode", "target_entities", "states", "idempotency", "concurrency_guard"],
      "properties": {
        "mode": { "enum": ["stateful", "stateless"] },
        "target_entities": {
          "type": "array",
          "items": { "type": "string", "pattern": "^ENT-[a-z0-9][a-z0-9-]*$" }
        },
        "initial_states": {
          "type": "array",
          "items": { "type": "string", "pattern": "^[a-z][a-z0-9_-]*$" }
        },
        "states": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["id", "kind", "description"],
            "properties": {
              "id": { "type": "string", "pattern": "^[a-z][a-z0-9_-]*$" },
              "kind": { "enum": ["initial", "intermediate", "terminal"] },
              "description": { "type": "string", "minLength": 3 }
            }
          }
        },
        "idempotency": {
          "type": "object",
          "additionalProperties": false,
          "required": ["strategy", "on_duplicate"],
          "properties": {
            "strategy": { "enum": ["none", "keyed", "content_hash", "state_guard", "read_only"] },
            "key": { "type": ["string", "null"] },
            "on_duplicate": { "type": "string", "minLength": 3 }
          }
        },
        "concurrency_guard": { "type": "string", "minLength": 3 }
      }
    },
    "factors": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "title", "type", "allowed_values"],
        "properties": {
          "id": { "type": "string", "pattern": "^[a-z][a-z0-9_]*$" },
          "title": { "type": "string", "minLength": 2 },
          "type": { "enum": ["enum", "boolean"] },
          "allowed_values": {
            "type": "array",
            "minItems": 2,
            "uniqueItems": true,
            "items": { "type": ["string", "boolean"] }
          },
          "description": { "type": "string" }
        }
      }
    },
    "decisions": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "title", "evaluated_factors", "hit_policy", "branches"],
        "properties": {
          "id": { "type": "string", "pattern": "^[a-z][a-z0-9-]*$" },
          "title": { "type": "string", "minLength": 3 },
          "entry_states": { "type": "array", "items": { "type": "string" } },
          "evaluated_factors": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": true,
            "items": { "type": "string" }
          },
          "hit_policy": { "enum": ["UNIQUE", "ANY", "PRIORITY", "FIRST", "COLLECT"] },
          "output_priority": { "type": "array", "items": { "type": "string" } },
          "branches": {
            "type": "array",
            "minItems": 1,
            "items": { "$ref": "#/$defs/branch" }
          }
        }
      }
    },
    "superseded_branches": {
      "type": "array",
      "description": "Переадресация перенесённых/расщеплённых веток при Flow Split без поломки исторических ссылок из задач и ADR",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "superseded_by", "reason"],
        "properties": {
          "id": { "type": "string", "pattern": "^[a-z][a-z0-9-]*$" },
          "superseded_by": { "type": "string", "pattern": "^FLOW-[a-z0-9][a-z0-9-]*#[a-z][a-z0-9-]*$" },
          "reason": { "type": "string", "minLength": 3 }
        }
      }
    }
  },
  "allOf": [
    {
      "if": { "properties": { "status": { "const": "superseded" } } },
      "then": { "required": ["superseded_by"], "properties": { "superseded_by": { "type": "string" } } }
    }
  ],
  "$defs": {
    "branch": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "title", "decision_maker", "when", "effects", "outcome", "oracle_status", "refs"],
      "properties": {
        "id": { "type": "string", "pattern": "^[a-z][a-z0-9-]*$" },
        "title": { "type": "string", "minLength": 3 },
        "decision_maker": { "enum": ["deterministic", "agent_judgment", "human_approval"] },
        "when": {
          "type": "object",
          "minProperties": 1,
          "additionalProperties": {
            "oneOf": [
              { "type": ["string", "boolean"] },
              { "type": "array", "minItems": 1, "uniqueItems": true, "items": { "type": ["string", "boolean"] } }
            ]
          }
        },
        "steps": { "type": "array", "items": { "type": "string", "minLength": 3 } },
        "transition": {
          "type": "object",
          "additionalProperties": false,
          "required": ["from", "to"],
          "properties": {
            "from": {
              "oneOf": [
                { "type": "string" },
                { "type": "array", "minItems": 1, "items": { "type": "string" } }
              ]
            },
            "to": { "type": "string" },
            "state_unchanged_on_disk": { "type": "boolean" }
          }
        },
        "effects": {
          "type": "object",
          "additionalProperties": false,
          "required": ["mutates", "atomicity"],
          "properties": {
            "mutates": { "type": "array", "items": { "type": "string", "minLength": 1 } },
            "mutates_db": { "type": "array", "items": { "type": "string", "minLength": 1 } },
            "emits_events": { "type": "array", "items": { "type": "string", "minLength": 1 } },
            "external_calls": { "type": "array", "items": { "type": "string", "minLength": 1 } },
            "idempotency_key": { "type": "string", "minLength": 1 },
            "atomicity": { "enum": ["read_only", "atomic", "compensated", "best_effort"] },
            "rollback": { "type": "string" }
          }
        },
        "retry_policy": {
          "type": "object",
          "additionalProperties": false,
          "required": ["retry_when", "on_exhausted"],
          "properties": {
            "retry_when": { "type": "string" },
            "max_attempts": { "type": "integer", "minimum": 1 },
            "timeout": { "type": "string" },
            "on_exhausted": { "type": "string" }
          }
        },
        "outcome": {
          "type": "object",
          "additionalProperties": false,
          "required": ["kind", "summary", "postconditions"],
          "properties": {
            "kind": { "enum": ["ok", "blocked", "error", "retry", "finding"] },
            "exit_code": { "type": ["integer", "null"] },
            "http_status": { "type": ["integer", "null"], "minimum": 100, "maximum": 599 },
            "error_code": { "type": ["string", "null"] },
            "summary": { "type": "string", "minLength": 3 },
            "postconditions": { "type": "array", "minItems": 1, "items": { "type": "string", "minLength": 3 } }
          }
        },
        "next": {
          "type": "object",
          "additionalProperties": false,
          "required": ["kind"],
          "properties": {
            "kind": { "enum": ["end", "decision", "flow"] },
            "target": { "type": "string" }
          }
        },
        "oracle_status": { "enum": ["verified", "missing_oracle", "manual_only"] },
        "refs": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "rules": { "type": "array", "items": { "type": "string" } },
            "contracts": { "type": "array", "items": { "type": "string" } },
            "entities": { "type": "array", "items": { "type": "string" } },
            "flows": { "type": "array", "items": { "type": "string" } },
            "skills": { "type": "array", "items": { "type": "string" } },
            "terms": { "type": "array", "items": { "type": "string" } },
            "code": { "type": "array", "items": { "type": "string" } },
            "tests": { "type": "array", "items": { "type": "string" } },
            "tasks": { "type": "array", "items": { "type": "string" } }
          }
        }
      }
    }
  }
}
```

### 6.4. Эталонный пример 1: `FLOW-create-task` (`hit_policy: "UNIQUE"`, 12 из 12 комбинаций покрыты)

Пример показывает, как реальный процесс создания задачи в `sf` описывается с полным покрытием пространства входов ($2 \times 3 \times 2 = 12$ комбинаций, `0 gaps`, `0 overlaps`) и явной границей между суждением агента и детерминированным CLI:

```json
{
  "schema_version": 1,
  "id": "FLOW-create-task",
  "type": "flow",
  "domain": "task-intake",
  "title": "Приём, выделение ключа и создание задачи",
  "summary": "Загружать при изменении приёма задач, выделения номеров в реестре, arch task new/init и проверки постановки.",
  "status": "current",
  "implemented": true,
  "applicability": {
    "cli_version": ">=0.2.0",
    "task_schema": "draft-0.2"
  },
  "provenance": "Код doc/tools/arch/task_ops.py и doc/tests/test_task_identity.py на снимке f8cb406",
  "actors": [
    {"id": "owner", "kind": "human", "role": "Формулирует запрос и разрешает блокирующие вопросы scope/оракула"},
    {"id": "intake_agent", "kind": "agent", "role": "Выявляет неоднозначности и заполняет семантические поля по скиллу create-task"},
    {"id": "arch_cli", "kind": "system", "role": "Детерминированно разбирает ключ, ведёт task-registry.json и создаёт каркас задачи"}
  ],
  "preconditions": [
    "Доступна конфигурация doc/config/paths.yaml и реестр doc/config/task-registry.json"
  ],
  "invariants": [
    "CLI не выводит семантические поля из текста запроса и не угадывает тип задачи",
    "При любой ошибке валидации, коллизии или записи не остаётся частичного каталога doc/tasks/<task_key>/",
    "Файл task.md никогда не создаётся; единственный канонический вход — task.json",
    "Создание локальной карточки не выполняет обратной записи во внешние трекеры"
  ],
  "not_included": [
    "Сетевые запросы или обратная синхронизация в Jira и внешние системы",
    "Автоматический git checkout рабочей ветки или запуск реализации"
  ],
  "lifecycle": {
    "mode": "stateful",
    "target_entities": ["ENT-task-input", "ENT-task-record"],
    "initial_states": ["unregistered"],
    "states": [
      {"id": "unregistered", "kind": "initial", "description": "Запрос поступил, записи в реестре и каталога задачи нет"},
      {"id": "awaiting_clarification", "kind": "intermediate", "description": "Ожидание ответа владельца по блокирующей неоднозначности"},
      {"id": "scaffolded", "kind": "terminal", "description": "Созданы task.json, stage1/ и запись в task-registry.json"},
      {"id": "rejected", "kind": "terminal", "description": "Операция отклонена без модификации диска и реестра"}
    ],
    "idempotency": {
      "strategy": "keyed",
      "key": "task_key",
      "on_duplicate": "Повторный task init с существующим каталогом или ключом в реестре завершается exit 1 без перезаписи"
    },
    "concurrency_guard": "Предварительная проверка отсутствия каталога doc/tasks/<task_key> и ключа в task-registry.json до записи"
  },
  "factors": [
    {
      "id": "ambiguity",
      "title": "Неоднозначность постановки",
      "type": "enum",
      "allowed_values": ["none", "blocking"],
      "description": "Меняет ли неясность целевой результат, границы полномочий или проверочный оракул"
    },
    {
      "id": "key_mode",
      "title": "Способ задания ключа",
      "type": "enum",
      "allowed_values": ["auto_ui", "explicit_valid", "explicit_invalid"],
      "description": "auto_ui — task new; explicit_valid/invalid — результат parse_task_key для task init"
    },
    {
      "id": "collision",
      "title": "Коллизия в реестре или на диске",
      "type": "enum",
      "allowed_values": ["none", "exists"],
      "description": "Существует ли уже каталог задачи либо конфликтующая запись в task-registry.json"
    }
  ],
  "decisions": [
    {
      "id": "intake-and-init",
      "title": "Разрешение постановки и создание карточки задачи",
      "entry_states": ["unregistered", "awaiting_clarification"],
      "evaluated_factors": ["ambiguity", "key_mode", "collision"],
      "hit_policy": "UNIQUE",
      "branches": [
        {
          "id": "clarify-blocking-question",
          "title": "Остановка на уточнение блокирующей неоднозначности",
          "decision_maker": "agent_judgment",
          "when": {"ambiguity": "blocking", "key_mode": "*", "collision": "*"},
          "transition": {"from": ["unregistered", "awaiting_clarification"], "to": "awaiting_clarification", "state_unchanged_on_disk": true},
          "effects": {"mutates": [], "atomicity": "read_only"},
          "outcome": {
            "kind": "blocked",
            "exit_code": null,
            "error_code": null,
            "summary": "Агент фиксирует открытые вопросы к владельцу и не вызывает task new/init",
            "postconditions": ["Каталог doc/tasks/ и task-registry.json побайтно не изменены"]
          },
          "next": {"kind": "end"},
          "oracle_status": "manual_only",
          "refs": {
            "rules": ["MAN-software-factory"],
            "contracts": ["CAP-task-intake"],
            "skills": ["doc/skills/create-task/SKILL.md"],
            "terms": ["TERM-task-json"]
          }
        },
        {
          "id": "reject-invalid-task-key",
          "title": "Отклонение синтаксически неверного ключа задачи",
          "decision_maker": "deterministic",
          "when": {"ambiguity": "none", "key_mode": "explicit_invalid", "collision": "*"},
          "transition": {"from": "unregistered", "to": "rejected", "state_unchanged_on_disk": true},
          "effects": {"mutates": [], "atomicity": "read_only"},
          "outcome": {
            "kind": "error",
            "exit_code": 1,
            "error_code": "VALIDATION",
            "summary": "parse_task_key отклоняет формат ключа до создания папок и изменения реестра",
            "postconditions": ["Ни каталог задачи, ни task-registry.json не изменены"]
          },
          "next": {"kind": "end"},
          "oracle_status": "verified",
          "refs": {
            "contracts": ["REG-cli-validation-rules#task-key"],
            "code": ["doc/tools/arch/validation.py#parse_task_key", "doc/tools/arch/task_ops.py"],
            "tests": ["doc/tests/test_task_identity.py"]
          }
        },
        {
          "id": "reject-existing-task-or-registry-conflict",
          "title": "Отклонение при коллизии каталога или номера в реестре",
          "decision_maker": "deterministic",
          "when": {"ambiguity": "none", "key_mode": ["auto_ui", "explicit_valid"], "collision": "exists"},
          "transition": {"from": "unregistered", "to": "rejected", "state_unchanged_on_disk": true},
          "effects": {"mutates": [], "atomicity": "read_only"},
          "outcome": {
            "kind": "error",
            "exit_code": 1,
            "error_code": "CONFLICT",
            "summary": "CLI блокирует перезапись существующей задачи или дублирование номера в реестре",
            "postconditions": ["Существующая карточка и task-registry.json сохранены без изменений"]
          },
          "next": {"kind": "end"},
          "oracle_status": "verified",
          "refs": {
            "contracts": ["REG-task-number-registry"],
            "code": ["doc/tools/arch/task_ops.py"],
            "tests": ["doc/tests/test_task_identity.py"]
          }
        },
        {
          "id": "allocate-ui-number-and-create",
          "title": "Выделение следующего UI-номера и создание задачи (arch task new)",
          "decision_maker": "deterministic",
          "when": {"ambiguity": "none", "key_mode": "auto_ui", "collision": "none"},
          "steps": [
            "Выделить следующий свободный 4-значный UI-номер в task-registry.json",
            "Создать doc/tasks/<task_key>/task.json и stage1/",
            "Зафиксировать запись в task-registry.json"
          ],
          "transition": {"from": ["unregistered", "awaiting_clarification"], "to": "scaffolded"},
          "effects": {
            "mutates": ["doc/config/task-registry.json", "doc/tasks/<task_key>/task.json", "doc/tasks/<task_key>/stage1/"],
            "atomicity": "atomic",
            "rollback": "Откат созданного каталога при ошибке записи карточки или реестра"
          },
          "outcome": {
            "kind": "ok",
            "exit_code": 0,
            "error_code": null,
            "summary": "Атомарно созданы карточка UI-задачи, stage1/ и запись в реестре номеров",
            "postconditions": [
              "arch task validate <task_key> завершается с exit 0",
              "arch task registry check завершается с exit 0"
            ]
          },
          "next": {"kind": "flow", "target": "FLOW-task-lifecycle"},
          "oracle_status": "verified",
          "refs": {
            "contracts": ["CAP-task-intake", "REG-task-number-registry", "ENT-task-input"],
            "flows": ["FLOW-task-lifecycle"],
            "code": ["doc/tools/arch/task_ops.py"],
            "tests": ["doc/tests/test_task_identity.py"]
          }
        },
        {
          "id": "init-explicit-task-key",
          "title": "Создание задачи с известным ключом (arch task init)",
          "decision_maker": "deterministic",
          "when": {"ambiguity": "none", "key_mode": "explicit_valid", "collision": "none"},
          "steps": [
            "Проверить ключ через parse_task_key (Jira bare number, UI-NNNN или PREFIX-NNNN)",
            "Создать doc/tasks/<task_key>/task.json и stage1/ и зарегистрировать ключ"
          ],
          "transition": {"from": ["unregistered", "awaiting_clarification"], "to": "scaffolded"},
          "effects": {
            "mutates": ["doc/config/task-registry.json", "doc/tasks/<task_key>/task.json", "doc/tasks/<task_key>/stage1/"],
            "atomicity": "atomic",
            "rollback": "Удаление незавершённого каталога при сбое записи"
          },
          "outcome": {
            "kind": "ok",
            "exit_code": 0,
            "error_code": null,
            "summary": "Зарегистрирована задача с внешним или заранее выделенным ключом",
            "postconditions": [
              "arch task validate <task_key> завершается с exit 0",
              "arch task registry check завершается с exit 0"
            ]
          },
          "next": {"kind": "flow", "target": "FLOW-task-lifecycle"},
          "oracle_status": "verified",
          "refs": {
            "contracts": ["CAP-task-intake", "ENT-task-input"],
            "flows": ["FLOW-task-lifecycle"],
            "code": ["doc/tools/arch/task_ops.py"],
            "tests": ["doc/tests/test_task_identity.py"]
          }
        }
      ]
    }
  ]
}
```

### 6.5. Эталонный пример 2 (фрагмент): почему каскад `COLLECT` + `UNIQUE` критичен для `FLOW-task-lifecycle`

В реальном `arch task diagnose` и `arch task close` (`doc/tools/arch/task_ops.py`) работают **два связанных узла с разными политиками**:
1. Узел **`diagnose-blockers` (`hit_policy: "COLLECT"`)** независимо проверяет факторы `deps_ok`, `subtasks_closed`, `plan_ready`, `evidence_fresh`, `worktree_clean` и **собирает все сработавшие блокировки в один список `close_blockers[]`** (не останавливаясь на первой!).
2. Следующий узел **`close-gate` (`hit_policy: "UNIQUE"`, `next` из первого узла)** смотрит на факторы `(mode: "dry_run" | "commit", has_blockers: true | false)`:
   - `(dry_run, true)` → `exit 0`, `would_close: false`, `atomicity: "read_only"`;
   - `(dry_run, false)` → `exit 0`, `would_close: true`, `atomicity: "read_only"`;
   - `(commit, true)` → `exit 1`, `state_unchanged_on_disk: true` (карточка, `state.json` и `events.jsonl` гарантированно не тронуты);
   - `(commit, false)` → `exit 0`, атомарный перевод в `completed/closed` и синхронизация статусов детей.

Плоская модель из исходной `UI-0029` выразить связку `COLLECT → UNIQUE` без ручного перемножения десятков комбинаций не могла; двухшаговый массив `decisions[]` выражает её компактно и математически проверяемо.

---

## 7. Детерминированные проверки CLI, граница ответственности и контракт графового индекса

### 7.1. Граница ответственности CLI vs агент/человек (единый подход с `UI-0028` §2.2 и `ARCH-contract` §8.2)

В соответствии с `architecture-contract.md` §8.2 и `manifest.md` CLI не пытается заменять семантическое мышление агента и человека, но монопольно владеет детерминированными инвариантами, чтением срезов и генерацией производных артефактов:

| Операция | Владелец | Обоснование |
|---|---|---|
| **Точечное чтение и радар связей** (`show`, `read FLOW-ID#branch`, `search --flows`, `context --flows`, `impact --flows`, `refs`) | **Только CLI** | Исключает чтение полных монолитов, выдаёт ранжирование, прямой контур `participating` и 1-hop контур отражения `impacted` в предсказуемом бюджете байт |
| **Генерация производных артефактов** (`flow build` → `<slug>.md` + `flows.index.json`) | **Только CLI** | Таблицы решений, Mermaid-диаграммы и обратный граф `referenced_by` обязаны быть 100% детерминированными и идемпотентными побайтно |
| **Проверка инвариантов и гейты** (`flow validate`, `flow check`, `task diagnose / close`) | **Только CLI** | Математическая проверка `0 gaps / 0 overlaps / no masked branch`, достижимости состояний, `refs`, `oracle_status` и отсутствия ручного дрейфа `.md` |
| **Применение структурных дельт веток** (`flow delta validate / apply`) | **CLI предпочтителен** | Проверяет `base_sha256` исходного `*.flow.json` (защита от тихого затирания соседних веток при параллельной работе) и атомарно правит ветку по `FLOW-ID#branch-id` |
| **Создание и полная правка `<slug>.flow.json`** | **CLI и прямая правка JSON допустимы** | Крупное дерево решений удобно писать целиком как валидный JSON-файл с обязательным последующим прогоном `flow validate` + `flow build` |
| **Семантика процесса** (выбор факторов, границ применимости, разнесение по веткам, решение «нужна ли новая ветка») | **Агент + человек** | CLI никогда не угадывает продуктовый смысл из сырого текста задачи и не генерирует фиктивные ветки автоматически |

### 7.2. Статические проверки `arch docs flow validate` (входят в `arch validate` и `--gate`)

1. **JSON Schema Draft 2020-12 (`arch-flow.schema.json`)**: строгий запрет неизвестных полей (`additionalProperties: false`), уникальность `branch.id` внутри флоу и глобальная уникальность `FLOW-ID` (при полном сохранении существующей `flow.schema.json` для `task-conf`).
2. **Проверка матрицы решений на каждом узле `decisions[]`:**
   - все ключи в `evaluated_factors` объявлены в `factors[]`, а ключи `branch.when` совпадают с `evaluated_factors` и используют только допустимые значения из `allowed_values` (либо `"*"`);
   - над конечным декартовым произведением `evaluated_factors` строятся множества покрываемых кортежей каждой ветки:
     - для **`UNIQUE`**: пересечение любых двух веток пусто (`0 overlaps`), а объединение покрывает всё декартово произведение (`0 gaps`);
     - для **`ANY`**: пересекающиеся ветки обязаны иметь одинаковый `outcome.kind` и `transition.to`;
     - для **`FIRST` / `PRIORITY`**: объединение покрывает 100% входов (`0 gaps`), и ни одна ветка не полностью поглощена вышестоящими ветками (**no masked/dead branch**!);
     - для **`COLLECT`**: ни одна ветка не имеет пустого покрытия и не дублирует условие другой ветки один в один.
3. **Проверка автомата жизненного цикла (`lifecycle`):**
   - при `mode == "stateful"` непусты `target_entities`, `initial_states` и `states`; все `transition.from` и `transition.to` ссылаются на объявленные `states[].id`;
   - графовая проверка: все состояния достижимы из `initial_states`, и из каждого `intermediate`-состояния существует путь хотя бы к одному `terminal`-состоянию (или к `next.kind == "flow"`);
   - проверка непротиворечивости эффектов: если `transition.state_unchanged_on_disk == true` или `effects.atomicity == "read_only"`, то `effects.mutates` обязан быть пустым `[]`; если `effects.mutates` непуст, `atomicity` не может быть `"read_only"`.
4. **Проверка ссылок и честности оракулов (`refs` + `oracle_status`):**
   - `refs.contracts`, `refs.rules` → резолвятся в существующие `DOC-ID` (и якоря `#section`, если указаны);
   - `refs.entities` → существующие `ENT-*`; `refs.flows` и `next.target` (при `kind == "flow"`) → существующие `FLOW-*`;
   - `refs.terms` → существующие `TERM-*` (проверяются против `glossary.json` при влитой `UI-0028`, либо с fallback на заголовки `TERM-*` в `glossary.md` до влития `UI-0028`);
   - `refs.skills`, `refs.code`, `refs.tests` → существующие проектно-относительные пути файлов, с проверкой символа `#symbol` в `refs.code` и точного узлового селектора `path/to/test.py[::TestClass[::test_case]]` в `refs.tests` (встроенный модуль `ast` для Python и плагинный слой `tree-sitter`/LSP для целевых многоязычных репозиториев);
   - если `oracle_status == "verified"`, массив `refs.tests` обязан содержать минимум 1 существующий селектор теста; если `decision_maker == "deterministic"` и `refs.tests` пуст, допустим только явный `oracle_status == "missing_oracle"` (который виден в отчётах диагностики и покрытия, но никогда не маскируется под проверенный).

### 7.3. Контракт графового индекса `doc/architecture/flows.index.json`

Поскольку `doc/architecture/schemas/index.schema.json` имеет `additionalProperties: false`, связующий граф флоу (как и `glossary.index.json` в `UI-0028`) хранится в отдельном детерминированном файле `doc/architecture/flows.index.json` (сортировка списков по `id`, отсортированные ключи JSON, завершающий `\n`):

```json
{
  "index_schema_version": 1,
  "flows": [
    {
      "id": "FLOW-create-task",
      "domain": "task-intake",
      "title": "Приём, выделение ключа и создание задачи",
      "status": "current",
      "implemented": true,
      "source_path": "doc/architecture/domains/task-intake/flows/create-task.flow.json",
      "generated_md_path": "doc/architecture/domains/task-intake/flows/create-task.md",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "target_entities": ["ENT-task-input", "ENT-task-record"],
      "decision_ids": ["intake-and-init"],
      "branch_count": 5,
      "oracle_counts": {"verified": 4, "missing_oracle": 0, "manual_only": 1}
    }
  ],
  "branches": [
    {
      "ref": "FLOW-create-task#allocate-ui-number-and-create",
      "flow_id": "FLOW-create-task",
      "decision_id": "intake-and-init",
      "branch_id": "allocate-ui-number-and-create",
      "title": "Выделение следующего UI-номера и создание задачи (arch task new)",
      "decision_maker": "deterministic",
      "when": {"ambiguity": "none", "key_mode": "auto_ui", "collision": "none"},
      "transition": {"from": ["unregistered", "awaiting_clarification"], "to": "scaffolded"},
      "mutates": ["doc/config/task-registry.json", "doc/tasks/<task_key>/task.json", "doc/tasks/<task_key>/stage1/"],
      "outcome": {"kind": "ok", "exit_code": 0, "error_code": null},
      "next": {"kind": "flow", "target": "FLOW-task-lifecycle"},
      "oracle_status": "verified",
      "refs": {
        "contracts": ["CAP-task-intake", "REG-task-number-registry", "ENT-task-input"],
        "flows": ["FLOW-task-lifecycle"],
        "terms": ["TERM-system-task-key", "TERM-system-task-json"],
        "code": ["doc/tools/arch/task_ops.py"],
        "tests": ["doc/tests/test_task_identity.py"]
      }
    }
  ],
  "referenced_by": {
    "by_entity": {
      "ENT-task-input": ["FLOW-create-task#allocate-ui-number-and-create", "FLOW-create-task#init-explicit-task-key"],
      "ENT-task-record": ["FLOW-create-task#allocate-ui-number-and-create", "FLOW-task-lifecycle#close-commit-ok"]
    },
    "by_contract": {
      "REG-task-number-registry": ["FLOW-create-task#reject-existing-task-or-registry-conflict", "FLOW-create-task#allocate-ui-number-and-create"]
    },
    "by_term": {
      "TERM-system-task-key": ["FLOW-create-task#reject-invalid-task-key", "FLOW-create-task#allocate-ui-number-and-create"]
    },
    "by_code": {
      "doc/tools/arch/task_ops.py": ["FLOW-create-task#allocate-ui-number-and-create", "FLOW-create-task#init-explicit-task-key"],
      "doc/tools/arch/validation.py#parse_task_key": ["FLOW-create-task#reject-invalid-task-key"]
    },
    "by_test": {
      "doc/tests/test_task_identity.py": ["FLOW-create-task#reject-invalid-task-key", "FLOW-create-task#allocate-ui-number-and-create"]
    },
    "by_mutated_path": {
      "doc/config/task-registry.json": ["FLOW-create-task#allocate-ui-number-and-create", "FLOW-create-task#init-explicit-task-key"]
    },
    "by_flow": {
      "FLOW-task-lifecycle": [
        {"from_branch": "FLOW-create-task#allocate-ui-number-and-create", "via": "next.target"},
        {"from_branch": "FLOW-create-task#init-explicit-task-key", "via": "next.target"}
      ]
    },
    "by_task": {
      "UI-0032": [{"path": "doc/tasks/UI-0032/task.json", "field": "flow_refs", "target": "FLOW-verify-task"}]
    }
  }
}
```

### 7.4. Полный справочник CLI-команд работы с флоу (коды возврата `CliEnvelope`, условия вызова и бюджеты)

Все команды подчиняются единому конверту `CliEnvelope` из [doc/tools/arch/cli/errors.py](doc/tools/arch/cli/errors.py) (`{ok, code, data, errors: [{code, message, field, suggestion, exit_code}], hints}`) и семантическим кодам возврата фабрики:
- **`0` (`EXIT_OK`)** — успех;
- **`1` (`EXIT_ERROR`)** — нарушение схемы, дыра/пересечение в таблице решений, недостижимое состояние, битая ссылка, дрейф generated-файла или провал гейта;
- **`2` (`EXIT_ARGS`)** — синтаксически неверный идентификатор (`FLOW-*`, `FLOW-*#branch-id`) или несовместимые флаги;
- **`5` (`EXIT_CONFLICT`)** — несовпадение `base_sha256` при `delta apply`, дубликат `FLOW-ID` или `branch.id`;
- **`10` (`EXIT_AUTH`)** — попытка записи вне разрешённых путей `paths.yaml`;
- **`20` (`EXIT_NOT_FOUND`)** — запрошенный `FLOW-*` или ветка `#branch-id` не найдены.

> **Важная привязка к полям `task.json` (`REG-cli-validation-rules`):** в текущей реализации `validate_task_json()` ([doc/tools/arch/validation.py](doc/tools/arch/validation.py)) поле `related_docs` проверяется регулярным выражением `TASK_KEY_RE` (то есть хранит ссылки на соседние задачи, а не на документы!). Архитектурные документы лежат в `project_context_refs`, а для точной адресации флоу и конкретных веток в `task.json` вводится отдельное типизированное поле **`"flow_refs": ["FLOW-...", "FLOW-...#branch-id"]`** (по прямой аналогии с полем `"glossary_terms"` из `UI-0028` §4.4), дополняющее существующие поля `contracts_and_invariants`, `allowed_files_modules` и `related_tests`.

| Команда CLI | Когда и кем вызывается | Что делает и какой срез возвращает | Коды выхода |
|---|---|---|---|
| `arch docs flow list [--domain <d>] [--status <s>] [--implemented true\|false] [--json]` | Разведка домена, планирование, обзор | Компактный перечень флоу из `flows.index.json` с числом узлов, веток и сводкой `oracle_counts` (~100 байт на флоу) | `0`, `2` |
| `arch docs flow show <FLOW-ID> --view summary\|decisions\|transitions\|mermaid\|refs\|gaps [--max-bytes N] [--json]` | Скиллы `architecture-read`, `plan-task`, `review-implementation` | Выдаёт ровно одну проекцию выбранного флоу без загрузки соседних секций | `0`, `2`, `20` |
| `arch docs read <FLOW-ID>[#<branch-id>] [--max-bytes N] [--json]` | Скиллы `plan-task`, `go-to-task` (точечное чтение ветки) | При указании `#branch-id` возвращает карточку **одной ветки** + только её `evaluated_factors`, `invariants` родителя и `refs` (0.5–1.5 КБ) | `0`, `2`, `20` |
| `arch docs flow refs <TARGET> [--kind entity\|contract\|term\|code\|test\|path\|flow\|task] [--json]` | `architecture-read`, `incident-response`, `refactor`, `migration` | Мгновенная обратная выборка из `flows.index.json#referenced_by`: какие именно `FLOW-ID#branch-id` завязаны на указанный файл/символ, `ENT-*`, `CAP-*`, `TERM-*` или `FLOW-*` | `0`, `2`, `20` |
| `arch docs search "<query>" [--flows] [--domain <d>] [--path <p>] [--symbol <s>] [--no-expand-terms] [--json]` | Шаг `intent` (`create-task`, `jira-incoming`), первичный поиск | Расширяет запрос синонимами из `glossary.index.json` (`UI-0028`) и ранжирует совпавшие флоу и ветки по `id`, `title`, факторам, `error_code`, `TERM-*` и `refs.code` | `0`, `2` |
| `arch docs context --task <KEY> [--flows] [--max-bytes N] [--json]` | Шаги `architecture-context` и `implement` (`go-to-task`) | Строит **двухкольцевой радар задачи** (`participating` + 1-hop `impacted` + `unmapped_paths` + `missing_oracles`) в рамках бюджета байт | `0`, `2`, `20` |
| `arch docs impact [--since <rev> \| --paths <p...>] [--scope all\|arch\|code] --flows [--json]` | `architecture-context` (по путям) и `review-implementation` (по `git diff`) | Сверяет список планируемых файлов или реальный `git diff` с графом флоу: показывает затронутые ветки, косвенно задетые потоки и непокрытые изменения кода (`unmapped_code_changes`) | `0`, `1`, `2` |
| `arch docs flow validate [--id <FLOW-ID>] [--json]` | Авторство `*.flow.json`, шаг `architecture-sync`, `arch validate` | Проверяет JSON Schema (`arch-flow.schema.json`), полноту и пересечения таблиц решений (`0 gaps`, `0 overlaps`, `no masked`), граф состояний `lifecycle`, межфлоу-стыки, `refs` (`AST #symbol`, `TERM-*`, `ENT-*`) и `oracle_status` | `0`, `1`, `2`, `20` |
| `arch docs flow build [--id <FLOW-ID>] [--json]` | Шаг `architecture-sync`, миграция, создание/обновление флоу | Детерминированно генерирует `<slug>.md` (таблицы решений + Mermaid) и глобальный `doc/architecture/flows.index.json` (повторный вызов побайтно идемпотентен) | `0`, `1`, `10` |
| `arch docs flow check [--json]` | `--gate`, CI, `verify`, `task diagnose / close` | Проверяет без записи на диск, что все `<slug>.md` и `flows.index.json` побайтно соответствуют текущим `*.flow.json` (ловит любую ручную правку витрин) | `0`, `1` |
| `arch docs flow coverage [--domain <d>] [--ratchet --since <rev>] [--strict] [--json]` | Контроль полноты описания флоу, постепенный онбординг больших brownfield-баз (`--ratchet`), задачи `audit` и релизный гейт | Строит отчёт полноты по репозиторию (или с `--ratchet` — **только по затронутым в diff модулям**, не блокируя работу со старым непокрытым кодом): % покрытия модулей (с учётом `exempt_globs`), команд/эндпоинтов, `CAP-*` и оракулов `verified` | `0`, `1` (при `--strict`/`--ratchet` и наличии дыр) |
| `arch docs flow correlate (--task <KEY> \| --entity <ENT-*> \| --term <TERM-*> \| --contract <DOC-*> \| --path <p>) [--depth 1\|2] [--include-unmapped] [--json]` | Скилл **`flow-audit`**, планирование эпика/миграции, поиск всех процессов вокруг сущности или задачи | Собирает по графу все коррелирующие флоу (прямые `distance: 0` и сцепленные `distance: 1..2` через общие `ENT-*`, `mutates`, `next.target`, `TERM-*`, `refs.code`), а также соседние непокрытые функции тех же модулей (`unmapped_correlated_symbols`) | `0`, `2`, `20` |
| `arch docs flow inspect <FLOW-ID \| path[#symbol]> [--json]` | Выделенный скилл **`flow-audit`**, `brownfield_bootstrap`, расследование расхождений кода и флоу | Детерминированно разбирает AST/символы привязанных функций и сверяет сигналы кода с ветками флоу: находит неучтённые `exit_code` / `http_status` / `error_code`, операции записи на `read_only`-путях, непокрытые публичные функции, тесты-кандидаты и точные номера строк `lines` | `0`, `1`, `2`, `20` |
| `arch docs flow capsule (--task <KEY> \| --branch <FLOW-ID#branch-id>) [--budget-tokens <N>] [--mode execute\|review\|plan] [--json]` | **Одновызовный пакет для слабых/дешёвых моделей** в `go-to-task` / `review-implementation` (**Zero-Archaeology Capsule**, §13.4) | За **1 вызов CLI** собирает хирургическую капсулу (`1.5K–4.5K` токенов): только целевые ветки JSON (без соседних веток-дистракторов), точные AST-вырезки кода `lines`, 1-строчное кольцо `impacted`, точные селекторы `refs.tests` и список защищённых инвариантов/путей Trust Zone | `0`, `2`, `20` |
| `arch docs flow verify (<FLOW-ID>[#<branch-id>] \| --changed \| --task <KEY>) [--assert-guard] [--atomicity-check] [--json]` | Быстрый внутренний цикл проверки (`<2 с`) и защита от взлома тестов слабой моделью (§13.5) | Запускает только узловые селекторы `refs.tests` затронутых веток; с `--assert-guard` блокирует несанкционированное удаление/ослабление `assert*` в тестах и правку `*.flow.json`; с `--atomicity-check` проверяет побайтную неизменность дерева при отказе (`read_only` / `state_unchanged_on_disk`) | `0`, `1`, `2`, `10`, `20` |
| `arch docs flow delta validate <path/to/flow-delta.json> [--json]` | Шаг `plan` (`plan-task`) | Проверяет схему `flow-delta.schema.json`, существование целевых `FLOW-ID` / `decision_id` / `branch_id` и корректность результирующей матрицы решений в памяти без изменения файлов | `0`, `1`, `2`, `5`, `20` |
| `arch docs flow delta apply <path/to/flow-delta.json> [--dry-run] [--json]` | Шаг `architecture-sync` (`go-to-task`) | Сверяет `base_sha256` целевого `*.flow.json` (при расхождении веток — `exit 5 CONFLICT`), атомарно применяет операции `add_branch \| modify_branch \| remove_branch \| supersede_branch \| remap_code` и валидирует результат | `0`, `1`, `2`, `5`, `10`, `20` |
| `arch scan --scope flows [--json]` | Периодический аудит (`audit`), `arch scan` | Неблокирующий санитарный скан: ищет `stale_provenance` (код в `refs.code` многократно менялся после ревизии флоу), зависшие `missing_oracle`, неиспользуемые `deprecated`/`superseded` флоу и новые `unmapped_domain_code` | `0`, `1` |
| `arch task decompose <KEY> --spec <file> [--json]` *(расширение)* | Планирование сложной задачи с подзадачами `0001..NNNN` | При наличии `flow_refs` у подзадач проверяет отсутствие неучтённого конфликта параллельной правки одной и той же ветки `FLOW-ID#branch-id` между независимыми детьми | `0`, `1`, `5` |
| `arch task diagnose <KEY> [--json]` / `arch task close <KEY> [--dry-run] [--json]` *(расширение)* | Финальный гейт закрытия любой задачи | Проверяет: нет неприменённого `stageN/flow-delta.json`; `flow check` зелёный; при правке файла из `by_code` обновлён флоу либо указан `unchanged_contract`; тесты затронутых `verified`-веток входят в свежий снимок `verification.json` | `0`, `1` |

Пример компактного двухкольцевого ответа `arch docs context --task <KEY> --flows --json` (и `arch docs impact --flows --json`):

```json
{
  "participating": {
    "flows": ["FLOW-create-task"],
    "branches": [
      {
        "ref": "FLOW-create-task#reject-invalid-task-key",
        "reason": "declared_in_task_flow_refs",
        "oracle_status": "verified",
        "entities": ["ENT-task-input"],
        "contracts": ["REG-cli-validation-rules#task-key"],
        "terms": ["TERM-system-task-key"],
        "code": ["doc/tools/arch/validation.py#parse_task_key"],
        "tests": ["doc/tests/test_task_identity.py"]
      }
    ],
    "missing_oracles": []
  },
  "impacted": {
    "upstream_callers": [],
    "downstream_flows": [
      {"flow_id": "FLOW-task-lifecycle", "via_branch": "FLOW-create-task#init-explicit-task-key"}
    ],
    "shared_entities_and_mutations": [
      {
        "branch": "FLOW-create-task#allocate-ui-number-and-create",
        "shared_on": ["ENT-task-input", "doc/config/task-registry.json"]
      }
    ],
    "shared_code_and_contracts": [
      {
        "branch": "FLOW-subtask-lifecycle#validate-parent-key",
        "shared_on": ["doc/tools/arch/validation.py#parse_task_key"]
      }
    ],
    "competing_open_tasks": []
  },
  "unmapped_paths": []
}
```

---

## 8. Целевая структура переработанной задачи `UI-0029`, инвентарь файлов и запреты

### 8.1. Четырёхшаговая декомпозиция подзадач на живом корпусе `sf`

Вместо текущего плана с игрушечным репозиторием предлагается чёткая 4-шаговая декомпозиция на живом корпусе `sf` (с предметными типами детей в соответствии с `UI-0030` и валидными командами проверки по политике `UI-0032`):

1. **`UI-0029-0001` (`task_type: "docs"`, `flow: "docs-only"`): ADR, `arch-flow.schema.json` и контракт в `ARCH-contract`**
   - Выпустить `ADR-0003-flow-json-canon.md` (смена источника `type: flow` на `*.flow.json` с генерируемым `<slug>.md` и `flows.index.json`, граница CLI, разграничение с `task-conf` и режим пополнения через дельты веток).
   - Создать `doc/architecture/schemas/arch-flow.schema.json` (не затрагивая существующую `schemas/flow.schema.json` от `task-conf`!) и обновить `ARCH-contract` §5.5E.
   - *(Важно по порядку шагов, как в `UI-0028` §6: регистрация `generated_files` в `paths.yaml` переносится в конец шага с готовым генератором, чтобы не сломать `arch docs paths --check` раньше времени).*
2. **`UI-0029-0002` (`task_type: "feature"`, `flow: "standard-implementation"`, `depends_on: ["0001"]`): Модуль `arch_flows.py`, `validate/build/check/show/refs/delta` и радар в `docs`**
   - Реализовать модуль `doc/tools/arch/arch_flows.py` (не смешивая имя с `flows.py`, отвечающим за `task-conf`!): проверка схемы `arch-flow.schema.json`, матриц решений (`gaps`, `overlaps`, `masked`), графа `lifecycle`, `refs` (включая `TERM-*` и `ast`-проверку символов Python) и `oracle_status`; генерация `<slug>.md` (с Mermaid) и `flows.index.json`; структурные операции `delta validate/apply`; двухкольцевой радар (`participating` + `impacted` + `unmapped_paths`) в `docs read / search / context / impact / check-links` и `validate`.
   - Покрыть все позитивные и отказные кейсы (дыра в матрице решений, пересечение в `UNIQUE`, замаскированная ветка в `FIRST`, недостижимое состояние, непустой `mutates` при `read_only`, битая ссылка на символ кода, несовпадение `base_sha256` при `delta apply`, ручная правка generated `.md`, побайтовая идемпотентность повторного `build`) unit-тестами.
3. **`UI-0029-0003` (`task_type: "refactor"`, `flow: "standard-implementation"`, `depends_on: ["0002"]`): Полная миграция и расчистка всех 8 `FLOW-*` самой системы `sf`**
   - Перевести реальные системные процессы `sf` в `*.flow.json` (`FLOW-create-task`, `FLOW-task-lifecycle`, `FLOW-subtask-lifecycle`, `FLOW-verify-task`, `FLOW-document-session`, `FLOW-kilo-session-audit` + при согласовании `FLOW-docs-context-and-impact`), связав ветки с реальными файлами `doc/tools/arch/*.py`, терминами `TERM-*`, сущностями `ENT-*` и тестами `doc/tests/*.py`.
   - Вынести справочник JSON-полей и SQL из `kilo-session-audit` в `implementation-spec`, пометить поглощённые дубли (`FLOW-execute-task`, `FLOW-cli-task-lifecycle`) статусом `superseded` с `superseded_by`, удалить мёртвую `schemas/bodies/flow.json`, обновить `paths.yaml` (`generated_files`), сгенерировать все `<slug>.md` и `flows.index.json`.
4. **`UI-0029-0004` (`task_type: "feature"`, `flow: "standard-implementation"`, `depends_on: ["0003"]`): Интеграция со скиллами, шагами `task-conf`, гейтом `diagnose/close` и сквозная приёмка**
   - Обновить скиллы (`create-task`, `plan-task`, `architecture-read`, `architecture-docs`, `arch-cli`, `go-to-task`, `review-implementation`, `document-session`) и промпты шагов `architecture-context` / `plan` / `architecture-sync`.
   - Подключить валидацию `flow_refs` в `task.json`, проверку синхронизации дельт и свежести `evidence` к `arch task diagnose` и `arch task close` (`--dry-run` и боевой режим) и провести сквозную приёмку со всеми гейтами `sf`.

### 8.2. Инвентарь создаваемых и изменяемых файлов (по образцу `UI-0028` §3)

| Действие | Путь | Роль |
|---|---|---|
| **Создать** | `doc/architecture/decisions/ADR-0003-flow-json-canon.md` | Архитектурное решение о JSON-каноне `*.flow.json`, generated `.md`, графе `flows.index.json` и цикле пополнения |
| **Создать** | `doc/architecture/schemas/arch-flow.schema.json` | JSON Schema Draft 2020-12 для архитектурных системных флоу (`*.flow.json`) |
| **Создать** | `doc/architecture/schemas/flow-delta.schema.json` | JSON Schema плановой дельты веток `stageN/flow-delta.json` с защитой `base_sha256` |
| **Создать** | `doc/architecture/flows.index.json` | Generated-граф ветвлений и обратных ссылок `referenced_by` |
| **Создать** | `doc/architecture/domains/**/flows/*.flow.json` | Канонические JSON-модели реальных системных флоу `sf` |
| **Создать** | `doc/tools/arch/arch_flows.py` | Ядро загрузки, проверки матриц решений и `lifecycle`, сборки `.md`/`flows.index.json`, радара `participating/impacted` и `delta apply` |
| **Создать** | `doc/tools/arch/cli/commands/arch_flow.py` | CLI-команды `arch docs flow list\|show\|refs\|correlate\|inspect\|capsule\|verify\|validate\|build\|check\|coverage\|delta` |
| **Создать** | `doc/skills/flow-audit/SKILL.md` | Выделенный скилл глубокого расследования кода, аудита коррелирующих флоу и достраивания/декомпозиции `*.flow.json` |
| **Создать** | `doc/tests/test_arch_flows.py` | Unit- и контрактные тесты схем, таблиц решений, графа состояний, AST-инспектора, дельт и идемпотентности `build` |
| **Удалить** | `doc/architecture/schemas/bodies/flow.json` | Мёртвая H2-схема старых Markdown-флоу (удаляется синхронно с миграцией в `0003`) |
| **Изменить** | `doc/architecture/domains/**/flows/*.md` | Переводятся в статус `generated_files` (генерируются из `*.flow.json`) |
| **Изменить** | `doc/config/paths.yaml` | Регистрация `*.flow.json`, `flows.index.json`, generated `flows/*.md`, `skills/flow-audit/SKILL.md` и новых подкоманд CLI |
| **Изменить** | `doc/AGENTS.md` и `doc/skills/README.md` | Добавление одной строки-роутера на скилл `flow-audit` (по правилу роутера `Rules vs Skills.md`) |
| **Изменить** | `doc/tools/arch/body_validation.py` | Переключение проверки `type: flow` со старой `bodies/flow.json` на связку `*.flow.json` + `flow check` |
| **Изменить** | `doc/tools/arch/doc_ops.py` | Адресное чтение `FLOW-ID#branch-id`, расширение `search`, двухкольцевой радар в `context` и `impact` |
| **Изменить** | `doc/tools/arch/validation.py`, `task_record.py`, `task_ops.py` | Поддержка `flow_refs` в `task.json` и проверка синхронизации флоу в `task diagnose` / `task close` |
| **Изменить** | `doc/architecture/system/{architecture-contract,cli-command-map,cli-validation-rules}.md` | Отражение контракта `*.flow.json`, команд `arch docs flow` и кодов ошибок |
| **Изменить** | `doc/skills/{create-task,plan-task,architecture-read,architecture-docs,arch-cli,go-to-task,review-implementation,document-session}/SKILL.md` | Короткие маршруты работы с `flows.index.json`, `participating/impacted` и дельтами веток |

### 8.3. Чего делать нельзя (жёсткие архитектурные предохранители)

- **Нельзя перезаписывать `doc/architecture/schemas/flow.schema.json`** — этот файл уже валидирует конфигурационные маршруты задач `task-conf` (`schema_version: "flow-1"`). Схема архитектурных флоу называется `arch-flow.schema.json`.
- **Нельзя менять `doc/architecture/schemas/index.schema.json`**, чтобы протащить ветки и обратные ссылки в `index.json` (`additionalProperties: false`). Весь граф ветвлений живёт в `flows.index.json`.
- **Нельзя вводить YAML-канон для архитектурных флоу** — `doc/architecture/system/data.md` («Политика формата») прямо закрепляет JSON для машинных записей и индексов.
- **Нельзя создавать игрушечные репозитории (`orders/billing/shipping`) или дублирующий тип `product-flow`** — единственным полигоном и потребителем является живая система `sf` и канонический `type: flow`.
- **Нельзя хранить ручные обратные ссылки (`referenced_by`) внутри `ENT-*`, `glossary.json`, `CAP-*` или `.py`-файлов** — ссылки пишутся только на стороне ссылающегося (`branch.refs` и `task.json`), а обратный индекс вычисляется в `flows.index.json` при `build`.
- **Нельзя дублировать в `*.flow.json` определения терминов глоссария, поля схем сущностей или справку по флагам CLI** — флоу связывает их по ID, оставаясь компактной картой решений.
- **Нельзя заменять весь `*.flow.json` вслепую при параллельных задачах без проверки `base_sha256`** и нельзя молча переименовывать существующие `branch.id` без явной операции `supersede / rename`.
- **Нельзя ставить `oracle_status: "verified"` без реального пути в `refs.tests`** или подменять детерминированный тест оценкой LLM.

---

## 9. Открытые вопросы и точки решений для дальнейшей проработки

*(Раздел для совместного уточнения при доработке этого документа)*:

1. **Состав итоговых системных флоу `sf` для 100% покрытия модулей (п. 3.3 и п. 11.3):**
   - Подтверждаем ли целевой набор из **9 активных `*.flow.json`** (`FLOW-create-task`, `FLOW-task-lifecycle`, `FLOW-task-flow-execution` для движка `flows.py`, `FLOW-subtask-lifecycle`, `FLOW-verify-task`, `FLOW-document-session`, `FLOW-kilo-session-audit`, плюс два новых флоу для ранее пустого домена `project-knowledge`: `FLOW-docs-validation-and-indexing` и `FLOW-docs-retrieval-and-impact`) + 1 плановый `FLOW-role-model-routing` (`implemented: false`) + 2 `superseded` (`FLOW-execute-task`, `FLOW-cli-task-lifecycle`), либо объединяем движок `flows.py` узлами внутрь `FLOW-task-lifecycle` (итого 8 активных флоу)?
2. **Соотношение номеров `ADR-0002` / `ADR-0003` и порядок с `UI-0028`, `UI-0030`, `UI-0031`:**
   - В `UI-0028` уже зарезервирован путь `ADR-0002-glossary-json-store.md`, а поле `terms` в `branch.refs` стыкуется с `TERM-*` из `UI-0028`. Подтверждаем ли двустороннюю мягкую стыковку (проверять `refs.terms` против `glossary.json`, если он уже создан, иначе против заголовков `TERM-*` в `glossary.md`), чтобы `UI-0029` и `UI-0028` можно было вливать в любом порядке?
3. **Глубина проверки ссылок на код (`refs.code`):**
   - Достаточно ли на первом срезе проверять `path/to/module.py` + разбор `def / class` через стандартный модуль `ast` Python для синтаксиса `doc/tools/arch/validation.py#parse_task_key` (со статусом `unverified_symbol` для не-Python файлов), без внешних анализаторов?
4. **Формат сгенерированного Markdown (`<slug>.md`):**
   - Включаем ли в генерируемый `<slug>.md` обе Mermaid-диаграммы по умолчанию (`flowchart TD` по узлам решений и `stateDiagram-v2` для `lifecycle.mode == "stateful"`), или только таблицу решений + одну компактную диаграмму переходов, чтобы размер generated `.md` гарантированно укладывался в бюджет чтения `<15 КБ`?
5. **Хранение плановой дельты флоу внутри карточки задачи (`stageN/flow-delta.json`):**
   - Фиксируем ли на шаге `plan` отдельный файл `doc/tasks/<KEY>/stageN/flow-delta.json` (с `mode: "unchanged_contract" | "branch_delta" | "brownfield_bootstrap"`, `base_sha256` и списком операций над ветками), который на шаге `architecture-sync` применяется командой `arch docs flow delta apply`, либо разрешаем для простых одноэтапных задач сразу править `*.flow.json` в рабочей ветке задачи?
6. **Политика гейта `diagnose / close` для `unmapped_code_changes` (код без привязанного флоу):**
   - Выбираем ли градуированный режим: **жёсткий `error` (блокер закрытия)** только если задача изменила файлы в уже поставленных на учёт ядерных доменах (`task-intake`, `task-lifecycle`, `execution-verification`) и нарушила/рассинхронизировала привязанный флоу, а для новых/вспомогательных модулей без флоу выдаём **`warning` в `diagnose` и `impact`** с предложением `brownfield_bootstrap`?

---

## 10. Флоу как связующий каркас архитектуры и цикл их пополнения/использования (`OpenSpec`, `Spec Kit`, `EventCatalog`, `sf`)

### 10.1. Почему именно `*.flow.json` становится «позвоночником» всей документации для агента (и как не превратить его в God-object)

Сверка с материалами `data/` ([Пример пакета документации фичи.md](data/machinedocs-encyclopedia/Примеры/Пример%20пакета%20документации%20фичи.md), [Код, контекст и минимальный harness.md](data/machinedocs-encyclopedia/Практики/Код,%20контекст%20и%20минимальный%20harness.md), [Исследование формата документации проекта и входящей задачи.md](data/machinedocs-encyclopedia/Практики/Исследование%20формата%20документации%20проекта%20и%20входящей%20задачи.md)) подтверждает ключевой архитектурный вывод: **именно `FLOW-*` является главным связующим узлом (connective spine) проектного знания для агента** — при условии строгого разделения статических и динамических осей:

| Слой знания в `sf` | Канонический артефакт | За что отвечает единолично | Чего в нём быть **не должно** |
|---|---|---|---|
| **Словарь домена** | `glossary.json` (`TERM-*`, `UI-0028`) | Официальное имя термина, определение, `official_synonyms`, `search_synonyms`, `avoid` | Описания ветвлений процессов и списков задач |
| **Сущности данных** | `ENT-*.md` | Поля структуры данных, типы и внутренние инварианты самой сущности | Маршрутов многошаговой оркестрации между разными командами |
| **Бизнес- и системные правила** | `CAP-*.md`, `REG-*.md` | Нормативные требования и границы допустимого («что обязано выполняться») | Пересказа пошаговых деревьев исполнения |
| **Архитектурные решения** | `ADR-*.md` | Причина выбора, компромиссы (`trade-offs`) и отвергнутые альтернативы | Оперативных таблиц ветвления текущего кода |
| **Код и тесты** | `doc/tools/arch/*.py`, `doc/tests/*.py` | Фактическое исполняемое поведение и проверяемый тестовый оракул | Продуктового замысла (`intent`) и границ `not_included` |
| **Системные флоу (связующий каркас)** | **`*.flow.json` (`FLOW-*#branch-id`)** | **Причинно-следственная сшивка всех атомов в дерево решений и переходов состояний:** *триггер/факторы → правило (`CAP/REG`) → сущность (`ENT`) → термины (`TERM`) → код (`code#symbol`) → соседний флоу (`next.target`) → тест (`tests`)* | Копипасты определений терминов, JSON-схем сущностей и полных сигнатур CLI |

**Как исключается ручной рассинхрон связей:**
- Авторство ссылок **строго однонаправленное** (`branch.refs` в `*.flow.json` + `flow_refs` в `task.json`, как в `UI-0028` §2.3).
- При каждом `arch docs flow build` автоматически пересчитывается полный обратный граф `flows.index.json#referenced_by`. Поэтому по любому файлу кода, термину, сущности или бизнес-правилу CLI за миллисекунды отвечает, в каких именно ветках каких процессов этот элемент задействован.

### 10.2. Экономика контекста: двунаправленный радар на входе в задачу вместо чтения монолитов

В [Код, контекст и минимальный harness.md](data/machinedocs-encyclopedia/Практики/Код,%20контекст%20и%20минимальный%20harness.md), [Управление контекстом многоагентных систем.md](data/machinedocs-encyclopedia/Практики/Управление%20контекстом%20многоагентных%20систем.md) и [Следование архитектуре.md](data/machinedocs-encyclopedia/Документация/Следование%20архитектуре.md) выделены два базовых закона агентной разработки:
1. **Контекст — конечный ресурс с убывающей отдачей:** широкие обзорные инструкции конкурируют с задачей за внимание модели и раздувают расход токенов, тогда как just-in-time подгрузка по точному индексу даёт максимальную точность.
2. **Risk map at input дешевле review at output:** агент обязан увидеть карту рисков и соседних зависимостей *до* первой правки кода.

Граф `flows.index.json` превращает `arch docs context --task <KEY> --flows --json` в компактную дорожную карту (1–3 КБ JSON) из **двух колец и детектора слепых зон**:
- **Кольцо 1 — `participating` (какие флоу непосредственно участвуют в задаче):** точные ветки `FLOW-ID#branch-id`, которые реализуют целевое изменение, вместе со списком только их `TERM-*`, `ENT-*`, `CAP-*/REG-*`, файлов кода и тестов + список `missing_oracles` (где тест необходимо добавить в план приёмки).
- **Кольцо 2 — `impacted` (на каких флоу задача отражается косвенно / 1-hop Blast Radius):**
  1. `upstream_callers` — ветки других флоу, передающие управление в изменяемый флоу через `next.target`;
  2. `downstream_flows` — процессы, в которые переходит управление после выполнения наших веток;
  3. `shared_entities_and_mutations` — соседние ветки, читающие или меняющие те же `target_entities` (`ENT-*`) или пути `effects.mutates`;
  4. `shared_code_and_contracts` — ветки других процессов, опирающиеся на тот же символ кода `refs.code` или правило `refs.contracts`;
  5. `competing_open_tasks` — незакрытые задачи бэклога (`doc/tasks/*/task.json`), завязанные на те же ветки (предотвращение параллельных семантических конфликтов, стыковка с `taskcontrol.md`).
- **Детектор слепых зон — `unmapped_paths`:** затронутые задачей файлы кода, которые ещё не привязаны ни к одной ветке в `flows.index.json#referenced_by.by_code` (сигнал для `brownfield_bootstrap`).

### 10.3. Детальная сверка с `GitHub Spec Kit`, `OpenSpec` и `EventCatalog`: как пополняются и используются хранимые флоу

| Система и источники | Хранение флоу и архитектуры | Использование в планировании и кодинге | Механизм пополнения от задачи к задаче | Практические пробелы (2025–2026) и как их закрывает `sf` |
|---|---|---|---|---|
| **GitHub Spec Kit** ([GitHub Spec Kit.md](data/sdd-encyclopedia/Инструменты/GitHub%20Spec%20Kit.md), [Discussion #152](https://github.com/github/spec-kit/discussions/152), [Thoughtworks Radar Vol. 34, Apr 2026](https://www.thoughtworks.com/content/dam/thoughtworks/documents/radar/2026/04/tr_technology_radar_vol_34_en.pdf)) | **Папки отдельных фич** `specs/NNN-feature/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/`) + общая `constitution.md`. Единого системного реестра флоу в ядре нет. | Конвейер `/speckit.specify → clarify → plan → tasks → analyze → implement`. Команда `/speckit.analyze` ищет противоречия только внутри пакета одной текущей фичи. | В базовом Spec Kit завершённые фичи лежат как исторический архив и не складываются автоматически в единую живую карту системы; для слияния в канон сообщество создаёт надстройки `spec-kit-archive` и `canon` ([#152](https://github.com/github/spec-kit/discussions/152)). | 1) Агент не видит сквозной карты прошлых флоу и обратного влияния между фичами; 2) большой расход токенов на полные Markdown-документы на каждый тикет. **В `sf`:** единый живой граф `flows.index.json` + точечная JSON-выборка по веткам. |
| **Fission-AI OpenSpec v1.0–1.13 (OPSX)** ([OpenSpec.md](data/sdd-encyclopedia/Инструменты/OpenSpec.md), [Delta Specs.md](data/sdd-encyclopedia/Сущности/Delta%20Specs.md), [workflows.md](https://github.com/Fission-AI/OpenSpec/blob/main/docs/workflows.md), [openspec-parallel-merge-plan.md](https://github.com/Fission-AI/OpenSpec/blob/main/openspec-parallel-merge-plan.md), [OpenSpec 1.13 Review](https://developertoolkit.ai/en/ecosystem/frameworks/openspec/)) | **Два хранилища:**<br>1) `openspec/specs/<capability>/spec.md` — живая истина системы;<br>2) `openspec/changes/<id>/` — рабочая папка задачи (`proposal.md`, `design.md`, `tasks.md` и дельта `ADDED / MODIFIED / REMOVED / RENAMED`). | В `/opsx:explore` и `/opsx:propose` читаются только затронутые capability-спеки (кратная экономия контекста). В `/opsx:apply` код пишется по `tasks.md`. В `/opsx:verify` LLM сверяет реализацию с дельтой. | **Эталонный brownfield-цикл:**<br>• Недокументированный модуль при первом касании оформляется через `ADDED` (текущее поведение под characterization-тестами + новое требование);<br>• Изменение оформляется через `MODIFIED`;<br>• На финише `/opsx:sync` + `/opsx:archive` вливают дельту в `openspec/specs/` и убирают задачу в архив. | **Две реальные болезни OpenSpec 2026 г.:**<br>1) Markdown-блок `MODIFIED` заменяет требование целиком и при параллельных задачах тихо затирал соседние сценарии — авторы в `openspec-parallel-merge-plan.md` сами спроектировали переход на **стабильные ID сценариев и хеш-отпечатки базы**;<br>2) нет типизированного графа `флоу ↔ ENT ↔ TERM ↔ код ↔ тесты`, полноту в `verify` угадывает LLM. **В `sf`:** адресация сразу по `FLOW-ID#branch-id` + проверка `base_sha256` + 100% детерминированный CLI-гейт. |
| **EventCatalog v3–v5 (MCP Architecture Graph)** ([Сущности.md](data/machinedocs-encyclopedia/Документация/Сущности.md), [EventCatalog Jan 2026](https://www.eventcatalog.dev/blog/eventcatalog-january-2026), [Document AI Agents](https://www.eventcatalog.dev/blog/document-ai-agents), [EventCatalog v5](https://www.eventcatalog.dev/blog/eventcatalog-v5)) | **Типизированный граф архитектуры:** домены, сервисы, агенты, команды/события, схемы, `flows` и `ubiquitous-language` с версиями и ID. | Через MCP/CLI агент вызывает узкие запросы `find_resources`, `find_producers_and_consumers` (blast radius), `explain_ubiquitous_language_terms`, `review_schema_changes` без загрузки всего репо. | Обновляется в PR вместе с кодом; автоматические проверки блокируют несовместимые изменения схем и нарушения ADR. | Требует внешнего сервера/коммерческой лицензии Scale, заточен под микросервисные события и не связан с локальными карточками задач и `verification.json`. **В `sf`:** весь граф живёт локально в Git (`flows.index.json` + `glossary.index.json`) и вшит прямо в `arch-cli` и `task-conf`. |

### 10.4. Как, когда и при каких условиях читаются и обновляются флоу (4 уровня чтения + все 12 типов задач + все 9 скиллов)

#### 10.4.1. Четыре уровня прогрессивного чтения (`Index-First` + `Progressive Disclosure`)

Чтобы агент никогда не вычитывал лишнего ([Index-First подход.md](data/machinedocs-encyclopedia/Архитектура/Index-First%20подход.md), [Progressive Disclosure.md](data/cli-skills-encyclopedia/Форматы/Progressive%20Disclosure.md), [Токен-эффективность.md](data/cli-skills-encyclopedia/Практики/Токен-эффективность.md)), чтение флоу строго градуировано на **4 уровня зума** по условию задачи:

| Уровень зума | Условие входа («когда читать именно этот уровень») | Команда CLI | Типичный объём |
|---|---|---|---|
| **Zoom 0 — Навигационный радар** | Старт любой задачи, поиск по запросу, путям или терминам, проверка радиуса влияния | `arch docs search --flows`, `arch docs flow list`, `arch docs flow refs <target>`, `arch docs context --task <KEY> --flows` | **0.5 – 2.5 КБ** |
| **Zoom 1 — Проекция одного среза** | Понимание общей развилки процесса или его графа состояний без чтения чужих деталей | `arch docs flow show <FLOW-ID> --view summary \| decisions \| transitions \| refs` | **1.0 – 3.5 КБ** |
| **Zoom 2 — Точечная ветка (основной рабочий режим)** | Планирование `AC → CASE`, написание кода и тестов конкретной развилки `FLOW-ID#branch-id` | `arch docs read <FLOW-ID>#<branch-id> --json` | **0.5 – 1.5 КБ** |
| **Zoom 3 — Полный `<slug>.flow.json` или `<slug>.md`** | **Только** при создании нового флоу (`brownfield_bootstrap`), крупной перестройке факторов `factors[]` всего узла или ручном визуальном ревью человеком в Git/просмотрщике | Прямое чтение `<slug>.flow.json` (авторство) или `<slug>.md` (человек) | **5 – 15 КБ** |

#### 10.4.2. Пошаговая работа на базовом конвейере `standard-implementation`

В [doc/config/task-conf/types/feature/flows/standard-implementation/config.yaml](doc/config/task-conf/types/feature/flows/standard-implementation/config.yaml) уже заложены все 8 шагов, в которые работа с `*.flow.json` встраивается без создания параллельного конвейера:

| Шаг `task-conf` (`standard-implementation`) | Что делает агент и `arch` CLI с графом `*.flow.json` | Читаемый / создаваемый артефакт | Детерминированный гейт шага |
|---|---|---|---|
| **1. `intent`** (`create-task` / `intake`) | Нормализует термины запроса через `arch glossary query` (`UI-0028`) и делает поиск `arch docs search "<query>" --flows --json`. Записывает предварительные `flow_refs` в `task.json`. | `doc/tasks/<KEY>/task.json` (`flow_refs`, `glossary_terms`) | Блокирующие вопросы scope сняты; указанные `FLOW-*` существуют |
| **2. `architecture-context`** | Вызывает `arch docs context --task <KEY> --flows --json` (и при известных путях `arch docs impact --paths ... --flows --json`). Получает `participating`, `impacted` и `unmapped_paths` за 1 вызов; дочитывает только целевые ветки (`Zoom 2`). | Секция архитектурного контекста и радиуса влияния в `stageN/plan.md` | Все участвующие и отражённые потоки, их инварианты и конфликты зафиксированы |
| **3. `plan`** | Выбирает один из **4 режимов** (`unchanged_contract`, `code_remap`, `branch_delta`, `brownfield_bootstrap`), связывает ветки с матрицей трассируемости `AC ↔ FLOW-ID#branch ↔ CASE` и при изменении/создании веток формирует `stageN/flow-delta.json` с `base_sha256`. При декомпозиции (`arch task decompose`) разводит подзадачи `0001..NNNN` по непересекающимся веткам (или ставит `depends_on`). | `stageN/plan.md` + `stageN/flow-delta.json` | У каждого `AC` и каждой затронутой детерминированной ветки есть проверяемый `CASE`; `flow delta validate` — `exit 0` |
| **4. `implement`** (`refactor` / `fix`) | Пишет код и тесты в границах `effects.mutates` и `allowed_files_modules`, соблюдая `invariants` своего флоу и постусловия соседних веток из кольца `impacted`. | Изменённые модули кода и тесты | Целевые unit/контрактные тесты проходят, выход за разрешённый scope отсутствует |
| **5. `review-implementation`** | Запускает на стабильном снимке `arch docs impact --since <base_rev> --scope all --flows --json`: сверяет реальный `git diff` кода с заявленной дельтой веток, проверяет `impacted`-ветки и `unmapped_code_changes`. | Отчёт ревью в `stageN/plan.md` | Нет расхождений между фактическим diff кода и планом дельты флоу |
| **6. `architecture-sync`** | Применяет подтверждённую поведением дельту к канону (`arch docs flow delta apply stageN/flow-delta.json` с проверкой `base_sha256`), затем запускает `arch docs flow build` (пересборка `<slug>.md` и `flows.index.json`). | Обновлённые `<slug>.flow.json`, `<slug>.md`, `flows.index.json` | `arch docs flow validate` и `arch docs flow check` — `exit 0` |
| **7. `verify`** | Прогоняет финальные проверки и тесты из плана стадии, записывает команды, коды возврата и SHA-256 снимка `checked_revision` в `stageN/verification.json`. | `stageN/verification.json` | Все обязательные `CASE` зелёные на текущем снимке; все `verified`-ветки имеют существующие тесты |
| **8. `close`** | `arch task diagnose <KEY>` и `arch task close <KEY>` проверяют отсутствие дрейфа `flows.index.json`/`<slug>.md`, отсутствие неприменённых `flow-delta.json` и свежесть `evidence`. | Закрытая карточка задачи + актуальный граф системы | `diagnose` — 0 блокеров; обновлённый флоу сразу доступен следующей задаче |

#### 10.4.3. Полная матрица всех 12 типов задач и 16 маршрутов `doc/config/task-conf/types/*`

Система постановки и реализации задач `sf` включает **12 типов задач и 16 конфигурационных маршрутов**. Ниже зафиксировано поведение работы с `*.flow.json` для каждого из них:

| Тип задачи (`task_type`) | Маршруты в `task-conf/types/<type>/flows/` | Как читает `*.flow.json` | Как пополняет / обновляет `*.flow.json` | Обязательный гейт на выходе |
|---|---|---|---|---|
| **`feature`** | `standard-implementation`<br>`research-first` | В `standard-implementation`: `Zoom 0 → Zoom 2` (`participating` + `impacted`). В `research-first`: `flow list/show` + `coverage` | В `standard-implementation`: `branch_delta` или `brownfield_bootstrap` (новая функциональность). В `research-first`: только черновик `implemented: false, status: "draft"` либо без записи в канон | `flow validate`, `flow check`, покрытие новых детерминированных веток тестами (`verified`) |
| **`bugfix`** | `standard-implementation`<br>`minimal-scaffold` | На шаге `reproduce`/`scaffold` через `flow refs <path#symbol>` находит ветку, где произошёл сбой | **Два случая:** (1) код нарушил верную ветку в `*.flow.json` → `unchanged_contract` + добавление регрессионного теста в `refs.tests` (`missing_oracle → verified`); (2) в самом флоу был пропущен краевой случай → `branch_delta` с расщеплением ветки | Регрессионный тест привязан к ветке; соседние ветки `impacted` не сломаны |
| **`refactor`** | `standard-implementation`<br>`minimal-scaffold` | В `analyze`: читает `flow show --view decisions` и `flow refs <module>`, фиксируя неизменность внешнего дерева решений | Основной режим — **`code_remap`**: условия `when`, переходы и `outcome` остаются неизменными, обновляются только пути/символы в `refs.code` при переносе функций/модулей | `flow validate` подтверждает валидность всех новых `#symbol` в AST Python |
| **`docs`** | `docs-only` (`architecture-context → change → validate → close`) | Читает `arch-flow.schema.json`, целевой `*.flow.json` и связанные `ENT-*/CAP-*/TERM-*` | Прямое создание/миграция `*.flow.json` (включая `implemented: false` проектные флоу или уточнение `summary`/`refs`) + `flow build` | `flow validate`, `flow check`, `index check`, `docs check-links` — `exit 0` |
| **`jira-incoming`** | `jira-process` (`intake → architecture-context → plan → ... → close`) | На шаге `intake` нормализует внешний язык тикета через `glossary match/search` (`UI-0028`) и строит радар `context --flows` | Полностью идентично `feature` / `bugfix` (`unchanged_contract`, `branch_delta` или `brownfield_bootstrap`) на шаге `architecture-sync` | Полный гейт `standard-implementation` (локально в Git, без автозаписи обратно в Jira) |
| **`incident`** | `incident-response` (`plan → verify → close`) | Сверхбыстрый путь: `arch docs flow refs <error_code_or_file>` мгновенно показывает ветку отказа, её `atomicity`, `rollback` и `impacted` потоки | Горячий фикс закрывает инцидент с `unchanged_contract` или минимальной `branch_delta`; при обнаружении новой ветки отказа она фиксируется с обязательным регрессионным тестом | `flow check` + прохождение теста воспроизведения инцидента |
| **`migration`** | `migration-first` (`plan → verify → close`) | Через `flows.index.json#referenced_by` (`by_entity`, `by_mutated_path`) собирает **100% флоу**, читающих или пишущих мигрируемый формат (`task.json`, `state.json`, схемы) | Обновляет `applicability` (`task_schema`, `cli_version`), `invariants` и ветки миграции во всех затронутых `*.flow.json` | Ни один поток из `by_entity` не остался на старой версии контракта без ветки совместимости |
| **`audit`** | `research-first` (`audit → report → close`) | Запускает `arch docs flow coverage --json`, `arch docs flow validate --json`, `arch scan --scope flows --json` | Read-only аудит: не меняет код, формирует отчёт о дырах покрытия (`unmapped_domain_code`), `missing_oracle` и `stale_provenance` (и при необходимости порождает задачи в бэклоге) | Отчёт опирается на воспроизводимый JSON-вывод команд `coverage` и `scan` |
| **`planning`** | `standard-implementation`<br>`research-first` | Читает `flow list`, `flow show --view decisions`, `context --flows` для декомпозиции эпика | Не меняет `implemented: true` флоу напрямую; раскладывает будущие подзадачи по целевым `FLOW-ID#branch-id` (и может выпустить проектный `status: "draft", implemented: false` флоу) | При `task decompose` нет неучтённых коллизий веток между параллельными подзадачами |
| **`research`** | `research-first` (`research → recommend → close`) | Читает `flow list / show` для понимания ограничений текущей системы | Канон `implemented: true` не мутирует; результаты сохраняются в `doc/tasks/<KEY>/research/*.md` | `flow check` подтверждает неизменность канона |
| **`spike`** | `spike-first` (`plan → verify → close`) | Читает `participating` и `impacted` для оценки технической реализуемости гипотезы | Прототипирование не меняет `implemented: true` канон до принятия решения о боевой реализации (`feature`) | Чистое состояние канонических `*.flow.json` при закрытии спайка |
| **`scaffold`** | `minimal-scaffold` (`scaffold → close`) | Проверяет через `flow refs`, не пересекается ли новый каркас с существующими путями `by_mutated_path` | Если создаётся каркас нового домена — опционально добавляет черновой `<slug>.flow.json` (`implemented: false, status: "draft"`) + `flow build` | `docs paths --check` и `flow check` — `exit 0` |

#### 10.4.4. Матрица всех 10 агентских скиллов (`9` существующих + новый выделенный `flow-audit`)

| Скилл (`doc/skills/...`) | Условие активации | Какие команды флоу обязан использовать | Что запрещено делать в скилле |
|---|---|---|---|
| **`flow-audit`** *(новый выделенный скилл)* | Запрос «проверь/дострой флоу по коду», режим `brownfield_bootstrap`, задачи типа `audit`, либо срабатывание гейтов `FF-4`/`FF-5` на расхождение кода и флоу | `flow refs` / `context --flows` → **`flow inspect <target> --json`** → точечное чтение строк `line_start..line_end` кода → триаж расхождений → достройка/расщепление `*.flow.json` → `flow validate && flow build` | Вслепую копировать баги кода в `*.flow.json` без сверки с `CAP-*/REG-*/ENT-*`, вычитывать весь монорепо без `flow inspect` или превращать домен в один гигантский мега-флоу |
| **`architecture-read`** | Любой запрос контекста архитектуры на входе/планировании/ревью | Роутер: известен `FLOW-ID` → `flow show`; известна ветка → `docs read FLOW-ID#branch`; известен файл/сущность/термин → `flow refs`; есть карточка задачи → `docs context --task <KEY> --flows` | Вычитывать целиком все `domains/**/flows/*.md`, читать исходники `.py` без нужды или грузить монолитные спеки без предварительного `Zoom 0` |
| **`create-task`** | Регистрация новой задачи из чата или трекера | `glossary query` + `docs search "<query>" --flows` → записывает найденные `FLOW-*` / `FLOW-*#branch` в `task.json#flow_refs` | Выдумывать несуществующие `FLOW-ID` или класть ссылки на документы в `related_docs` (там только `TASK_KEY_RE`) |
| **`plan-task`** | Написание/ревизия `stageN/plan.md` и декомпозиция | `docs context --task <KEY> --flows`, `docs read FLOW-ID#branch`, запись таблицы `AC ↔ FLOW-ID#branch ↔ CASE`, выбор режима в `stageN/flow-delta.json`, `flow delta validate` | Оставлять детерминированную новую/изменённую ветку без `CASE` или планировать параллельную правку одной ветки в двух независимых подзадачах |
| **`go-to-task`** | Продолжение, реализация, синхронизация, верификация и закрытие задачи | На старте: `docs context --flows`; на `architecture-sync`: `flow delta apply` + `flow build` + `flow validate`; перед закрытием: `flow check` + `task diagnose` | Закрывать задачу при неприменённом `flow-delta.json` или править generated `<slug>.md` руками |
| **`architecture-docs`** | Прямая работа с файлами в `doc/architecture/` | Проверка по `arch-flow.schema.json`, строгая связка `правка *.flow.json → flow validate → flow build → flow check` | Редактировать файлы из `generated_files` (`flows/*.md`, `flows.index.json`) напрямую в обход `flow build` |
| **`review-implementation`** | Ревью готового кода на стабильном снимке | `docs impact --since <base_rev> --scope all --flows --json` + сверка каждого изменённого файла кода со списком `participating`, постусловиями `impacted` и статусом `oracle_status` | Одобрять изменение модуля из `by_code`, если нарушен инвариант ветки или забыта синхронизация `*.flow.json` |
| **`document-session`** | Явная команда владельца «задокументируй» по итогам сессии | Проверяет ветку `FLOW-document-session`, вносит подтверждённые факты (`provenance`, `refs.code`, `refs.tests`) в `*.flow.json`, запускает `flow validate && flow build && check-links` | Записывать неподтверждённые гипотезы как `implemented: true` или менять исходную постановку `task.json` задним числом |
| **`kilo-session-audit`** | Аудит сессий в `kilo.db` (`session find / digest / events`) | Следует веткам `FLOW-kilo-session-audit`; при аудите эффективности агента проверяет по `tool_calls`, использовал ли агент точечные `context --flows` / `read FLOW#branch` вместо чтения монолитов | Выполнять сырой поиск по всей `kilo.db` в обход детерминированных команд `arch session` |
| **`arch-cli`** | Справочник команд `arch` для агента | Содержит краткую шпаргалку подгруппы `arch docs flow` (`list, show, refs, validate, build, check, coverage, delta`) и кодов возврата `0/1/2/5/10/20` | Дублировать полное описание JSON Schema внутри `SKILL.md` (схема лежит в `arch-flow.schema.json`) |

### 10.5. Четыре штатных режима пополнения базы флоу и формат `stageN/flow-delta.json`

В соответствии с деревом решений *«Нужен ли артефакт?»* из [Код, контекст и минимальный harness.md](data/machinedocs-encyclopedia/Практики/Код,%20контекст%20и%20минимальный%20harness.md) пополнение базы флоу работает в четырёх чётких режимах:

1. **Режим A — `unchanged_contract` (контракт веток не меняется):**
   - *Когда:* исправление бага реализации под уже верную ветку, внутренняя оптимизация, добавление недостающего теста (перевод `missing_oracle → verified`) или правка вне логики процессов.
   - *Действие:* ветки из `participating` маппятся в `AC → CASE`; фиксируется `mode: "unchanged_contract"` и `reason` (чтобы гейт `architecture-sync` отличил осознанное отсутствие правок флоу от забывчивости).
2. **Режим B — `code_remap` (чистый рефакторинг без смены дерева решений):**
   - *Когда:* функции/модули переименовываются или разрезаются (`refactor`), но матрица факторов `when`, переходы `lifecycle` и исходы `outcome` остаются инвариантными.
   - *Действие:* обновляются только якоря `refs.code` / `refs.tests`; `flow validate` гарантирует, что ни один бизнес-исход не изменился, а все новые `#symbol` реально существуют в AST Python.
3. **Режим C — `branch_delta` (эволюция существующего процесса):**
   - *Когда:* добавляется новый фактор, новая ветка успеха/ошибки, меняется переход состояний, `effects.mutates` или межфлоу-переход `next.target`.
   - *Действие:* атомарная дельта по стабильным ID `FLOW-ID#branch-id` с фиксацией `base_sha256` целевого `<slug>.flow.json`. Если параллельная задача правила другую ветку — применение проходит без потерь; если ту же ветку или `evaluated_factors` — `flow delta apply` возвращает `exit 5 (CONFLICT)` вместо тихого затирания!
4. **Режим D — `brownfield_bootstrap` (первичный заход в «тёмный» участок кода без флоу):**
   - *Когда:* радар показал `unmapped_paths` на доменном модуле с нетривиальным ветвлением или жизненным циклом.
   - *Действие:* в рамках этой же задачи создаётся `<slug>.flow.json` **только для затронутого процесса** (опорные текущие ветки + новая ветка задачи). Карта логики проекта органически зарастает по ходу реальной работы без требования описывать весь мир заранее.

Пример компактного файла `doc/tasks/<KEY>/stage1/flow-delta.json` (режим `branch_delta`):

```json
{
  "schema_version": 1,
  "task_key": "UI-0035",
  "stage": "stage1",
  "mode": "branch_delta",
  "targets": [
    {
      "flow_id": "FLOW-create-task",
      "source_path": "doc/architecture/domains/task-intake/flows/create-task.flow.json",
      "base_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "operations": [
        {
          "op": "modify_branch",
          "decision_id": "intake-and-init",
          "branch_id": "reject-invalid-task-key",
          "patch": {
            "refs": {
              "contracts": ["REG-cli-validation-rules#task-key"],
              "terms": ["TERM-system-task-key"],
              "code": ["doc/tools/arch/validation.py#parse_task_key", "doc/tools/arch/task_ops.py"],
              "tests": ["doc/tests/test_task_identity.py"]
            }
          }
        }
      ]
    }
  ]
}
```

### 10.6. Градуированная политика для `unmapped_code_changes` (`measure → warn → enforce`)

В соответствии с практикой внедрения архитектурных гейтов из [Аудит архитектуры.md](data/machinedocs-encyclopedia/Документация/Аудит%20архитектуры.md) (`measure → warn → enforce`):
- **Уровень `error` (жёсткий блокер `validate` / `diagnose` / `close`):**
  1. Любое нарушение схемы `arch-flow.schema.json`, неполнота/пересечение матрицы решений (`gaps / overlaps / masked`), недостижимое состояние, битая ссылка `refs` или ручная правка generated `<slug>.md` / `flows.index.json`.
  2. Наличие неприменённого `stageN/flow-delta.json` на момент `close`.
  3. Изменение `.py`-модуля, уже привязанного к ветке `FLOW-ID#branch-id` (или нового доменного файла внутри уже покрытых ядерных доменов при включённом `strict`), если не выполнено ни обновление `*.flow.json`, ни явная фиксация `unchanged_contract` / `code_remap` с зелёными `refs.tests`.
- **Уровень `warning` (сигнал в `docs impact` и `task diagnose` без паралича мелких правок):**
  - Изменение модуля вне `exempt_globs`, который ещё не привязан ни к одному `*.flow.json` (`unmapped_code_changes`) — выдаёт явную подсказку `hints` рассмотреть `brownfield_bootstrap`.

---

## 11. Четырёхуровневый контроль полноты и непрерывная защита от устаревания (Anti-Drift Fitness Functions)

Чтобы система не деградировала со временем ни в сторону «полупустых флоу только для happy-path», ни в сторону «забытых модулей без флоу», ни в сторону «протухших спек, разошедшихся с кодом», в `sf` вводятся **4 ортогональных уровня контроля полноты и актуальности**.

### 11.1. Уровень 1 — Полнота и непротиворечивость вариантов решений внутри узла (`Decision Completeness`)

Проверяется детерминированно в `arch docs flow validate` на каждом узле `decisions[]`:
1. **Математическая полнота комбинаций (`0 gaps`):** объединение множеств кортежей `when` по всем веткам узла обязано покрывать 100% декартова произведения $\prod_{f \in \text{evaluated\_factors}} \text{allowed\_values}(f)$. Если добавлен новый вариант в `allowed_values` (например, третий режим ключа), валидатор мгновенно перечисляет все непокрытые кортежи входов.
2. **Отсутствие скрытых противоречий (`0 overlaps` / `no masked branch`):**
   - при `hit_policy: "UNIQUE"` любые два пересекающихся кортежа дают `exit 1` с указанием конфликтующих `branch.id`;
   - при `hit_policy: "FIRST" | "PRIORITY"` проверяется, что ни одна нижестоящая ветка не поглощена полностью вышестоящими правилами (нет «мёртвых веток», которые никогда не сработают).
3. **Запрет «немых wildcard-заглушек» и проверка негативных исходов:**
   - запрещено покрывать весь узел единственной веткой со сплошными `"*"` (минимальное число содержательных веток на узел с факторами $\ge 2$);
   - если процесс не является чисто информационным (`stateless` + `read_only`), отсутствие хотя бы одной ветки с `outcome.kind` $\in \{\text{"error"}, \text{"blocked"}, \text{"finding"}\}$ поднимает предупреждение `happy_path_only_warning` (защита от главной ошибки описания флоу по [Флоу.md](data/machinedocs-encyclopedia/Документация/Флоу.md) — фиксации только успешного пути).
4. **Честное разделение природы решателя (`decision_maker`):**
   - ветка с `decision_maker: "deterministic"` не может иметь `oracle_status: "manual_only"` (детерминированное правило обязано быть проверяемым либо `verified`, либо явно светиться в техническом долге как `missing_oracle`);
   - ветки `agent_judgment` и `human_approval` обязаны ссылаться на скилл (`refs.skills`) или правило полномочий (`refs.rules` / `refs.contracts`).

### 11.2. Уровень 2 — Полнота жизненного цикла и межпотоковых стыков (`Lifecycle & Inter-Flow Completeness`)

Проверяется в `arch docs flow validate` по всему корпусу `*.flow.json`:
1. **Полнота автомата состояний (`stateful`):**
   - каждое состояние из `lifecycle.states` достижимо хотя бы по одному пути из `initial_states` (нет «островных» состояний);
   - из каждого `intermediate`-состояния существует ориентированный путь хотя бы в одно `terminal`-состояния или в межпотоковый переход `next.kind == "flow"` (нет «ловушек без выхода»);
   - для каждой ветки с `outcome.kind == "error"` или `"blocked"` явно задано либо сохранение состояния на диске (`state_unchanged_on_disk: true` + `mutates: []`), либо компенсирующее действие `effects.rollback`.
2. **Стыковка границ между соседними флоу (`Inter-Flow Handshake`):**
   - если ветка `FLOW-A#b1` завершается переходом `next: {"kind": "flow", "target": "FLOW-B"}`, валидатор проверяет:
     - `FLOW-B` существует и не имеет статус `deprecated`/`superseded` (если `FLOW-A` сам `current`);
     - при пересечении `target_entities` у `FLOW-A` и `FLOW-B` целевое состояние `transition.to` ветки `FLOW-A#b1` совместимо с `initial_states` приёмника `FLOW-B` (например, `FLOW-create-task` переводит задачу в `scaffolded`, с которого стартует `FLOW-task-lifecycle`).
3. **Ссылочная полнота связующего каркаса:**
   - все `ENT-*`, `CAP-*`, `REG-*`, `ADR-*`, `TERM-*`, `doc/skills/*/SKILL.md`, `doc/tools/arch/*.py#symbol` и `doc/tests/*.py` реально существуют; ни одна ссылка не висит в воздухе.

### 11.3. Уровень 3 — Контроль полноты описания ВСЕХ флоу проекта (`arch docs flow coverage`)

Чтобы владелец и агент в любой момент знали, **вся ли логика системы `sf` покрыта задокументированными флоу или появились «белые пятна»**, команда `arch docs flow coverage [--domain <d>] [--strict] [--json]` вычисляет **4 объективные метрики полноты по всему репозиторию**:

1. **`module_coverage` (покрытие кодовой базы `doc/tools/arch/**/*.py`):**
   - сканирует все `.py`-файлы в `doc/tools/arch/`, вычитает явно задекларированный в `doc/config/paths.yaml` список инфраструктурных утилит `flow_coverage.exempt_globs` (константы, обёртки ввода-вывода, базовые классы CLI) и проверяет, что каждый оставшийся доменный модуль входит в `flows.index.json#referenced_by.by_code` хотя бы одного актуального `FLOW-*`.
2. **`cli_surface_coverage` (покрытие командного интерфейса `arch`):**
   - извлекает зарегистрированные в `cli/commands/*.py` подкоманды CLI и сверяет их с покрытием веток `*.flow.json`: ни одна новая команда CLI не может появиться в коде незаметно для карты флоу.
3. **`capability_coverage` (покрытие доменных возможностей `CAP-*`):**
   - проверяет каждый документ `type: capability` в `doc/architecture/domains/**`:
     - если у `CAP-*` стоит `implemented: true`, в этом домене обязан существовать минимум один `FLOW-*` со статусом `current`/`accepted`, ссылающийся на данный `CAP-*` в `refs.contracts`;
     - если `implemented: false` (как `CAP-role-model-routing`), он учитывается в корзине `planned_capabilities` без ложной тревоги, пока флаг `implemented` не переключён в `true`!
4. **`oracle_coverage` (покрытие детерминированных веток исполняемыми тестами):**
   - считает по каждому флоу и по проекту в целом долю `verified / (verified + missing_oracle)` среди всех веток с `decision_maker == "deterministic"`, а также блокирует **регрессию оракулов** (перевод ранее `verified`-ветки обратно в `missing_oracle`).

Пример машинного отчёта `arch docs flow coverage --json` на целевом состоянии `sf`:

```json
{
  "summary": {
    "active_flows": 9,
    "planned_flows": 1,
    "superseded_flows": 2,
    "total_branches": 46,
    "module_coverage_pct": 100.0,
    "cli_surface_coverage_pct": 100.0,
    "implemented_capability_coverage_pct": 100.0,
    "deterministic_oracle_coverage_pct": 95.2
  },
  "gaps": {
    "unmapped_domain_modules": [],
    "unmapped_cli_commands": [],
    "implemented_capabilities_without_flow": [],
    "missing_oracle_branches": [
      "FLOW-document-session#abort-ambiguous-evidence"
    ]
  },
  "planned": {
    "capabilities": ["CAP-role-model-routing"],
    "flows": ["FLOW-role-model-routing"]
  },
  "exempt_infrastructure_count": 14
}
```

### 11.4. Уровень 4 — Пять эшелонов непрерывного поддержания актуальности (`Anti-Drift Fitness Functions`)

По стандарту описания архитектурных fitness-функций из [Аудит архитектуры.md](data/machinedocs-encyclopedia/Документация/Аудит%20архитектуры.md) и [SDD в CI-CD.md](data/sdd-encyclopedia/Процессы/SDD%20в%20CI-CD.md) (*Сигнал → Механизм → Момент запуска → Реакция на сбой → Путь исключения*) актуальность `*.flow.json` удерживается пятью автоматическими контурами:

| № | Fitness-функция (что ловит) | Измеримый сигнал | Механизм проверки | Когда срабатывает (`Cadence`) | Действие при сбое (`Action`) и путь исключения |
|---|---|---|---|---|---|
| **FF-1** | **Дрейф схемы, матриц решений и ссылок на код/термины** (удалена/переименована функция `#symbol`, файл, тест, `TERM-*`, `ENT-*`, появилась дыра в `when`) | Невалидный JSON, `gaps > 0`, `overlaps > 0`, отсутствующий путь или AST-символ | `arch docs flow validate` (входит в `arch validate`) | Локально при правке, на шаге `architecture-sync`, в CI `--gate` | **`Block` (`exit 1`)**; исключений нет — битая ссылка или дыра в матрице исправляются немедленно |
| **FF-2** | **Ручная правка сгенерированных витрин** (кто-то поправил `flows/<slug>.md` или `flows.index.json` мимо `*.flow.json`) | Побайтовое расхождение файла на диске с выводом генератора в памяти | `arch docs flow check` (и `arch docs paths --check`) | Шаг `verify`, `task diagnose/close`, pre-merge CI `--gate` | **`Block` (`exit 1`)**; лечится одной командой `arch docs flow build` после переноса смысла в `*.flow.json` |
| **FF-3** | **Тихое затирание соседних веток при параллельной работе задач** | `sha256(current *.flow.json) != flow_delta.base_sha256` на затронутом узле/ветке | `arch docs flow delta apply` | Шаг `architecture-sync` | **`Block` (`exit 5 CONFLICT`)**; агент перечитывает обновлённый узел и пересобирает дельту без потери чужих веток |
| **FF-4** | **Тихое расхождение кода и флоу внутри задачи** (`git diff` меняет модуль из `by_code`, но ни `*.flow.json`, ни `unchanged_contract`/`code_remap` не оформлены, либо не применён `flow-delta.json`) | Непустой пересекающийся diff в `docs impact --since <base_rev> --flows` без синхронизации | `arch task diagnose <KEY>` и `arch task close <KEY>` | На `review-implementation` и перед закрытием задачи (`close`) | **`Block` (`exit 1`)**; законный обход для чисто внутренних правок — явная запись `mode: "unchanged_contract"` с прохождением `refs.tests` в `verification.json` |
| **FF-5** | **Накопление «белых пятен» и устаревание `provenance`** (появился новый доменный модуль без флоу, либо модуль из `refs.code` менялся много раз без ревизии веток) | `unmapped_domain_modules > 0`, `missing_oracle`, отставание `provenance` по истории Git | `arch docs flow coverage` и `arch scan --scope flows` | На шаге `audit`, при релизной проверке и по расписанию | **`Warn` на обычных задачах → `Block` при `--strict` на релизе**; легальный путь для утилит — добавление в `flow_coverage.exempt_globs` владельцем |

---

## 12. Симбиоз CLI и агента при расследовании кода (`flow-audit`) и критерии декомпозиции границ флоу

### 12.1. Почему нужен отдельный скилл `doc/skills/flow-audit/SKILL.md` в паре с AST-инспектором CLI

В [Работа агентов с CLI.md](data/cli-skills-encyclopedia/Практики/Работа%20агентов%20с%20CLI.md), [Rules vs Skills.md](data/cli-skills-encyclopedia/Практики/Rules%20vs%20Skills.md) и [Код, контекст и минимальный harness.md](data/machinedocs-encyclopedia/Практики/Код,%20контекст%20и%20минимальный%20harness.md) зафиксирована фундаментальная граница между детерминированным инструментом (`Computational Sensor`) и рассуждающим агентом (`Inferential Investigator`):

- **Чего не может голый CLI без агента:** статический парсер видит в Python-коде ветвления `if/elif/else` и возвраты `error_envelope(...)`, но **не знает смысла предметной области** — является ли конкретная проверка в коде полноценной бизнес-веткой, низкоуровневой технической прослойкой или вообще **багом реализации**, противоречащим замыслу владельца (`CAP-*`/`REG-*`).
- **Чего не должен делать агент без CLI:** вручную грепать тысячи строк кода в поисках всех связанных сущностей, забытых кодов возврата, функций записи на диск и комбинаторных дыр в матрицах решений (дорого по токенам и ненадёжно из-за эффекта *Lost in the Middle*).
- **Почему именно отдельный скилл `flow-audit`, а не раздувание `architecture-read` или `AGENTS.md`:**
  - по правилу `Rules vs Skills.md` (*«AGENTS.md — короткий роутер в одну строку; мультишаговая процедура для части задач выносится в отдельный скилл»*) обычный `architecture-read` должен оставаться сверхлёгким навигатором на каждый день (в [doc/AGENTS.md](doc/AGENTS.md) прямо закреплено: *«При обычном использовании не читайте реализацию CLI»*);
  - а глубокое расследование исходников, сверка коррелирующих флоу по сущности/задаче и достраивание `*.flow.json` выделяются в специализированный скилл **`doc/skills/flow-audit/SKILL.md`** с одной строкой-триггером в таблице режимов `doc/AGENTS.md`:
    > *«Проверить полноту флоу по коду, расследовать расхождение или достроить флоу для задачи/сущности → Прочитать `skills/flow-audit/SKILL.md`»*.

### 12.2. Две специальные команды CLI для подачи фактов в скилл `flow-audit`: `flow correlate` и `flow inspect`

Чтобы агент в скилле `flow-audit` не искал связи вручную и не читал целиком модули по 1500–1800 строк (паттерн нормализованных находок из [Инструменты аудита для software factory.md](data/machinedocs-encyclopedia/Практики/Инструменты%20аудита%20для%20software%20factory.md)), CLI предоставляет связку двух детерминированных команд:

#### А. Поиск всех коррелирующих флоу вокруг задачи, сущности, правила или файла — `arch docs flow correlate`

Команда `arch docs flow correlate (--task <KEY> | --entity <ENT-*> | --term <TERM-*> | --contract <DOC-*> | --path <path>) [--depth 1|2] [--include-unmapped] [--json]` решает стартовую задачу расследования, когда агент знает только карточку задачи или сущность (например, `ENT-task-record`) и должен найти **все связанные с ней процессы и слепые пятна в коде**:
- **`direct_flows` (`distance: 0`):** флоу, в которых указанный объект прямо стоит в `target_entities`, `branch.refs` или `task.json#flow_refs`;
- **`coupled_flows` (`distance: 1..2`):** соседние флоу, связанные через передачу управления `next.target`, общие мутируемые пути `effects.mutates`, общие модули кода `refs.code` или общие термины `TERM-*`;
- **`unmapped_correlated_symbols`:** публичные функции в тех же `.py`-модулях (или соседних файлах пакета, импортирующих ту же модель/константы), которые ещё не привязаны ни к одной ветке в `flows.index.json`!

Пример вывода `arch docs flow correlate --entity ENT-task-record --include-unmapped --json`:

```json
{
  "seed": {"kind": "entity", "id": "ENT-task-record"},
  "direct_flows": [
    {
      "flow_id": "FLOW-create-task",
      "matched_branches": ["FLOW-create-task#allocate-ui-number-and-create", "FLOW-create-task#init-explicit-task-key"],
      "via": "lifecycle.target_entities"
    },
    {
      "flow_id": "FLOW-task-lifecycle",
      "matched_branches": ["FLOW-task-lifecycle#close-commit-ok"],
      "via": "lifecycle.target_entities"
    }
  ],
  "coupled_flows": [
    {"flow_id": "FLOW-subtask-lifecycle", "distance": 1, "shared_on": ["doc/tools/arch/task_ops.py", "ENT-task-record"]},
    {"flow_id": "FLOW-verify-task", "distance": 1, "shared_on": ["ENT-verification-evidence", "doc/tools/arch/acceptance.py"]}
  ],
  "unmapped_correlated_symbols": [
    {"symbol": "doc/tools/arch/task_ops.py#cmd_task_migrate", "lines": [1510, 1598]}
  ]
}
```

#### Б. Детерминированный AST-сканер сигналов кода — `arch docs flow inspect`

Команда `arch docs flow inspect <FLOW-ID | path.py[#symbol]> --json` разбирает стандартным модулем `ast` Python привязанные функции и сопоставляет фактические сигналы кода с текущим `*.flow.json`:

1. **Сверка кодов выхода и ошибок:** извлекает из AST вызовы `CliError(code=..., exit_code=...)`, `error_envelope(...)`, `ok_envelope(...)`, `EXIT_*` и сравнивает их со множеством `(outcome.exit_code, outcome.error_code)` в ветках флоу → выдаёт `undocumented_error_signals` с точными номерами строк!
2. **Сверка мутаций диска:** находит в AST вызовы записи/удаления (`atomic_write_json`, `write_text`, `mkdir`, `unlink`, `rmtree`, `rename`) и подсвечивает подозрительные записи на путях, объявленных `read_only` (`mutation_signals`).
3. **Точки ветвления и тесты-кандидаты:** возвращает диапазоны строк `lines: [start, end]` содержательных `if/elif/match`-развилок функции и список тестовых файлов из `doc/tests/*.py`, импортирующих или вызывающих данный символ (`candidate_tests`).

Пример вывода `arch docs flow inspect FLOW-create-task --json`:

```json
{
  "target": "FLOW-create-task",
  "correlated_flows": ["FLOW-task-lifecycle", "FLOW-subtask-lifecycle"],
  "inspected_symbols": [
    {
      "ref": "doc/tools/arch/task_ops.py#cmd_task_init",
      "lines": [142, 238],
      "declared_branches": [
        "FLOW-create-task#reject-invalid-task-key",
        "FLOW-create-task#reject-existing-task-or-registry-conflict",
        "FLOW-create-task#init-explicit-task-key"
      ],
      "undocumented_error_signals": [
        {
          "code": "REGISTRY_MISSING",
          "exit_code": 1,
          "path": "doc/tools/arch/task_ops.py",
          "line": 168,
          "snippet": "error_envelope('REGISTRY_MISSING', ...)"
        }
      ],
      "mutation_signals": [
        {"call": "atomic_write_json", "line": 214},
        {"call": "mkdir", "line": 199}
      ],
      "candidate_tests": ["doc/tests/test_task_identity.py"]
    }
  ],
  "unreferenced_public_symbols": []
}
```

### 12.3. Пятишаговый протокол и готовый эталонный макет скилла `doc/skills/flow-audit/SKILL.md`

По стандарту упаковки процедурных навыков из [Agent Skills (SKILL.md).md](data/cli-skills-encyclopedia/Форматы/Agent%20Skills%20%28SKILL.md%29.md) (`name` + точный триггер в `description`, объём `<500` строк, опора на CLI вместо ручного чтения монорепо) ниже зафиксирован готовый эталонный каркас нового скилла `doc/skills/flow-audit/SKILL.md` и строка роутера для `doc/AGENTS.md`.

**Строка для таблицы «Сначала выберите режим» в `doc/AGENTS.md`:**

```markdown
| Найти все флоу вокруг задачи/сущности, проверить их полноту по коду или достроить флоу | Прочитать [flow-audit](skills/flow-audit/SKILL.md). |
```

**Макет `doc/skills/flow-audit/SKILL.md`:**

```markdown
---
name: flow-audit
description: Find all architectural flows correlated with a task, entity, term, or module, audit their completeness against actual code via AST inspection, and complete or split *.flow.json models. Use when auditing flow coverage, investigating code-vs-flow drift, or bootstrapping missing flows.
metadata:
  status: draft
---

# Skill: flow-audit (расследование, аудит по коду и достраивание архитектурных флоу)

Для обычного быстрого чтения известного контракта без анализа исходников используйте [architecture-read](../architecture-read/SKILL.md). Настоящий навык применяется, когда нужно **найти все коррелирующие флоу вокруг задачи/сущности/модуля, сверить их с реальным кодом и достроить (либо расщепить) `*.flow.json` до полноты**.

## Порядок расследования (5 шагов)

1. **Соберите корреляционный контур через CLI (не читайте код вслепую):**
   - По задаче, сущности, термину или пути вызовите:
     `arch docs flow correlate (--task <KEY> | --entity <ENT-*> | --term <TERM-*> | --path <p>) --include-unmapped --json`
   - При общем аудите домена вызовите:
     `arch docs flow coverage [--domain <d>] --json`
2. **Снимите детерминированный AST-слепок по каждому целевому флоу/модулю:**
   - Вызовите `arch docs flow inspect <FLOW-ID | path.py[#symbol]> --json`.
   - Зафиксируйте `undocumented_error_signals`, `mutation_signals`, `unreferenced_public_symbols` и диапазоны строк `lines`.
3. **Прочитайте точечные диапазоны кода и разложите каждую находку на 4 корзины триажа:**
   - Откройте через `Read` **только указанные `lines`** и применимые правила `CAP-*` / `REG-*` / `ENT-*`.
   - Классифицируйте каждое расхождение:
     1. `missing_branch_in_flow` — код реализует законное доменное правило, пропущенное во флоу → **добавить фактор/ветку в `*.flow.json`**;
     2. `implementation_bug_or_gap` — контракт `CAP-*/REG-*` и флоу верны, а код ошибается или пропускает проверку → **НЕ подгонять флоу под баг!** Зафиксировать дефект (`finding`) или исправить код в рамках задачи;
     3. `incidental_plumbing` — техническая деталь форматирования/кэша/обёртки без доменного исхода → оставить в коде (при чистом хелпере предложить в `exempt_globs`);
     4. `ambiguous_intent` — из кода и контрактов неясно, задумка это или дефект → пометить `NEEDS CLARIFICATION` для владельца.
4. **Проверьте критерии нарезки границ перед записью:**
   - Убедитесь, что один флоу держит одну ведущую сущность домена, не склеивает состояния через внешнюю паузу и укладывается в бюджет `≤4` узлов `decisions[]` и `≤15` веток. При превышении — выделите подпоток через `next: {"kind": "flow", "target": "FLOW-..."}` и `superseded_branches`.
5. **Замкните детерминированную проверку CLI:**
   - Выполните `arch docs flow validate` → `arch docs flow build` → повторный `arch docs flow inspect <FLOW-ID>` → `arch docs flow check` и `arch docs check-links`.

## Жёсткие запреты
- Запрещено переписывать `*.flow.json` под обнаруженный баг кода в обход `CAP-*/REG-*`.
- Запрещено редактировать generated `flows/*.md` и `flows.index.json` вручную.
- Запрещено ставить `oracle_status: "verified"` без реального тестового файла в `refs.tests`.
```

### 12.4. Шесть критериев разделения (нарезки) флоу + дерево решений + разбор на живом `task_ops.py`

Чтобы все флоу проекта образовывали модульную сеть, а не один гигантский клубок на тысячи комбинаций, из [Флоу.md](data/machinedocs-encyclopedia/Документация/Флоу.md), [Семантический чанкинг.md](data/machinedocs-encyclopedia/Практики/Семантический%20чанкинг.md), [Иерархическая документация.md](data/machinedocs-encyclopedia/Архитектура/Иерархическая%20документация.md), [Следование архитектуре.md](data/machinedocs-encyclopedia/Документация/Следование%20архитектуре.md) (`REUSE_OR_PROMOTE` vs `KEEP_LOCAL`), DDD Bounded Contexts и OMG DMN DRD выводятся **6 операциональных правил нарезки**:

| № | Критерий границы | Когда это **один** `*.flow.json` | Когда **обязательно резать** на два разных `*.flow.json` (связав через `next.target: "FLOW-..."`) |
|---|---|---|---|
| **1** | **Граница домена и ведущей сущности (`Primary Entity / Bounded Context`)** | Все узлы управляют одним этапом жизненного цикла одной ведущей сущности в рамках одного домена (`domains/<domain>/`) | Сменяется домен-владелец **или** ведущая сущность (например, `ENT-task-record` в `FLOW-task-lifecycle` vs `ENT-verification-evidence` в `FLOW-verify-task` vs подзадача в `FLOW-subtask-lifecycle`) |
| **2** | **Точка покоя и смена триггера (`Quiescent State / Commit Boundary`)** | Шаги выполняются в рамках одной непрерывной транзакции/операции от вызова до коммита состояния на диск | Между частями процесса система **останавливается в устойчивом состоянии на диске** и ждёт нового внешнего вызова CLI, другого шага агента или решения человека (например, `FLOW-create-task` заканчивается в `scaffolded`, а дальше при новых вызовах работает `FLOW-task-lifecycle`) |
| **3** | **Ортогональность факторов (`Anti-Combinatorial Explosion`)** | Узел решения опирается на **2–4 совместно проверяемых фактора**; последовательные проверки *одного вызова* разделены на **2–4 каскадных узла `decisions[]`** внутри файла | Наборы входных факторов полностью не пересекаются, относятся к разным операциям/командам и при объединении раздувают файл свыше порогов бюджета |
| **4** | **Правило переиспользования (`PROMOTE vs KEEP_LOCAL`)** | Подпроцесс нужен ровно в одном месте и не вызывается снаружи (`KEEP_LOCAL` как узел `decision`) | Один и тот же подпроцесс со стабильным контрактом входа/выхода вызывается из **2 и более разных флоу** (`PROMOTE` в отдельный `FLOW-*` — например, `FLOW-verify-task` или `FLOW-docs-validation-and-indexing`) |
| **5** | **Нижний порог против «атомарной пыли» (`Minimum Viable Flow`)** | У процесса есть явный триггер, минимум **2 содержательные ветки исхода** (например, успех + предметный отказ) и наблюдаемый доменный результат | Чистая техническая функция без доменных развилок (парсер строки, запись файла по атомарному `tmp+rename`, форматирование JSON) — **не делается отдельным флоу**, остаётся деталью шага или в `exempt_globs` |
| **6** | **Количественные бюджеты размера (`Cognitive & Token Guardrails`)** | **1–4** узла `decisions[]`, **2–15** веток суммарно в файле, generated `<slug>.md` **до ~150 строк (`<15 КБ`)** | При превышении `>4` узлов `decisions[]`, `>15` веток или `>150` строк generated `.md` команда `arch docs flow validate` выдаёт предупреждение **`flow_split_recommended`** с указанием самого крупного узла-кандидата на отщепление |

#### Оперативное дерево решений агента: «Как оформить кусок логики?»

```text
Есть ли у кода собственные доменные развилки (≥2 осмысленных исхода) или смена состояния ENT-*?
├─ Нет (чистый парсинг, форматирование, I/O-обёртка, константы)
│  └─ НЕ создавать флоу → деталь внутри steps[] либо модуль в flow_coverage.exempt_globs.
└─ Да
   ├─ Меняется ли домен, ведущая сущность ENT-*, внешний триггер после точки покоя на диске,
   │  либо этот подпроцесс вызывается из ≥2 разных флоу (PROMOTE)?
   │  ├─ Да → ОТДЕЛЬНЫЙ файл <slug>.flow.json (связать с предшественником через next: {kind: "flow"}).
   │  └─ Нет (тот же запуск, та же сущность, один владелец)
   │     ├─ Проверяются ли те же самые 2–4 фактора, что и в существующем узле decision?
   │     │  ├─ Да → НОВАЯ ВЕТКА (branch) внутри существующего узла decision.
   │     │  └─ Нет (следующий последовательный шлюз того же вызова, например collect → gate)
   │     │     ├─ Укладывается ли файл в ≤4 узлов decisions[] и ≤15 веток?
   │     │     │  ├─ Да → КАСКАДНЫЙ УЗЕЛ decision внутри того же *.flow.json (next: {kind: "decision"}).
   │     │     │  └─ Нет (сработал порог flow_split_recommended) → ОТЩЕПИТЬ в дочерний *.flow.json.
```

#### Наглядный пример на реальном коде `sf`: почему `doc/tools/arch/task_ops.py` (1820 строк) нельзя описывать одним `FLOW-task-ops`

Один физический файл `doc/tools/arch/task_ops.py` содержит 1820 строк кода. Если бы мы наивно приравнивали «1 файл кода = 1 флоу», получился бы нечитаемый монстр `FLOW-task-ops` на ~40 веток и сотни ложных комбинаций факторов. Применение 6 правил режет один крупный модуль на **4 чистых, компактных и сцепленных между собой флоу** (при этом **каждый** ссылается на свои точные функции `task_ops.py#<func>` в `refs.code`!):
1. **`FLOW-create-task`** (`task-intake`, `cmd_task_new` / `cmd_task_init`) — отделён по **Критерию 1 и 2**: точка входа до появления задачи, завершается точкой покоя `scaffolded` и передаёт `next: {"kind": "flow", "target": "FLOW-task-lifecycle"}`.
2. **`FLOW-subtask-lifecycle`** (`task-lifecycle`, `cmd_task_decompose` / `cmd_subtask_*`) — отделён по **Критерию 1 и 3**: собственные ортогональные факторы графа детей (`subtask_policy`, ацикличность `depends_on`, готовность параллельной волны).
3. **`FLOW-verify-task`** (`execution-verification`, `cmd_task_evidence` + `acceptance.py`) — отделён по **Критерию 1 и 4 (`PROMOTE`)**: ведущая сущность `ENT-verification-evidence`, переиспользуется и для задач, и для подзадач.
4. **`FLOW-task-lifecycle`** (`task-lifecycle`, `status / workspace / diagnose / close / migrate`) — ядро переходов родительской карточки от `scaffolded` до `closed` с двухшаговым каскадом `diagnose-blockers (COLLECT) → close-gate (UNIQUE)` внутри одного файла.

### 12.5. Как разделённые флоу дополняют друг друга, обновляются при правке кода и расщепляются без поломки ссылок

Разделённые по этим 6 критериям флоу работают как **сцепленные модули единого графа**:
1. **Контракт сцепления («шип — паз» между флоу):**
   - `FLOW-A` заканчивает ветку явным постусловием, терминальным состоянием `transition.to` и ссылкой `next: {"kind": "flow", "target": "FLOW-B"}`;
   - `FLOW-B` фиксирует ожидаемое входное состояние в `lifecycle.initial_states` и `preconditions`, а в `flows.index.json#referenced_by.by_flow["FLOW-B"]` автоматически прописывается обратная ссылка на `FLOW-A#branch-id`.
2. **Три сценария обновления сети флоу при изменении кода:**
   - **Локальная правка внутри капсулы одного флоу (80–90% задач):** если код меняется внутри `FLOW-A`, а его выходные состояния и постусловия на границе с `FLOW-B` сохраняются — меняется **только `FLOW-A`** (никакого каскадного переписывания соседних документов!).
   - **Изменение межпотокового контракта на стыке:** если правка в `FLOW-A` меняет состояние/артефакт, который ждёт `FLOW-B` (или общую `ENT-*` / мутируемый файл), двухкольцевой радар `arch docs context --flows` **ещё на этапе планирования** выводит `FLOW-B` в кольцо `impacted`, а проверка `Inter-Flow Handshake` (§11.2) в `flow validate` не пропустит несогласованный стык.
   - **Органическое расщепление при росте продукта (`Flow Split` с сохранением обратной адресации через `superseded_branches`):** когда в результате нескольких фич один флоу перерастает порог `15` веток (`flow_split_recommended`), агент по скиллу `flow-audit` выделяет созревший подпроцесс в новый `<sub-slug>.flow.json`, ставит в родительской ветке `next: {"kind": "flow", "target": "FLOW-<sub-slug>"}`, а в родительском файле записывает блок `superseded_branches` (поддержанный в `arch-flow.schema.json` §6.3!):
     - все закрытые задачи и ADR со старым адресом `FLOW-parent#old-branch` остаются 100% валидными;
     - `arch docs read FLOW-parent#old-branch --json` автоматически возвращает переадресацию на `FLOW-<sub-slug>#new-branch` вместо ошибки `EXIT_NOT_FOUND`!

---

## 13. Сравнительный анализ технологий агентной разработки (2025–2026) и механика достижения глобальных целей `sf`

Четыре глобальные цели системы `sf` образуют **одновременную инженерную задачу с жёсткими ограничениями**:
1. **Масштаб большой кодовой базы (`100K–1M+ LOC` brownfield)** без потери межмодульной связности и без археологии репозитория на каждом тикете;
2. **Высокая надёжность даже на слабых, малых и открытых моделях (`7B–35B` локальных или бюджетных API-моделях)**, у которых узкое эффективное внимание, быстрая деградация на дистракторах и повышенный риск пропуска граничных веток или «взлома» тестов;
3. **Минимальный расход токенов на принятое изменение (`tokens-per-accepted-task`)** — радикально ниже `GitHub Spec Kit`, `OpenSpec`, `BMAD` и автономных поисковых агентов;
4. **Качество выше `OpenSpec`/`Spec Kit`/аналогов и риск багов, стремящийся к нулю (`escaped defect rate → 0`)**.

Ниже сведены результаты ресёрча по локальным базам `/home/user/sf/data/` и эмпирическим исследованиям 2024–2026 гг., объясняющие, почему существующие SDD-инструменты не закрывают все 4 цели одновременно и как именно связка `sf + *.flow.json (v2.0)` решает это противоречие.

---

### 13.1. Эмпирическая физика контекста и слабых моделей: 6 доказанных законов (2024–2026)

1. **Закон «Гниения контекста» (`Context Rot`) и дистракторов:**
   Исследование Chroma Research (*Hong, Troynikov, Huber, 2025 — «Context Rot: How Increasing Input Tokens Impacts LLM Performance»*) и фреймворк [Tokalator (`arXiv:2604.08290`, Apr 2026)](https://arxiv.org/html/2604.08290) на 18 LLM доказали, что точность моделей падает задолго до формального лимита окна контекста, причём **слабые/компактные модели деградируют кратно круче, когда во входе присутствуют правдоподобные дистракторы** (соседние сценарии того же домена, смежные функции, повторы правил). Классический эффект *Lost in the Middle* (U-образная кривая внимания, см. [08-контекст-инженерия-агентов.md](data/sdd-research/08-контекст-инженерия-агентов.md) и [Большие кодовые базы.md](data/machinedocs-encyclopedia/Практики/Большие%20кодовые%20базы.md)) приводит к тому, что слабая модель, получившая 15-страничный `spec.md`, выполняет начало и конец, но теряет инварианты отказов из середины.
2. **Парадокс статических контекстных файлов (`AGENTS.md` Cost Trap):**
   Масштабное эмпирическое исследование ETH Zurich SRI — *Gloaguen, Mündler, Müller, Raychev, Vechev* ([`arXiv:2602.11988v3`, Sep 2026, ICLR 2026 Workshop](https://arxiv.org/html/2602.11988v3), включая тесты на `Qwen3-30b-coder` и 438 задач SWE-bench/CTXbench) — установило: статические и особенно LLM-сгенерированные обзорные контекстные файлы **не повышают процент решённых задач (а автосгенерированные снижают его на ~3%), но статистически значимо увеличивают стоимость инференса на `+20%..+23%` и число шагов агента на `+2.45..+3.92`**. Напротив, работа *Lulla et al.* ([`arXiv:2601.20404`, Jan 2026](https://arxiv.org/abs/2601.20404)) показала, что **сверхкороткие операционные указатели на точные команды и пути** сокращают выходные токены на **`−16.58%`** и медианное время выполнения на **`−28.64%`**. Вывод: статические простыни вредны; работает только ультракороткий роутер + динамическая хирургическая выдача под конкретную задачу.
3. **Ловушка широкого обхода графа кода против 1-hop локализации:**
   В работе [RepoGraph (`arXiv:2410.14684`)](https://arxiv.org/html/2410.14684v1) показано, что компактная 1-hop выжимка графа кода (`717–2,310` токенов) поднимает точность `Agentless` до `29.67%`, но **расширение выдачи до плоского 2-hop графа (`10,505` токенов) роняет точность обратно до `26.00%`** из-за шума соседей! А свежий бенчмарк [LARGER (`arXiv:2605.16352`, May 2026)](https://arxiv.org/html/2605.16352) показал, что свободный агентский обход графа (`LocAgent`) сжигает **`711.5K–940.7K` токенов на одну задачу** (`$1.26–$1.67`), тогда как детерминированная иерархическая локализация [Agentless (`arXiv:2407.01489`)](https://ar5iv.labs.arxiv.org/html/2407.01489) укладывается в **`17.8K–26.3K` токенов** (`$0.03–$0.05` — **в 35 раз дешевле!**).
4. **Почему малые модели (`0.6B–32B`) проваливаются в свободном поиске, но побеждают в жёстком harness'е:**
   Предрегистрированное исследование на **`170,500` эпизодах** 9 открытых моделей (`Qwen3 0.6B–32B`, `Gemma 4 E2B–12B`) на 500 held-out задачах SWE-bench — *«How Much Do Structural Tools Help Small Coding Agents?»* ([`arXiv:2610.33958`, Oct 2026](https://arxiv.org/pdf/2610.33958)) — доказало, что малые модели (`4B–8B`) в режиме самостоятельной навигации упираются в лимит шагов (`step cap 14.3%–20.7%`) и теряются в сырых графовых тулах. Одновременно индустриальный разбор 2026 года ([Why Local LLMs Fail at Agentic Coding in 2026](https://capitalandcompute.net/blog/why-local-llms-fail-agentic-coding/)) показал, что **одни и те же веса открытой модели `Qwen3.6-27B` дают `67.8%` на SWE-bench Verified в базовом `mini-swe-agent`, `77.2%` во внутреннем скаффолде Qwen и до `87.4%–90.0%` в инженерном CLI-harness'е** — разброс **`+22.2 п.п.` исключительно за счёт архитектуры среды, декомпозиции и дисциплины контекста, без смены модели!**
5. **Двукратный перерасход токенов в тяжёлом Markdown-SDD (`Spec Kit` vs `OpenSpec`):**
   Прямой замер 2026 года ([Spec Driven Development Is Wasting Tokens](https://medium.com/it-chronicles/is-your-safe-choice-burning-your-budget-1cfddf8782e4)) зафиксировал: на идентичных задачах `GitHub Spec Kit` тратит **`120,947–181,040` токенов** против **`57,740–91,729` токенов** у `OpenSpec` (**перерасход `+97%..+109%`**, а на фазе планирования — **`+152%`**), причём `Spec Kit` потребовал дополнительных циклов исправления багов, так как многословная Markdown-конституция и 8 файлов артефактов зашумили контекст модели.
6. **Фундаментальный предел прозаических спек (*«AI can ignore your spec — it can’t ignore a failing gate»*):**
   Как показала Birgitta Böckeler из Thoughtworks ([Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl, MartinFowler.com](https://www.martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)), а также авторы фреймворка принудительного TDD [Consort (`arXiv:2609.09671v1`, Sep 2026)](https://arxiv.org/html/2609.09671v1) и [ATDD-разбора Optivem](https://journal.optivem.com/p/spec-driven-development-make-specs), во всех популярных SDD-инструментах первого поколения спека остаётся **неисполняемым Markdown-текстом**: агент регулярно игнорирует часть пунктов, пересоздаёт уже существующие классы или подгоняет тесты под баг, если его не держит **детерминированный вычислительный гейт и защищённая зона оракулов (`Trust Zone`)** (см. также [Предотвращение ошибок.md](data/cli-skills-encyclopedia/Практики/Предотвращение%20ошибок.md) и [Архитектура агентной software factory.md](data/machinedocs-encyclopedia/Практики/Архитектура%20агентной%20software%20factory.md)).

---

### 13.2. Сводная сравнительная матрица 9 подходов и технологий агентной разработки (2025–2026)

Оценка проведена строго по 4 глобальным целям `sf` на основе [03-инструменты-и-фреймворки.md](data/sdd-research/03-инструменты-и-фреймворки.md), [Готовые решения агентной software factory.md](data/machinedocs-encyclopedia/Практики/Готовые%20решения%20агентной%20software%20factory.md), [Codified Context (3 яруса).md](data/machinedocs-encyclopedia/Архитектура/Codified%20Context%20%283%20яруса%29.md) и внешних бенчмарков 2025–2026 гг.:

| Технология / подход | Уровень по Böckeler | Типичный расход токенов на задачу | Большая база (`100K–1M+ LOC`) | Работа на **слабых моделях (`14B–32B` / Haiku)** | Полнота ветвлений и инвариантов | Защита от тихих багов и взлома тестов |
|---|---|---|---|---|---|---|
| **1. Ad-hoc агент / автономный поиск (`SWE-agent`, `LocAgent`, чат без спек)** | Нет спек (`Code-only`) | **Высокий / взрывной:** `96K–940K` токенов на блуждание по репо ([`arXiv:2605.16352`](https://arxiv.org/html/2605.16352)) | Плохо: агент каждый раз заново делает археологию grep'ом; ~60% merge rate на фичах ([uvik.net](https://uvik.net/blog/spec-driven-development-benchmark/)) | **Слабо:** упираются в лимит шагов (`14–20%`, [`arXiv:2610.33958`](https://arxiv.org/pdf/2610.33958)), правят симптом, ломают соседей | `0%` — только то, что модель случайно заметила в прочитанном файле | Нет: модель свободно удаляет/меняет падающие `assert` |
| **2. GitHub Spec Kit** ([github/spec-kit](https://github.com/github/spec-kit), `133K★`) | `Spec-first` (папка на фичу) | **Очень высокий:** `120K–181K` токенов (`+109%` к OpenSpec, 8 `.md` файлов на фичу) | Слабо на brownfield: папки `specs/001..099` не сливаются в единую живую модель системы ([Discussion #152](https://github.com/github/spec-kit/discussions/152)) | **Плохо:** длинные промпты и конституции вызывают *Context Rot* и циклы самоисправлений | Ручные чек-листы в прозе; нет математической проверки дыр/коллизий | Гейты рекомендательные (`Advisory prose`, [`arXiv:2609.09671`](https://arxiv.org/html/2609.09671v1)) |
| **3. OpenSpec (`OPSX`)** ([Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec), `73K★`) | `Spec-anchored` (живые `.md` + дельты) | **Средний:** `57K–92K` токенов (читаются целые `<domain>/spec.md` + `proposal/design/tasks`) | Хорошо для средних баз, но нет графа междоменных потоков, сущностей и AST-символов кода | **Средне:** меньше шума, чем в Spec Kit (`84%` merge rate на frontier LLM), но на слабых моделях Gherkin-проза допускает ложные самоаттестации | Проверяет заголовки Markdown (`### Requirement`), **не проверяет полноту комбинаций входов** | `/opsx:verify` — неблокирующая LLM-оценка; нет привязки сценария к тесту и коду |
| **4. AWS Kiro** ([kiro.dev](https://kiro.dev/docs/specs/)) | `Spec-first` / `Spec-anchored` в IDE | **Средний–высокий:** EARS + `design.md` + `tasks.md` (`$2.35/тикет`, эффект «кувалды на мелком баге») | Средне: `.kiro/steering/` даёт общий контекст, но спеки изолированы по фичам, жёсткий IDE lock-in | **Средне:** EARS структурирует условия лучше свободной прозы, но весь дизайн грузится целиком | Analyze Requirements ищет противоречия LLM-ом, а не детерминированным решателем | IDE hooks запускают тесты, но не защищают от ослабления оракула и пропущенных веток |
| **5. BMAD Method / Ролевые мультиагентные цепочки** ([BMAD.md](data/sdd-encyclopedia/Инструменты/BMAD.md)) | Многоролевой `Spec-first` (`PM → Arch → Dev → QA`) | **Экстремальный:** `150K–400K+` токенов (передача PRD, эпиков и стори между 4–6 персонами) | Плохо для точечных правок brownfield: огромная церемония ради изменения 20 строк кода | **Плохо:** эффект «испорченного телефона» при передаче прозы между слабыми субагентами | Зависит от промпта аналитика/архитектора, формального контроля нет | Процессные handoff'ы без формального инварианта атомарности и трассировки символов |
| **6. Tessl (`Spec-as-Source`)** | `Spec-as-source` (код генерируется из спеки) | Высокий при перегенерации модулей | **Неприменимо к большим brownfield-базам:** пометка `DO NOT EDIT` несовместима с хирургическими патчами и legacy | **Плохо:** слабая модель как «недетерминированный компилятор» выдаёт разный код при повторных прогонах ([MartinFowler.com](https://www.martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)) | Нет формальной модели состояний и побочных эффектов | Высокий риск регрессий при полной регенерации файла |
| **7. Чистые Code-Graph / RepoMap (`Agentless`, `RepoGraph`, `Aider`, `SCIP`)** | Без бизнес-спек (`AST/Graph-only`) | **Низкий:** `18K–47K` токенов полный цикл; срез графа `0.7K–2.3K` ([`arXiv:2410.14684`](https://arxiv.org/html/2410.14684v1)) | **Отлично по структуре вызовов**, но граф кода **не знает бизнес-замысла (`WHY`) и запретных состояний** | **Хорошо на локализации**, если срез строит harness (а не сама модель!), но модель слепа к недокументированным инвариантам | `0%` проверки доменных правил — существующий баг в коде воспринимается как норма | Опирается только на уже существующие регрессионные тесты |
| **8. Codified Context + Enforced TDD (`arXiv:2602.20478` + `Consort arXiv:2609.09671`)** | Трёхъярусная память + неизменяемые тесты | **Ниже среднего:** `25K–60K` токенов (холодные спеки подгружаются по MCP) | **Хорошо** (проверено на `108K LOC` C#, 283 сессии), но холодные спеки остаются текстовыми (~500 строк на документ) | **Выше среднего** за счёт жёсткого TDD-цикла и неизменяемых тестов, но чтение целой подсистемной спеки перегружает малые модели | Высокая для покрытых TDD-кейсов, но нет табличной проверки `0 gaps / 0 overlaps` до написания тестов | **Сильная:** тесты в отдельной Trust Zone (`Tests immutable`) |
| **9. Целевая система `sf` + `*.flow.json` (`v2.0`)** | **Executable Graph-Anchored SDD** (JSON-канон + дельты веток + AST/Test связь) | **Минимальный целевой:** **`3K–8K` входного контекста в капсуле** (`12K–28K` полный цикл задачи — **в 3–5× меньше OpenSpec и в 6–10× меньше Spec Kit**) | **Отлично:** `flows.index.json` + двухкольцевой радар `participating / impacted` + `--ratchet` онбординг без чтения монорепо | **Спроектировано специально под слабые модели:** модель получает готовую капсулу `1` ветки без дистракторов и работает в жёстком коридоре CLI-гейтов | **100% математическая проверка** DMN-таблиц (`0 gaps`, `0 overlaps`, `no masked`), графа `lifecycle` и межфлоу-стыков | **Максимальная (7 эшелонов):** AST-сверка `flow inspect`, `Red-before-Green`, `--assert-guard`, байтовая проверка `atomicity` |

---

### 13.3. Детальный разбор сильных и слабых сторон конкурирующих подходов — и честная оценка уязвимостей нашего подхода

#### Почему комбинация лучших идей побеждает любой одиночный инструмент
- **У `OpenSpec`** мы взяли лучшую идею для brownfield — разделение **живого канона** и **изолированной дельты задачи (`stageN/flow-delta.json`)**, но заменили хрупкий Markdown-блок `MODIFIED` (затирающий правки параллельных веток и не имеющий формальной семантики) на **адресацию конкретной ветки `FLOW-ID#branch-id` с проверкой `base_sha256` и решателем матриц решений**.
- **У `Kiro` и `EARS`** мы взяли дисциплину `entry_states (WHILE) + when (WHEN/IF) + outcome (SHALL)`, но перевели её из свободного текста в конечные перечислимые домены `factors[]`, доступные для комбинаторной верификации за миллисекунды.
- **У `Agentless` (`arXiv:2407.01489`) и `RepoGraph` (`arXiv:2410.14684`)** мы взяли детерминированную пред-локализацию кода до строк `lines: [start, end]` и строгий запрет на 2-hop «простыню» дистракторов, скрестив структурный граф кода (`refs.code`) с графом архитектурного смысла (`ENT-*`, `CAP-*`, `TERM-*`).
- **У `Consort` (`arXiv:2609.09671`) и [Архитектура агентной software factory.md](data/machinedocs-encyclopedia/Практики/Архитектура%20агентной%20software%20factory.md)** мы взяли принцип **неизменяемой Trust Zone оракулов (`--assert-guard`)**, не позволяющий слабой модели «починить» падение удалением `assert`.

#### Честный разбор слабых сторон самого подхода `*.flow.json` и как они нейтрализованы в `v2.0`

| Потенциальная слабость `*.flow.json` | Когда она проявляется | Как нейтрализована в архитектуре `flowjson.md` (`v2.0`) |
|---|---|---|
| **1. Высокий порог первичной разметки (`Cold-Start Tax`) на огромном legacy-репозитории** | Если потребовать 100% покрытия `500K LOC` до первой продуктовой задачи — работа встанет на месяцы | Введён режим **`arch docs flow coverage --ratchet --since <base>`** (§7.4, §14.2): обязательное покрытие требуется **только для затронутых задачей модулей** (`Touch-to-Codify`), а черновики создаются за минуты через `flow inspect` + скилл `flow-audit` |
| **2. Иллюзия безопасности при формально зелёной JSON-схеме и пустом тесте** | Слабая модель может прописать `oracle_status: "verified"` и ссылку на файл теста, где написано `assert True` | Узловой селектор `path.py::Class::test_fn` + `flow verify --assert-guard --atomicity-check` + проверка `Red-before-Green` на `baseline` (§13.5, §14.3 `GAP-SYS-03`) |
| **3. Хрупкость синтаксиса строгого JSON для слабых моделей** | Модели `7B–14B` при ручной генерации большого JSON на 300 строк иногда ошибаются в скобках или типах | Слабая модель-исполнитель в `80–90%` задач **вообще не редактирует весь `*.flow.json`**, а либо не меняет контракт (`unchanged_contract`), либо подаёт маленький `flow-delta.json` на 15–25 строк в `flow delta apply` с мгновенной самокоррекцией по `CliEnvelope.suggestion` |
| **4. Избыточная детализация тривиального кода («атомарная пыль»)** | Попытка описать через `*.flow.json` чистые парсеры, DTO и утилиты форматирования | Жёсткий порог `Minimum Viable Flow` (§12.4, Критерий 5) + белый список `flow_coverage.exempt_globs` в `paths.yaml` |

---

### 13.4. Токен-экономика: за счёт чего `sf + *.flow.json` расходует в 5–10× меньше токенов и не деградирует на слабых моделях

Главная причина перерасхода токенов в обычных агентных средах — **квадратичный налог многоходовой разведки** ($\sum_{t=1}^{T} C_t$, где каждый лишний ход `grep/read` повторно оплачивает всю накопленную историю сессии). Чтобы слабая модель решала задачу в минимальном окне без археологии, в `v2.0` вводится **Одновызовная капсула исполнения (`Zero-Archaeology Execution Capsule`)** — `arch docs flow capsule --task <KEY> --mode execute --json`:

```json
{
  "task_key": "UI-0035",
  "mode": "execute",
  "token_estimate": 2480,
  "target_branches": [
    {
      "ref": "FLOW-create-task#reject-invalid-task-key",
      "when": {"ambiguity": "none", "key_mode": "explicit_invalid", "collision": "*"},
      "invariants": [
        "При любой ошибке валидации не остаётся каталога doc/tasks/<task_key>/",
        "Файл task.md никогда не создаётся"
      ],
      "effects": {"mutates": [], "atomicity": "read_only"},
      "outcome": {
        "kind": "error",
        "exit_code": 2,
        "error_code": "INVALID_TASK_KEY",
        "postconditions": ["state_unchanged_on_disk == true"]
      }
    }
  ],
  "code_slices": [
    {
      "ref": "doc/tools/arch/validation.py#parse_task_key",
      "lines": [48, 96],
      "ast_error_signals": ["INVALID_TASK_KEY"]
    }
  ],
  "impacted_ring_summary": [
    "FLOW-subtask-lifecycle#validate-parent-key (shares validation.py#parse_task_key — keep signature & exit_code=2)"
  ],
  "verification_commands": [
    "arch docs flow verify FLOW-create-task#reject-invalid-task-key --assert-guard --atomicity-check"
  ],
  "trust_zone_protected": [
    "doc/architecture/domains/task-intake/flows/create-task.flow.json",
    "doc/config/paths.yaml"
  ]
}
```

#### Сравнение послойного бюджета входного контекста на одну типовую задачу доработки в большой базе (`100K+ LOC`)

| Слой контекста | `GitHub Spec Kit` | `OpenSpec` | Автономный `SWE-agent` | **`sf` + `flow capsule` (`v2.0`)** |
|---|---|---|---|---|
| Постоянные инструкции (`AGENTS.md` + роутер) | `3,500–8,000` ток. (`constitution.md` + шаблоны) | `1,500–3,000` ток. | `1,500–4,000` ток. | **`~650–900` ток.** (`doc/AGENTS.md` = 61 строка) |
| Процедурный скилл задачи | `6,000–15,000` ток. (серия slash-промптов) | `3,000–6,000` ток. | `2,000` ток. | **`1,200–1,800` ток.** (сжатый `SKILL.md` без воды) |
| Спецификация / архитектура задачи | `18,000–45,000` ток. (8 `.md` файлов фичи) | `8,000–20,000` ток. (весь `<domain>/spec.md` + `proposal/design`) | `0` (слепой поиск по коду) | **`600–1,500` ток.** (только нужная ветка `FLOW#branch` + 1-строчный `impacted`) |
| Чтение исходного кода и поиск локации | `30,000–60,000` ток. | `25,000–45,000` ток. | `60,000–200,000+` ток. (десятки `grep`/`read`) | **`1,000–3,000` ток.** (точный AST-диапазон `lines` из `code_slices`) |
| **Суммарный кумулятивный расход за задачу** | **`120,000–181,000` ток.** | **`57,000–92,000` ток.** | **`96,000–245,000+` ток.** | **`12,000–28,000` ток. (экономия в `3–5×` к OpenSpec и в `6–10×` к Spec Kit)** |

---

### 13.5. Конвейер «Риск багов → 0» на слабых моделях: 7 детерминированных эшелонов + ролевой роутинг

По принципу [Модели и стоимость.md](data/subagents-encyclopedia/Паттерны/Модели%20и%20стоимость.md) (*«Дорогой мозг, Дешёвые руки»*) и [Предотвращение ошибок.md](data/cli-skills-encyclopedia/Практики/Предотвращение%20ошибок.md) система **не требует от слабой модели архитектурного воображения**:
- **Сильная модель (или владелец)** работает редко и коротко — только когда меняется сам контракт (`plan-task` уровня `standard/full`, триаж `ambiguous_intent` в `flow-audit`, проектирование `flow-delta.json` на `20` строк);
- **Слабая/дешёвая/локальная модель (`Qwen3.6-27B`, `Qwen3-30B-A3B`, `Devstral-24B`, `Haiku`, `GPT-4.1-mini`)** выполняет `80–90%` объёма кодинга, рефакторинга и написания тестов внутри **7 жёстких механических барьеров**, через которые баг физически не может просочиться незамеченным:

1. **Эшелон 1 — Комбинаторная полнота до первой строчки кода (`flow validate`):** решатель DMN проверяет `0 gaps / 0 overlaps / no masked branch`. Невозможно «забыть описать ветку отказа при конфликте реестра».
2. **Эшелон 2 — Отсутствие дистракторов во входе (`flow capsule`):** слабая модель видит ровно свою ветку, свои `50–150` строк кода и 1-строчное предупреждение о соседях (`impacted_ring_summary`), поэтому не путает правила соседних команд.
3. **Эшелон 3 — Доказательство различающей силы теста (`Red-before-Green Baseline`):** перед изменением кода целевой тест новой/исправляемой ветки обязан **упасть на базовом коммите (`baseline exit != 0`) и пройти после патча (`exit == 0`)** — это математически исключает пустые тесты вида `assert True`.
4. **Эшелон 4 — Защита Trust Zone от подгонки оракулов (`flow verify --assert-guard`):** если модель-исполнитель без полномочий в `task.json` изменила `*.flow.json`, `paths.yaml` или удалила/ослабила существующие `assert*` в тестовом AST — гейт мгновенно завершается с `EXIT_AUTH (10)`.
5. **Эшелон 5 — Автоматическая побайтовая проверка атомарности отказов (`--atomicity-check`):** для всех веток с `atomicity: "read_only"` или `state_unchanged_on_disk: true` проверочный раннер сравнивает хеш-дерево временной фикстуры до и после вызова — любой забытый `.tmp`-файл или частичная запись ловится автоматически.
6. **Эшелон 6 — AST-контроль побочных сигналов после правки (`flow inspect`):** если слабая модель добавила в код новый `CliError` / `http_status` или запись на диск, не объявленные в ветке `*.flow.json`, `flow inspect` выдаёт точный номер строки расхождения.
7. **Эшелон 7 — Предохранитель зацикливания (`Circuit Breaker` + Fresh-Context Review):** если слабая модель дважды подряд не проходит `flow verify` на одной ошибке, цикл авто-ремонта принудительно останавливается (см. [Архитектура агентной software factory.md](data/machinedocs-encyclopedia/Практики/Архитектура%20агентной%20software%20factory.md)) и передаёт компактный пакет контрпримера независимому ревьюеру в чистом контексте ([review-implementation/SKILL.md](doc/skills/review-implementation/SKILL.md)).

---

## 14. Итоговый сквозной аудит `flowjson.md` и всей системы `sf`: пробелы, риски и детальный план доработок (`GAP-FLOW-01..05`, `GAP-SYS-01..07`)

Ниже зафиксирован честный инженерный аудит: **(А)** какие пробелы имела версия `flowjson.md` (`v1.2`) относительно четырёх глобальных целей и как они закрыты в текущей редакции `v2.0`; **(Б)** какие **конкретные файлы, модули и контракты самой системы `sf` (`/home/user/sf/doc/`)** сейчас содержат узкие места, мешающие работе слабых моделей, экономии токенов и масштабированию на большие кодовые базы, и требуют плановой доработки.

### 14.1. Сводная матрица готовности к 4 глобальным целям

| Глобальная цель системы | Текущий `sf` (`f8cb406` без `flow.json`) | `flowjson.md` (`v1.2`) | **`flowjson.md` (`v2.0`) + доработки Контура Б** |
|---|---|---|---|
| **1. Большая кодовая база (`100K–1M+ LOC`)** | **Частично (4/10):** есть `index.json` для `.md`, но нет графа процессов, символов кода, шардирования и brownfield ratchet | **Хорошо (7.5/10):** граф `flows.index.json` и `correlate/inspect`, но Python-центрично и без `--ratchet` | **Целевой максимум (9.5/10):** полиглот-адаптеры `AST/tree-sitter/LSP`, `mutates_db/emits_events/http_status`, инкрементальный кэш и `--ratchet` |
| **2. Надёжность на слабых моделях (`14B–32B` / fast API)** | **Низко (3.5/10):** тяжёлые прозаические `SKILL.md` (до `20.6 КБ`), многошаговый ручной сбор контекста, `CAP-role-model-routing` не реализован | **Средне (6.5/10):** точечное чтение ветки есть, но нет единой капсулы и защиты от взлома `assert` | **Целевой максимум (9.5/10):** одновызовная `flow capsule` без дистракторов + сжатые скиллы + ролевой роутинг + `Circuit Breaker` |
| **3. Минимальный расход токенов** | **Средне (5.5/10):** короткий `doc/AGENTS.md` (`61` строка), но раздутый `go-to-task` и медленный прогон полных тест-файлов | **Хорошо (8/10):** двухкольцевой радар 1–3 КБ, но стартовый ритуал требует серии отдельных вызовов CLI | **Целевой максимум (9.5/10):** `1` вызов `flow capsule` (`1.5K–4.5K` ток.) + узловые селекторы `test.py::case` |
| **4. Риск багов → 0 (выше OpenSpec / Spec Kit)** | **Средне (5/10):** есть `evidence` с SHA-256 файлов, но CLI слеп к смыслу оракулов (`assert True`), полноте ветвлений и дрейфу кода | **Высоко (8/10):** DMN `0 gaps/0 overlaps` + `lifecycle` + AST `inspect`, но без блокировки правки тестов | **Целевой максимум (9.5/10):** 7 детерминированных эшелонов (`Red-before-Green` + `--assert-guard` + `--atomicity-check`) |

---

### 14.2. Контур А: Пробелы самой спецификации `flowjson.md` (`v1.2`), выявленные аудитом и закрытые в `v2.0`

| ID пробела | В чём состоял пробел в `v1.2` и почему он мешал целям | Как закрыто в спецификации `v2.0` (разделы) |
|---|---|---|
| **`GAP-FLOW-01`** | **Отсутствие одновызовного сборщика микро-контекста для слабых моделей:** агенту приходилось делать 5–7 последовательных вызовов (`context`, `read`, `inspect`, `Read` файла), накапливая квадратичный налог истории и рискуя сбиться на малых моделях ([`arXiv:2610.33958`](https://arxiv.org/pdf/2610.33958)). | Введена команда **`arch docs flow capsule`** (§7.4, §13.4), собирающая за 1 вызов JSON-капсулу ветки, AST-срез строк кода, 1-строчный `impacted`, селектор теста и список защищённых путей Trust Zone в рамках `--budget-tokens`. |
| **`GAP-FLOW-02`** | **Уязвимость к «взлому оракула» (`Reward Hacking`) и файловая грубость `refs.tests`:** слабая модель могла удалить падающий `assert` в тесте, а указание целого файла `test_task_identity.py` заставляло гонять десятки тяжёлых тестов. | В §6.3 и §7.2 стандартизованы **узловые селекторы** `path.py[::Class[::test_fn]]`, а в §7.4 и §13.5 добавлена команда **`arch docs flow verify --assert-guard --atomicity-check`**. |
| **`GAP-FLOW-03`** | **Узкая CLI-ориентация полей `effects` и `outcome`:** в `v1.2` были только файловые `mutates` и `exit_code`, чего недостаточно для больших продуктовых кодовых баз с БД, очередями, микросервисами и HTTP/gRPC API. | В `arch-flow.schema.json` (§6.3) добавлены опциональные поля `effects.mutates_db`, `effects.emits_events`, `effects.external_calls`, `effects.idempotency_key` и `outcome.http_status`. |
| **`GAP-FLOW-04`** | **Привязка `flow inspect` только к Python `ast` и отсутствие масштабирования индекса на `1000+` флоу:** на большом полиглот-монорепозитории (TS/Go/Rust/Java/C#) один плоский индекс без инкрементального кэша замедлит проверки. | В §7.2 и §14.3 заложен контракт плагинного **`LanguageAdapter`** (`Python ast` из коробки + `tree-sitter` / SCIP-LSP для продуктовых языков) и инкрементальная пересборка `flows.index.json` по SHA-256 доменных шардов. |
| **`GAP-FLOW-05`** | **Паралич холодного старта (`Cold-Start Bottleneck`) при внедрении на большой существующий продукт:** режим `--strict` на всём репозитории заблокировал бы разработку на `300K LOC` до описания сотен флоу. | В `arch docs flow coverage` (§7.4, §13.3) добавлен режим **`--ratchet --since <rev>`** (*Progressive Brownfield Ratchet / Touch-to-Codify*): гейт требует покрытия только для изменённых в задаче модулей и критичных контуров. |

---

### 14.3. Контур Б: Детальная карта мест в системе `sf` (`/home/user/sf/doc/`), требующих доработки (Backlog выхода на глобальные цели)

Аудит живого дерева `/home/user/sf/doc/` показал **7 системных узких мест за пределами самой схемы `UI-0029`**, без устранения которых слабые модели будут терять качество или перерасходовать токены:

| ID и приоритет | Точное место в репозитории `sf` | Диагноз проблемы (почему бьёт по слабым моделям / токенам / качеству) | Конкретное требование к доработке |
|---|---|---|---|
| **`GAP-SYS-01`** *(P0 — Токены и слабые модели)* | [doc/skills/go-to-task/SKILL.md](doc/skills/go-to-task/SKILL.md) (`20,630` байт ≈ `5,200+` токенов плотной прозы) и [doc/skills/plan-task/SKILL.md](doc/skills/plan-task/SKILL.md) (`11,310` байт) | Тело `go-to-task/SKILL.md` написано длинными многосоставными абзацами и нарушает канон [Токен-эффективность.md](data/cli-skills-encyclopedia/Практики/Токен-эффективность.md) (*«Bullets, not paragraphs; Examples → references/»*). Слабая модель теряет правила середины файла (*Lost in the Middle*) и платит `5K+` токенов на старте каждой задачи. | Разрезать `go-to-task/SKILL.md` на **императивный чек-лист `<120` строк (`~1,200` ток.)** + вынести справочные блоки в `doc/skills/go-to-task/references/` (`fixture-oracles.md`, `status-vs-phase.md`, `release-branches.md`, `contract-sync.md`). Первым шагом исполнения сделать вызов `arch docs flow capsule --task <KEY>`. |
| **`GAP-SYS-02`** *(P0 — Слабые модели и стоимость)* | [doc/architecture/domains/model-routing/capabilities/role-model-routing.md](doc/architecture/domains/model-routing/capabilities/role-model-routing.md) (`implemented: false`), [doc/config/agent-policy.yaml](doc/config/agent-policy.yaml), `doc/config/task-conf/types/*/config.yaml` (`OPEN-MODELS` в [constraints-risks.md](doc/architecture/system/constraints-risks.md)) | Ролевой роутинг моделей задекларирован как черновик и не реализован (`0` кода в `doc/tools/arch/`). В `task-conf` нет разделения шагов для сильного планировщика/аудитора и слабого дешёвого исполнителя, нет лимита попыток ремонта (`max_repair_attempts`) и бюджетов токенов на шаг. | Реализовать профили ролей в `agent-policy.yaml` и шагах `task-conf`: `architect/planner` (проектирование `plan.md` и `flow-delta.json`), `fast-executor` (слабая/локальная модель, работающая строго по `flow capsule` с `temperature: 0.1` и `max_repair_attempts: 2`), `fresh-reviewer` (независимая проверка контрпримерами в чистом окне). |
| **`GAP-SYS-03`** *(P0 — Риск багов → 0)* | [doc/tools/arch/acceptance.py](doc/tools/arch/acceptance.py), `doc/tools/arch/evidence.py` и оговорка в `go-to-task/SKILL.md` (*«Смысл оракулов CLI не оценивает»*, `OPEN-ORACLE`) | Сейчас `arch task evidence` проверяет только `exit_code == 0` и совпадение SHA-256 снимка. Если слабая модель написала тест без содержательного `assert`, замокала проверяемую функцию или удалила старый `assert` — CLI примет `evidence` как валидный! | Доработать `acceptance.py` / `evidence.py` и связать с `flow verify`: **(1)** обязательный `Red-before-Green` чек против `arch task baseline` для `bugfix`/`feature`; **(2)** AST-проверка diff'а тестов на неуменьшение числа/силы `assert*` и отсутствие новых `@skip`/`xfail` без разрешения владельца; **(3)** авто-проверка неизменности байтового дерева на ветках `read_only` / `state_unchanged_on_disk`. |
| **`GAP-SYS-04`** *(P1 — Скорость и выживаемость цикла)* | [doc/tests/test_task_identity.py](doc/tests/test_task_identity.py) (~96 запусков подпроцессов CLI/wheel) и `doc/tests/run.sh` | Холодный запуск каждого подпроцесса Python CLI стоит `~0.6–0.8 с`, из-за чего прогон тестового модуля упирается в таймауты `>30–60 с`. На слабых моделях долгий фидбэк провоцирует пропуск промежуточных проверок и рост числа ошибок. | Перевести внутренний цикл разработки на **in-process вызов точки входа `main(argv)`** (ускорение в `15–30×`, `<1.5 с` на пакет) + запускать на итерациях только точечные селекторы из `flows.index.json#by_code → refs.tests`, оставив тяжёлый subprocess/wheel прогон `run.sh --gate` один раз перед закрытием задачи. |
| **`GAP-SYS-05`** *(P1 — Большие продуктовые базы `100K–1M+ LOC`)* | [doc/config/paths.yaml](doc/config/paths.yaml), `doc/tools/arch/doc_ops.py` и открытые ограничения `OPEN-REPO`, `OPEN-FUTURE-SCANNER` в [constraints-risks.md](doc/architecture/system/constraints-risks.md) | Текущий `arch-cli` жёстко предполагает один локальный корень и анализирует только Python. При подключении `sf` к большому внешнему продуктовому монорепозиторию (например, `500K LOC` TypeScript + Go + Python + SQL) понадобятся мультирепо/таргет-пути и быстрый синтаксический индекс символов. | Ввести в `paths.yaml` явный блок `target_repositories[]` (отделяющий control-plane фабрики `doc/` от целевого репозитория продукта) и абстракцию `LanguageAdapter` в `arch_flows.py`: встроенный `PythonAstAdapter` + опциональный `TreeSitterAdapter` / `LspScipAdapter` (паттерн *Two-Layer Code Index* из [Навигация по коду.md](data/machinedocs-encyclopedia/Практики/Навигация%20по%20коду.md)). |
| **`GAP-SYS-06`** *(P1 — Контракт задачи и параллелизм)* | [doc/tools/arch/validation.py](doc/tools/arch/validation.py) (`validate_task_json`), `OPEN-TASK-SCHEMA`, `OPEN-RELEASE`, `OPEN-SANDBOX` в [constraints-risks.md](doc/architecture/system/constraints-risks.md) | Схема `task.json` ещё в статусе `draft`; поле `related_docs` принимает только `TASK_KEY_RE` (из-за чего агенты путают его со ссылками на документы); нет формального поля `trust_zone_overrides` (разрешено ли задаче менять `*.flow.json` и существующие тесты) и `max_tokens_budget`. | Зафиксировать стабильную JSON Schema `task.json` v1.0: добавить типизированное поле `flow_refs`, булев флаг полномочий `allow_contract_or_test_mutation` (по умолчанию `false` для защиты Trust Zone!) и переименовать/алиасировать `related_docs` → `related_tasks` с обратной совместимостью при миграции. |
| **`GAP-SYS-07`** *(P1 — Измеримое доказательство превосходства)* | [doc/architecture/system/quality.md](doc/architecture/system/quality.md) (*«Количественные SLO или эмпирические доказательства не установлены»*) | Без воспроизводимого локального бенчмарка невозможно численно контролировать, что обновление промпта, скилла или схемы действительно снизило токены и дефекты на слабых моделях (см. [Evals и метрики агентной разработки.md](data/machinedocs-encyclopedia/Практики/Evals%20и%20метрики%20агентной%20разработки.md)). | Создать локальный набор `doc/tests/evals/` из **15–20 эталонных задач на реальных коммитах самой `sf`** с hidden-оракулами и автоматическим замером 4 целевых SLO: **(1)** `input_tokens_per_accepted_task < 25K`, **(2)** `escaped_bug_rate == 0%` на скрытых негативных тестах, **(3)** `first_pass_gate_rate >= 85%` на моделях класса `24B–32B` / `Haiku`, **(4)** `0` нарушений Trust Zone. |

---

## 15. Сводный реестр стандартов, материалов `data/` и внешних исследований SDD (2024–2026)

Все архитектурные решения и выводы аудита настоящего документа напрямую трассируются к локальной базе знаний `/home/user/sf/data/`, живому коду `/home/user/sf/doc/` и рецензируемым внешним исследованиям/стандартам 2024–2026 гг.

### 15.1. Локальные энциклопедии и исследования проекта (`/home/user/sf/data/` и `doc/`)

| Источник в репозитории | Ключевой принцип / стандарт | Где именно реализован в нашей спецификации `flowjson.md` |
|---|---|---|
| [data/machinedocs-encyclopedia/Документация/Флоу.md](data/machinedocs-encyclopedia/Документация/Флоу.md) | Каркас **АШОСС** (Акторы, Шаги, Ошибки, Состояния, `Not Included`), бюджет чтения `<150` строк на витрину, запрет описывать только happy-path | Слои `actors`, `steps`, `outcome` (`error/blocked`), `lifecycle`, `not_included` (§6.2–6.3); проверка `happy_path_only_warning` (§11.1) и бюджет размера (§12.4) |
| [data/machinedocs-encyclopedia/Практики/Большие кодовые базы.md](data/machinedocs-encyclopedia/Практики/Большие%20кодовые%20базы.md), [Навигация по коду.md](data/machinedocs-encyclopedia/Практики/Навигация%20по%20коду.md) & [Codified Context (3 яруса).md](data/machinedocs-encyclopedia/Архитектура/Codified%20Context%20%283%20яруса%29.md) | Трёхъярусная память (Hot роутер + доменные скиллы + Cold спецификации), `Two-Layer Code Index` (`tree-sitter` + семантика), квоты токенов | Двухкольцевой индекс `flows.index.json`, одновызовная `flow capsule`, плагинный `LanguageAdapter` и `--ratchet` онбординг больших баз (§7.3–7.4, §13.4, §14.2–14.3) |
| [data/cli-skills-encyclopedia/Практики/Токен-эффективность.md](data/cli-skills-encyclopedia/Практики/Токен-эффективность.md), [Предотвращение ошибок.md](data/cli-skills-encyclopedia/Практики/Предотвращение%20ошибок.md) & [Модели и стоимость.md](data/subagents-encyclopedia/Паттерны/Модели%20и%20стоимость.md) | Оптимизация `tokens-per-task`, бюджеты `<1500` / `<5000` ток., *«Дорогой мозг, Дешёвые руки»*, детерминированные гейты вместо уговоров в прозе | Экономика токенов в `5–10×` лучше OpenSpec/Spec Kit, 7 эшелонов защиты слабых моделей и требования `GAP-SYS-01..03` (§13.4–13.5, §14.3) |
| [data/machinedocs-encyclopedia/Практики/Архитектура агентной software factory.md](data/machinedocs-encyclopedia/Практики/Архитектура%20агентной%20software%20factory.md), [Готовые решения агентной software factory.md](data/machinedocs-encyclopedia/Практики/Готовые%20решения%20агентной%20software%20factory.md) & [Harness-инжиниринг.md](data/machinedocs-encyclopedia/Практики/Harness-инжиниринг.md) | Изоляция тестов и гейтов в отдельной `Trust Zone`, `Audit-first / Repair-second`, `Circuit Breaker` при повторе сбоя, отделение control plane от runtime | Защита `--assert-guard` и `trust_zone_protected` в `flow verify` / `flow capsule`, лимит попыток ремонта слабой модели и сравнение платформ (§13.2, §13.5, §14.3) |
| [data/machinedocs-encyclopedia/Практики/Evals и метрики агентной разработки.md](data/machinedocs-encyclopedia/Практики/Evals%20и%20метрики%20агентной%20разработки.md) & [doc/architecture/system/quality.md](doc/architecture/system/quality.md) | Измерение `cost per accepted change`, защита от `metric gaming` (ослабление `assert`), hidden-оракулы и 3 контура evals | Спецификация локального eval-бенчмарка `doc/tests/evals/` и целевых SLO в `GAP-SYS-07` (§14.3) |
| [data/machinedocs-encyclopedia/Практики/Семантический чанкинг.md](data/machinedocs-encyclopedia/Практики/Семантический%20чанкинг.md) & [Иерархическая документация.md](data/machinedocs-encyclopedia/Архитектура/Иерархическая%20документация.md) | Нарезка по смыслу (а не по числу символов), самодостаточность чанка ~100–150 строк с путями, триггером и связями | Шесть критериев разделения границ флоу, дерево решений нарезки, разбор `task_ops.py` и сигнал `flow_split_recommended` (§12.4–12.5) |
| [data/cli-skills-encyclopedia/Форматы/Agent Skills (SKILL.md).md](data/cli-skills-encyclopedia/Форматы/Agent%20Skills%20%28SKILL.md%29.md), [Rules vs Skills.md](data/cli-skills-encyclopedia/Практики/Rules%20vs%20Skills.md) & [Работа агентов с CLI.md](data/cli-skills-encyclopedia/Практики/Работа%20агентов%20с%20CLI.md) | Стандарт `SKILL.md` (`name`, триггерный `description`, `<500` строк), связка `API/Index → CLI → Skills → Agent`, однострочный роутер в `AGENTS.md` | Готовый макет скилла `doc/skills/flow-audit/SKILL.md` в паре с командами `flow correlate` / `flow inspect` и строкой роутера в `doc/AGENTS.md` (§12.1–12.3) |
| [data/machinedocs-encyclopedia/Практики/Инструменты аудита для software factory.md](data/machinedocs-encyclopedia/Практики/Инструменты%20аудита%20для%20software%20factory.md) & [Аудит кода.md](data/machinedocs-encyclopedia/Практики/Аудит%20кода.md) | Детерминированные анализаторы выдают нормализованные JSON-findings с файлом и строкой до запуска ревью агента/человека | Контракты `arch docs flow correlate` и AST-сканера `arch docs flow inspect` (`undocumented_error_signals`, `mutation_signals`, `lines`) и протокол триажа (§12.2–12.3) |
| [data/sdd-research/03-инструменты-и-фреймворки.md](data/sdd-research/03-инструменты-и-фреймворки.md), [08-контекст-инженерия-агентов.md](data/sdd-research/08-контекст-инженерия-агентов.md) & [Исследование формата документации проекта и входящей задачи.md](data/machinedocs-encyclopedia/Практики/Исследование%20формата%20документации%20проекта%20и%20входящей%20задачи.md) | Сравнение `GitHub Spec Kit`, `OpenSpec`, `Kiro`, `BMAD`, `Tessl`; дисциплина `<200` строк для всегда загружаемых файлов; `task.json` как единый вход | Многомерная сравнительная матрица 9 технологий (§13.2–13.3) и аудит контракта `task.json` (`GAP-SYS-06`) |
| [data/sdd-encyclopedia/Флоу/Стандарты описания флоу.md](data/sdd-encyclopedia/Флоу/Стандарты%20описания%20флоу.md) | Триада представлений (**Flowchart + DMN 1.4+ + State Machine**), запрет бинарных картинок в пользу генерируемого Mermaid | Единая JSON-модель `decisions[]` + `lifecycle` и детерминированная генерация таблиц + Mermaid в `<slug>.md` (§5.1, §6.1, §7.4) |
| [data/machinedocs-encyclopedia/Примеры/Пример пакета документации фичи.md](data/machinedocs-encyclopedia/Примеры/Пример%20пакета%20документации%20фичи.md) | Пакет **ССФТБА** (разделение Спецификации, Сущностей, Флоу, Тестов, Безопасности, Архитектуры) | Флоу как связующий каркас по ссылкам `branch.refs` без превращения в God-object (§10.1) |
| [data/machinedocs-encyclopedia/Документация/Сущности.md](data/machinedocs-encyclopedia/Документация/Сущности.md) & [Data Model.md](data/sdd-encyclopedia/Сущности/Data%20Model.md) | Сущности владеют атрибутами и инвариантами состояния; политика `NO ASSUMPTIONS` | Ссылки `lifecycle.target_entities` и `refs.entities` на `ENT-*`; явный `oracle_status: "missing_oracle"` вместо домыслов (§6.3, §7.2) |
| [data/sdd-encyclopedia/Сущности/Delta Specs.md](data/sdd-encyclopedia/Сущности/Delta%20Specs.md) & [OpenSpec.md](data/sdd-encyclopedia/Инструменты/OpenSpec.md) | Двухслойное хранение (живой канон + дельта изменений задачи `ADDED / MODIFIED / REMOVED`) | Контракт `stageN/flow-delta.json` и команды `flow delta validate / apply` (§7.4, §10.3, §10.5) |
| [data/sdd-encyclopedia/Инструменты/GitHub Spec Kit.md](data/sdd-encyclopedia/Инструменты/GitHub%20Spec%20Kit.md) & [Kiro.md](data/sdd-encyclopedia/Инструменты/Kiro.md) | Фазовый конвейер `specify → plan → tasks → analyze → implement` и EARS-правила | Привязка к шагам `task-conf` и структурная валидация до реализации (§10.3, §10.4) |
| [data/sdd-encyclopedia/Процессы/Workflow SDD.md](data/sdd-encyclopedia/Процессы/Workflow%20SDD.md) & [Сквозной цикл разработки.md](data/machinedocs-encyclopedia/Практики/Сквозной%20цикл%20разработки.md) | Агентский SDLC `Intent → Plan → Build → Verify → Observe` с человеческими чекпоинтами | Матрица всех 12 типов задач `task-conf` и разделение `deterministic \| agent_judgment \| human_approval` (§6.3, §10.4.3) |
| [data/sdd-encyclopedia/Процессы/SDD в CI-CD.md](data/sdd-encyclopedia/Процессы/SDD%20в%20CI-CD.md) & [Docs-as-Code и CI.md](data/machinedocs-encyclopedia/Архитектура/Docs-as-Code%20и%20CI.md) | 3 уровня валидации спек (синтаксис, семантика, стандарты) и непрерывный `Drift Detection` | Пять эшелонов `FF-1..FF-5` и разделение `validate / check / coverage / scan` (§7.2, §11.4) |
| [data/sdd-encyclopedia/Сущности/Матрица трассируемости.md](data/sdd-encyclopedia/Сущности/Матрица%20трассируемости.md) & [06-качество-и-трассируемость.md](data/sdd-research/06-качество-и-трассируемость.md) | Двунаправленная трассируемость `IEEE 830` / `ISO 29148` (Forward & Backward, методы ТДИА) | Прямые ссылки `branch.refs` + автоматический обратный индекс `flows.index.json#referenced_by` + цепочка `AC ↔ FLOW#branch ↔ CASE` (§7.3, §10.4) |
| [data/sdd-research/02-стандарты-и-форматы-требований.md](data/sdd-research/02-стандарты-и-форматы-требований.md) & [EARS-требования.md](data/sdd-encyclopedia/Сущности/EARS-требования.md) | Шаблоны EARS (`WHILE <state> + WHEN <trigger> + IF <condition> → SHALL <outcome>`), критерии `INCOSE` | Связка `entry_states` + `when` + `outcome` (`postconditions`, `exit_code`, `http_status`, `error_code`) в каждой ветке (§5.1, §6.3) |
| [data/sdd-research/09-bdd-исполняемые-спеки.md](data/sdd-research/09-bdd-исполняемые-спеки.md) & [Тесты.md](data/machinedocs-encyclopedia/Документация/Тесты.md) | Защита от общего заблуждения одного агента («код + тест из одной головы»); независимый оракул | Обязательный `oracle_status`, узловые селекторы `refs.tests`, `Red-before-Green` и `--assert-guard` (§6.3, §7.2, §13.5) |
| [data/cli-skills-encyclopedia/Форматы/Progressive Disclosure.md](data/cli-skills-encyclopedia/Форматы/Progressive%20Disclosure.md) & [Agent-Friendly CLI Design.md](data/cli-skills-encyclopedia/Практики/Agent-Friendly%20CLI%20Design.md) | Поэтапное раскрытие деталей в рамках `--max-bytes`, семантические exit-коды, JSON-конверт ошибок с `suggestion`, `--dry-run` | Полное использование `CliEnvelope` и кодов `0 / 1 / 2 / 5 / 10 / 20` из `errors.py`, флаг `--dry-run` в `delta apply` и `close` (§7.4) |
| [data/machinedocs-encyclopedia/Документация/Следование архитектуре.md](data/machinedocs-encyclopedia/Документация/Следование%20архитектуре.md), [Код, контекст и минимальный harness.md](data/machinedocs-encyclopedia/Практики/Код,%20контекст%20и%20минимальный%20harness.md) & [Исследование software factory — пробелы и готовые практики.md](data/machinedocs-encyclopedia/Практики/Исследование%20software%20factory%20—%20пробелы%20и%20готовые%20практики.md) | Матрица Fowler (`Feedforward/Feedback × Computational/Inferential`), `REUSE_OR_PROMOTE vs KEEP_LOCAL`, плавный ввод гейтов `measure → warn → enforce`, таблица переходов с идемпотентностью | 4 режима пополнения, белый список `exempt_globs`, `--ratchet` и поля `idempotency`, `concurrency_guard`, `effects`, `retry_policy` (§3.3, §6.2–6.5, §10.5, §11.4) |
| [doc/tasks/UI-0028/stage1/plan.md](doc/tasks/UI-0028/stage1/plan.md), [doc/architecture/system/constraints-risks.md](doc/architecture/system/constraints-risks.md), `UI-0030`, `UI-0032`, `ARCH-contract` | Архитектурный паттерн `sf` (`JSON + generated .md + .index.json`), открытые ограничения `OPEN-*` и локальный гейт `run.sh --gate` | Полная совместимость `*.flow.json` с хранилищем `sf` и привязка системного бэклога `GAP-SYS-01..07` к `OPEN-*` (§6.1, §8, §14.3) |

### 15.2. Внешние индустриальные стандарты, научные статьи и бенчмарки (2024–2026)

1. **OMG Decision Model and Notation (DMN) v1.6 / v1.7** ([OMG DMN](https://www.omg.org/spec/DMN/), [PDF 1.6](https://www.omg.org/spec/DMN/1.6/PDF)) & **UiPath Agentic SDD Decision Tables (`PILOT-8674`)** ([PR #3944](https://github.com/UiPath/skills/pull/3944)) — типизированные `factors` (`allowed_values`), политики `UNIQUE / ANY / PRIORITY / FIRST / COLLECT`, детерминированная проверка `0 gaps / 0 overlaps / no masked branch`.
2. **W3C SCXML** & **XState v5/v6 JSON Statecharts** ([Stately Docs](https://stately.ai/docs/xstate/v6/xstate-v5-to-v6)) — чистая JSON-модель состояний (`initial / intermediate / terminal`) и проверка достижимости графа.
3. **OpenAPI Arazzo Specification v1.0.1 / v1.1.0 (May 2026)** ([OpenAPI Spec](https://spec.openapis.org/arazzo/v1.1.0.html)) — проверяемые `postconditions` (`successCriteria`), `retry_policy` и композиция процессов (`next: {kind: "flow", target: "FLOW-*"}`).
4. **CNCF Serverless Workflow / Open Workflow v1.0–1.1** ([DSL Reference](https://github.com/serverlessworkflow/specification/blob/main/dsl-reference.md)) — моделирование побочных эффектов, атомарности и компенсации (`effects`, `atomicity`, `rollback`).
5. **JSON Schema Draft 2020-12** ([JSON Schema](https://json-schema.org/draft/2020-12/schema)) — строгая валидация канона `arch-flow.schema.json` и `flow-delta.schema.json`.
6. **Birgitta Böckeler (Thoughtworks) — «Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl»** ([MartinFowler.com, Oct 2025](https://www.martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)) — таксономия `spec-first / spec-anchored / spec-as-source`, критика перегруза из 8 Markdown-файлов в Spec Kit, эффекта «кувалды» на мелких багах в Kiro и недетерминизма регенерации в Tessl.
7. **Независимый производственный бенчмарк SDD на 50 Python-тикетах (Q4 2026)** ([uvik.net SDD Benchmark](https://uvik.net/blog/spec-driven-development-benchmark/)) — сравнение `OpenSpec` (`84%` merge rate, `$2.71`), `Kiro` (`82%`, `$2.35`), `Spec Kit`, `BMAD` и работы без спек (`60%` на фичах).
8. **Прямой токен-бенчмарк `OpenSpec` vs `GitHub Spec Kit` (Mar 2026)** ([IT Chronicles Benchmark](https://medium.com/it-chronicles/is-your-safe-choice-burning-your-budget-1cfddf8782e4)) — доказательство перерасхода токенов в `Spec Kit` на `+97%..+109%` (`120.9K–181.0K` против `57.7K–91.7K` у `OpenSpec`) при ухудшении сходимости с первого прохода.
9. **Thibaud Gloaguen, Niels Mündler, Mark Niklas Müller, Veselin Raychev, Martin Vechev (ETH Zurich SRI, ICLR 2026 / Sep 2026) — «Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?»** ([arXiv:2602.11988v3](https://arxiv.org/html/2602.11988v3)) — доказательство того, что статические и автосгенерированные обзорные контекстные файлы увеличивают стоимость инференса на `+20%..+23%` без статистически значимого роста успеха.
10. **Lulla et al. (Jan 2026) — влияние точечных операционных инструкций на эффективность агентов** ([arXiv:2601.20404](https://arxiv.org/abs/2601.20404)) — сокращение выходных токенов на `−16.58%` и медианного времени выполнения на `−28.64%` при точечных операционных указателях вместо общих обзоров.
11. **Aristidis Vasilopoulos (Feb 2026) — «Codified Context: Infrastructure for AI Agents in a Complex Codebase»** ([arXiv:2602.20478](https://arxiv.org/abs/2602.20478), [GitHub](https://github.com/arisvas4/codified-context-infrastructure)) — трёхъярусная архитектура контекста на распределённой системе `108,000 LOC` C# за 283 агентные сессии с валидацией перекрёстных ссылок.
12. **Chroma Research (Hong, Troynikov, Huber, 2025) — «Context Rot» & Tokalator Context Engineering Toolkit (Apr 2026)** ([arXiv:2604.08290](https://arxiv.org/html/2604.08290)) — неравномерная деградация 18 LLM при росте входного контекста и резкое усиление ошибок от дистракторов, критичное для слабых моделей.
13. **Chunqiu Steven Xia et al. — «Agentless: Demystifying LLM-based Software Engineering Agents»** ([arXiv:2407.01489](https://ar5iv.labs.arxiv.org/html/2407.01489)) — трёхуровневая детерминированная локализация до строк кода (`17.8K–42K` токенов, `$0.03–$0.70`) против дорогого свободного блуждания агентов.
14. **Siru Ouyang et al. — «RepoGraph: Enhancing AI Software Engineering with Repository-level Code Graph»** ([arXiv:2410.14684](https://arxiv.org/html/2410.14684v1)) — доказательство того, что 1-hop срез графа (`717–2,310` токенов) повышает точность, а плоский 2-hop срез (`10,505` токенов) снижает её (`29.67% → 26.00%`).
15. **LARGER: Lexically Anchored Repository Graph Exploration and Retrieval (May 2026)** ([arXiv:2605.16352](https://arxiv.org/html/2605.16352)) — количественное сравнение стоимости неконтролируемого обхода графа (`LocAgent`: `711.5K–940.7K` токенов/задача) и экономной локализации.
16. **«How Much Do Structural Tools Help Small Coding Agents?» (Oct 2026)** ([arXiv:2610.33958](https://arxiv.org/pdf/2610.33958)) — предрегистрированное исследование `170,500` эпизодов малых открытых моделей (`Qwen3 0.6B–32B`, `Gemma 4 E2B–12B`) на 500 held-out задачах SWE-bench (переполнение лимита шагов при свободном поиске без пред-локализации).
17. **Влияние инженерного harness'а на малые/средние открытые модели (`Qwen3.6-27B`: `67.8% → 87.4%–90.0%` SWE-bench Verified, Sep 2026)** ([Capital & Compute Analysis](https://capitalandcompute.net/blog/why-local-llms-fail-agentic-coding/)) — демонстрация того, что качество выполнения на малых весах определяется архитектурой CLI-среды и подачей контекста сильнее, чем размером модели.
18. **Consort: A Spec-First Agent Framework for Enforced, Test-Driven Development (Sep 2026)** ([arXiv:2609.09671v1](https://arxiv.org/html/2609.09671v1)) & **Optivem ATDD Enforcement (Sep 2026)** ([Optivem Journal](https://journal.optivem.com/p/spec-driven-development-make-specs)) — принудительный TDD с неизменяемыми тестами (`Tests immutable`) против рекомендательных прозаических гейтов `Spec Kit`.
19. **Fission-AI OpenSpec v1.0–1.13 (`OPSX`)** ([Workflows](https://github.com/Fission-AI/OpenSpec/blob/main/docs/workflows.md), [Parallel Merge Remediation Plan](https://github.com/Fission-AI/OpenSpec/blob/main/openspec-parallel-merge-plan.md)) — двухслойный контур живых спек и дельт и проблема затирания при блочном Markdown-мерже параллельных веток.
20. **GitHub Spec Kit** ([Repository](https://github.com/github/spec-kit), [Discussion #152](https://github.com/github/spec-kit/discussions/152)) — проблема отсутствия консолидированной системной модели при пофичевом хранении спек.
21. **EventCatalog v3–v5 Architecture Graph for AI Agents** ([EventCatalog v5](https://www.eventcatalog.dev/blog/eventcatalog-v5), [Document AI Agents](https://www.eventcatalog.dev/blog/document-ai-agents)) — типизированный граф `domains ↔ flows ↔ entities ↔ schemas ↔ ubiquitous-language` и расчёт `blast radius`.
22. **Martin Fowler / Thoughtworks — Harness Engineering & Technology Radar Vol. 34 (Apr 2026)** ([Harness Engineering](https://martinfowler.com/articles/harness-engineering.html), [Tech Radar Vol. 34](https://www.thoughtworks.com/content/dam/thoughtworks/documents/radar/2026/04/tr_technology_radar_vol_34_en.pdf)) & **Anthropic Context Engineering** ([Anthropic Research](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents)) — баланс вычислительных сенсоров и вероятностных инструкций при минимально достаточном контексте.




