---
title: "Полный аудит форматов, хранения и использования архитектурной документации sf"
description: "Комплексный аудит форматов архитектурной документации, JSON-схем, валидаторов, физической модели хранения и фактического использования агентами/задачами в сопоставлении с энциклопедиями data/ и исследованиями 2025–2026 гг."
status: draft
version: "1.0"
date: "2026-11-23"
git_rev: "f8cb406"
arch_version: "0.2.0"
tags: [audit, architecture-docs, schemas, storage, codified-context, sdd]
related:
  - ARCH-contract
  - ARCH-audit
  - ADR-0001
  - CAP-addressable-contracts
  - CAP-doc-integrity
  - SPEC-cli-implementation
  - REG-cli-command-map
  - REG-cli-validation-rules
  - UI-0018
  - UI-0026
  - UI-0028
  - UI-0029
  - UI-0031
---

# Полный аудит форматов, хранения и использования архитектурной документации

**Дата проверки:** 2026-11-23  
**Проверенный снимок:** `f8cb406` (`arch 0.2.0`)  
**Область аудита:** `doc/architecture/` (45 индексируемых документов + `README.md`), `doc/architecture/schemas/` (`document.schema.json`, `index.schema.json`, 15 схем `bodies/*.json`), `doc/config/paths.yaml`, `doc/skills/` (`architecture-read`, `architecture-docs`, `arch-cli`), корпус задач `doc/tasks/` (33 родительских задачи и 44 подзадачи — 77 файлов `task.json`), справочный корпус `data/` и актуальные внешние практики 2025–2026 гг.

> **Методология и разделение утверждений.** В соответствии с `README.md` в отчёте явно разграничены: **(1) факты проекта**, подтверждённые прогонами `arch` CLI, тестами и анализом файлов на снимке `f8cb406`; **(2) рекомендации справочников `data/` и внешних первичных источников**; **(3) выводы аудита** (оценка рисков и инженерных компромиссов); **(4) открытые вопросы (`NEEDS CLARIFICATION`)**, требующие решения владельца.

---

## 0. Резюме аудита (Executive Summary)

Архитектурный контур `sf` опирается на зрелую инженерную концепцию, опережающую типичные практики одиночных инструкционных файлов (`AGENTS.md` / `CLAUDE.md`):
- выстроена трёхуровневая архитектура контекста (**Codified Context**: компактные маршрутизирующие `AGENTS.md` → процедурные скиллы `doc/skills/` → адресуемая база архитектурных знаний `doc/architecture/` с воспроизводимым `index.json`);
- проведена чёткая граница между детерминированным CLI (`arch`) и смысловой работой агента;
- реализованы адресуемые разделы `DOC-ID#section-id` (`CAP-addressable-contracts`), локальный детерминированный поиск с изоляцией справочного слоя `data/`, сборка объявленного контекста задачи (`arch docs context`) и анализ влияния правок по явным связям (`arch docs impact`);
- детерминизм индекса подтверждается двойной пересборкой с `PYTHONHASHSEED=0` и `PYTHONHASHSEED=12345` (`bash doc/tests/run.sh --index-only`), а `arch docs check-links` подтверждает `0` битых стандартных Markdown-ссылок в 45 документах.

Вместе с тем глубокая сверка контракта, схем, валидатора и фактического корпуса выявила **системный разрыв между принятым контрактом (`ARCH-contract` v1.3) и реально исполняемыми проверками**, создающий на ряде участков «театр валидации»:

| Измерение аудита | Состояние | Ключевой установленный факт |
|---|---|---|
| **1. Форматы и JSON Schema метаданных** | **Требует синхронизации** | Исполняемая `document.schema.json` разрешает `additionalProperties: true` и требует строки в `source_refs`, прямо противореча `ARCH-contract` §6.2 (`additionalProperties: false` и типизированные объекты `source_refs`). |
| **2. Валидация тел (`schemas/bodies/*.json`)** | **Критично (нерабочий гейт)** | `validate_document_body()` в `doc/tools/arch/body_validation.py` читает ключи из корня JSON Schema вместо `schema["properties"]` и сравнивает заголовки без `## ` со строками с `## `. Функция **всегда возвращает `[]`**, пропуская **15 из 45 документов (33,3%)**, нарушающих собственные body-схемы. |
| **3. Хранение и единственность источников** | **Нарушены базовые инварианты** | Вопреки запрету манифеста и `ARCH-contract` §1 в репозитории существуют **два расходящихся манифеста** (`Манифест агентной software factory.md` на 113,9 КБ и `doc/architecture/system/manifest.md` на 136,9 КБ) и **два документа `type: system`**, а каталог `stage{stage}/architecture-delta/` не объявлен в `paths.yaml` и блокируется гейтом путей. |
| **4. Применение форматов в корпусе** | **Неоднородно** | В `doc/architecture/system/manifest.md` присутствуют **33 ссылки Obsidian `[[wikilink]]`** и callout-блоки (невидимые для `check-links`), в 5 документах — локальные пути рабочей станции, статус `current` использован **0 раз**, а флаг `implemented` искажает статус работающего ядра CLI. |
| **5. Использование агентами и задачами** | **Работает в новых задачах, сбоит на крупных и ранних записях** | Чтение `SPEC-cli-implementation#9-cli-clipy` (35 097 Б) с дефолтным бюджетом `arch docs read` **падает с `SECTION-TOO-LARGE`**; явные якоря `{#anchor}` размечены только в **6 из 45** документов; в `UI-0001..UI-0007` остаётся **37 битых `project_context_refs`**, а `arch scan` выявляет осиротевший каталог `doc/tasks/UI-0032-0005` без `task.json`. |

### Сводные количественные показатели корпуса на снимке `f8cb406`

| Метрика | Фактическое значение |
|---|---|
| Всего `.md`-файлов в `doc/architecture/` | **46** (45 в `index.json` + неиндексируемый `doc/architecture/README.md` без frontmatter) |
| Распределение по доменам (`domain`) | `system`: 21, `task-lifecycle`: 10, `execution-verification`: 6, `model-routing`: 3, `task-intake`: 3, `project-knowledge`: 2 |
| Объявлено типов в `paths.yaml` (`document_types`) | **26** (используются **20**: 15 с body-схемой + 5 `prose-only`; зарезервированы **6**) |
| Распределение `status` в `index.json` | `draft`: **43** (95,6%), `accepted`: **2** (`ADR-0001`, `ARCH-contract`), `current` / `deprecated` / `superseded`: **0** |
| Распределение `implemented` во frontmatter | `false`: **30**, `true`: **12**, поле опущено: **3** (`ARCH-contract`, `ARCH-audit`, `MAN-software-factory` → в индексе `false`) |
| Нарушения собственных `schemas/bodies/*.json` | **15 из 45 документов (33,3%)** |
| Документы с явными стабильными якорями `{#anchor}` | **6 из 45 документов (13,3%)**, всего 25 явных якорей |
| Документы с явной load-when формулировкой в `summary` | **11 из 45 документов (24,4%)** |
| Секции H2, превышающие лимит `arch docs read` (32 768 Б) | **2 секции H2** (`SPEC-cli-implementation` — 35 097 Б; `MAN-software-factory` — 56 230 Б) |
| Задачи с заполненным `related_docs` / `project_context_refs` | **60 / 77** и **55 / 77** (среди них **37 битых ссылок** в `UI-0001..UI-0007`) |
| Осиротевшие архитектурные документы (`0` входящих связей) | **2 документа** (`CAP-role-model-routing`, `RUNBOOK-arch-operations`); **21 из 45** ни разу не упомянуты в `task.json` |

---

## 1. Аудит форматов архитектурной документации

### 1.1. Расхождения конверта метаданных (`frontmatter`)

*(Факты проекта)* В репозитории одновременно присутствуют четыре описания схемы frontmatter: принятый контракт [architecture-contract.md](doc/architecture/system/architecture-contract.md) (§6.1–6.2), конфигурация [paths.yaml](doc/config/paths.yaml), исполняемая схема [document.schema.json](doc/architecture/schemas/document.schema.json) и схема индекса [index.schema.json](doc/architecture/schemas/index.schema.json). Между ними выявлены шесть структурных противоречий:

| Аспект контракта | `ARCH-contract` §6.2 (`status: accepted`) | `paths.yaml` / скиллы | Исполняемая `document.schema.json` | Следствие |
|---|---|---|---|---|
| Неизвестные поля (`additionalProperties`) | `false` («не скрывать опечатки в новых полях») | В `architecture-docs` перечислен закрытый список опциональных полей | **`true`** | Опечатки во frontmatter (`implemnted`, `relatd`, `owners`) молча проходят `arch validate`, но отбрасываются при генерации `index.json`. |
| Формат `source_refs` | Массив **объектов** `{kind, repo, path, symbol, pointer, revision, url}` с `if/then`-валидацией | Не проверяется | Массив **строк** (`{"type": "string", "minLength": 1}`) | **Прямой конфликт:** документ, оформленный строго по принятому `ARCH-contract` §6.1, отвергается `arch validate` и `index.schema.json`. |
| Паттерн `id` | `^[A-Za-z][A-Za-z0-9._:-]*$` (`minLength: 3`, `maxLength: 96`) | `document_id: "^[A-Za-z][A-Za-z0-9._:-]*$"` | `^[A-Z][A-Za-z0-9_-]*$` | Три разных ограничения: `paths.yaml` разрешает строчное начало, `.` и `:`, а `document.schema.json` запрещает их и не ограничивает `minLength`/`maxLength`. |
| Перечисление `type` | Явный `enum` из 26 типов | `project.document_types` (26 типов, проверяется в `docs paths --check`) | Свободный паттерн `^[a-z][a-z0-9-]*$` | `arch validate` пропускает несуществующие типы (например, `note` и `view` в `test_arch.py`), если не вызван `docs paths --check`. |
| Условные поля жизненного цикла | `allOf`: `type == decision → decision_status`; `superseded → superseded_by` | Заявлено обязательным в `architecture-docs/SKILL.md` | **Отсутствуют** (`decision_status` и `superseded_by` даже не объявлены в `properties`) | ADR без `decision_status` или документ со `status: superseded` без `superseded_by` проходит валидацию без ошибок. |
| Поля `implemented`, `aliases`, `owner` | `owner` описан в §6.2; `aliases` используется в `arch docs search`; `implemented` копируется в `index.json` | Описаны в скиллах и `CAP-addressable-contracts` | **Отсутствуют** в `document.schema.json` (`implemented` есть только в `index.schema.json`) | В `document.schema.json` не проверяются типы `implemented` (`boolean`) и `aliases` (`array[string]`) до этапа сборки индекса. |

### 1.2. Критический дефект валидации тел документов (`schemas/bodies/*.json`)

*(Факт проекта — воспроизводимое расхождение между контрактом и CLI, диагностированное по `doc/architecture/schemas/bodies/*.json`, `doc/tools/arch/store.py` и `doc/tools/arch/body_validation.py`)*:

В `doc/architecture/schemas/bodies/` лежат 15 файлов JSON Schema Draft 2020-12. Тест [test_doc_type_registry.py](doc/tests/test_doc_type_registry.py) проверяет наличие этих файлов и строку `$schema`, а `ArchitectureStore.validate()` вызывает `validate_document_body(doc.body, doc_type, schemas_dir)` для каждого документа. Однако сама функция `validate_document_body()` **является полным no-op** из-за тройной ошибки:

1. **Чтение мимо структуры JSON Schema:** все ограничения в `bodies/*.json` записаны внутри `schema["properties"]` (например, `schema["properties"]["required_sections"]["items"]["enum"]`, `schema["properties"]["has_table"]`), тогда как `body_validation.py` обращается к верхнему уровню словаря: `schema.get("required_sections", [])`, `schema.get("has_table")`, `schema.get("has_terms")`, `schema.get("table_columns")`, `schema.get("has_consequences")`. Все эти вызовы **всегда возвращают `None` или `[]`**.
2. **Несовпадение формата заголовков:** `_extract_sections(body)` извлекает `re.findall(r"^##\s+(.+)$", body, flags=re.MULTILINE)` **без** префикса `## ` (возвращая `"Последствия"`), а проверки сравнивают результат со строками **с префиксом** (`"## Последствия" not in sections` и `"## Назначение"` в `enum`). Если исправить только чтение схемы, валидатор отвергнет 100% документов.
3. **Отсутствие фильтрации code fences и явных якорей `{#anchor}`:** `_extract_sections()` читает сырой `body` вместе с примерами внутри ` ```markdown ` и не отрезает суффиксы `{#section-id}` из `CAP-addressable-contracts` (заголовок `## Требования {#anchors}` превращается в строку `"Требования {#anchors}"` и не совпадает с `"## Требования"`).

Дополнительно сами схемы `bodies/*.json` расходятся с шаблонами `ARCH-contract` §5.5:
- шаблоны в `ARCH-contract` §5.5 (подразделы A–I) задают **англоязычные** заголовки (`## Purpose and scope`, `## Context and problem`, `## Main and alternate paths`), а `bodies/*.json` требуют **русскоязычные** заголовки с иным составом секций (`## Шаги`, `## Пути отказа`, `## Политика`, `## Правило остановки`);
- в `bodies/flow.json` (`enum` из 3 секций, `minItems: 1`) и `bodies/capability.json` (`enum` из 2 секций, `minItems: 1`) JSON Schema формально требует лишь *одну любую* секцию из списка, а не полный каркас документа;
- в `doc/tools/tests/` и `doc/tests/` отсутствует хотя бы один негативный тест, проверяющий срабатывание `validate_document_body()` на документе с пропущенной секцией.

### 1.3. Профиль Markdown и ссылочная модель

- В `CAP-addressable-contracts` качественно формализована адресация `DOC-ID#section-id` с приоритетом явных якорей `{#section-id}`, игнорированием ссылок и заголовков внутри fenced code blocks и строгим отказом `SECTION-TOO-LARGE` вместо молчаливой обрезки.
- При этом нормативное правило `ARCH-contract` §3.6 (*«Не использовать raw HTML, Obsidian `[[wikilink]]`, vault-specific callout/embeds… в canonical docs»*) **не подкреплено проверкой в CLI**: ни `arch validate`, ни `arch docs check-links`, ни `arch docs paths --check` не детектируют `[[wikilink]]`, Obsidian callouts `> [!note]` и локальные абсолютные пути файловой системы.

---

## 2. Аудит корректности применения форматов в корпусе (`doc/architecture/`)

### 2.1. Документы, нарушающие собственные `schemas/bodies/*.json` (15 из 45)

Из-за нерабочего `body_validation.py` в корпусе накопилось **15 документов (33,3%)**, структура которых расходится с заявленной схемой их типа:

| ID документа | Путь | Тип (`type`) | Ожидание `bodies/<type>.json` | Фактические разделы `##` в документе | Диагноз |
|---|---|---|---|---|---|
| `DOM-task-lifecycle` | `doc/architecture/domains/task-lifecycle/README.md` | `domain` | `## Назначение и граница`, `## Принадлежит`, `## Не принадлежит` | `## Назначение и граница`, `## Принадлежит`, `## Инварианты`, `## Ключевые записи` | Пропущен раздел границ исключения (`## Не принадлежит`). |
| `ENT-task-input` | `doc/architecture/domains/task-lifecycle/entities/task-input.md` | `entity` | `## Назначение`, `## Концептуальное содержание`, `## Инварианты` | `## Назначение`, `## Концептуальная информация`, `## Контракт именования`, `## Инварианты` | Дрейф названия секции (`информация` вместо `содержание`). |
| `ENT-task-record` | `doc/architecture/domains/task-lifecycle/entities/task-record.md` | `entity` | Те же 3 секции | `## Назначение и граница`, `## Хранение`, `## Инварианты`, `## Команды`, `## Evidence` | Свободная структура без `## Концептуальное содержание`. |
| `ENT-verification-evidence` | `doc/architecture/domains/task-lifecycle/entities/verification-evidence.md` | `entity` | Те же 3 секции | `## Значение домена и граница`, `## Значимые атрибуты...`, `## Инварианты`, `## case-coverage-v1` | Написан по раннему переводу английского шаблона §5.5D, а не по `entity.json`. |
| `FLOW-cli-task-lifecycle` | `doc/architecture/domains/task-lifecycle/cli-task-lifecycle.md` | `flow` | Хотя бы одна из: `## Шаги`, `## Пути отказа`, `## Состояние модели` | `## Структура директории`, `## arch task init...`, `## arch task validate...`, `## Инварианты` | **Ошибочная типизация:** по содержанию это CLI-справочник, а не `flow`. |
| `FLOW-cli-subtask-lifecycle` | `doc/architecture/domains/task-lifecycle/cli-subtask-lifecycle.md` | `flow` | То же | `## Структура директории`, `## arch task subtask init...`, `## Правила` | **Ошибочная типизация:** справочник подкоманд CLI, а не `flow`. |
| `FLOW-create-task` | `doc/architecture/domains/task-intake/flows/create-task.md` | `flow` | То же | `## Назначение и возможность`, `## Триггер...`, `## Предусловия...`, `## Основные и альтернативные пути` | Оформлен по шаблону `ARCH-contract` §5.5E, который не совпадает с `flow.json`! |
| `FLOW-document-session` | `doc/architecture/domains/execution-verification/flows/document-session.md` | `flow` | То же | `## Триггер и область`, `## Пути`, `## Инварианты` | Заголовки не совпадают со схемой `flow.json`. |
| `FLOW-execute-task` | `doc/architecture/domains/task-lifecycle/flows/execute-task.md` | `flow` | То же | `## Триггер и актёры`, `## Предусловия`, `## Основной путь`, `## Условия остановки`, `## Не цели` | Заголовки не совпадают со схемой `flow.json`. |
| `FLOW-kilo-session-audit` | `doc/architecture/domains/execution-verification/flows/kilo-session-audit.md` | `flow` | То же | `## CLI-снимок сессии`, `## Доступ и схема`, `## Найти нужную сессию`... | По содержанию ближе к `runbook` / `implementation-spec`, чем к `flow`. |
| `MAN-software-factory` | `doc/architecture/system/manifest.md` | `system` | `## Назначение`, `## Граница области`, `## Архитектурные точки зрения`, `## Домены` | `## Цель`, `## Базовые принципы`, `## Четыре слоя...` | Дубликат корневого манифеста; нарушает и `system.json`, и правило единственности `type: system`. |
| `REG-cli-command-map` | `doc/architecture/system/cli-command-map.md` | `rule-set` | `## Политика`, `## Правило остановки` | `## Запись и восстановление`, `## Коды выхода`, `## Документальные контракты`... | Справочный реестр команд, которому тесна схема `rule-set.json`. |
| `REG-cli-validation-rules` | `doc/architecture/system/cli-validation-rules.md` | `rule-set` | `## Политика`, `## Правило остановки` | `## Источники правил`, `## Обязательные поля`, `## Объект source`... | Спецификация правил валидации без секций `rule-set.json`. |
| `REG-task-number-registry` | `doc/architecture/system/task-number-registry.md` | `rule-set` | `## Политика`, `## Правило остановки` | `## Политика (из корневого манифеста)`, ..., `## Правило остановки` | Уточнение в скобках в заголовке `## Политика (...)` ломает точное совпадение. |
| `VIEW-security` | `doc/architecture/system/security.md` | `security-view` | `## Активы`, `## Ненадёжные входные данные`, `## Требуемые свойства дизайна`, `## Риски / пробелы` | `## Требуемые свойства дизайна (механизм нерешён)` | Аналогичное уточнение в скобках в заголовке H2. |

### 2.2. Неоднородность `capability-spec` (нормативные требования и сценарии)

В `ARCH-contract` §5.5C и энциклопедии `data/sdd-encyclopedia/Сущности/EARS-требования.md` для `capability-spec` задан строгий контракт: атомарные нормативные требования с модальным глаголом `SHALL` и наблюдаемые сценарии `WHEN` / `THEN`. Фактическая картина по 5 документам `type: capability-spec`:

- `CAP-doc-integrity` и `CAP-single-agent-execution` — содержат и `SHALL`, и `WHEN`/`THEN` (при этом смешивая русскоязычный текст с английскими ключевыми словами).
- `CAP-role-model-routing` и `CAP-task-intake` — содержат сценарии `WHEN`/`THEN`, но не используют нормативную связку `SHALL`.
- `CAP-addressable-contracts` (крупнейший и фактически реализованный контракт на 10,4 КБ) — **не использует ни `SHALL`, ни `WHEN`/`THEN`**, описывая поведение обычными маркированными списками.

### 2.3. Дрейф метаданных `status`, `implemented`, `related` и локальных путей

1. **Мёртвый статус `current` и внутреннее противоречие `ARCH-contract`:** из пяти статусов (`draft`, `current`, `accepted`, `deprecated`, `superseded`) в корпусе задействованы только `draft` (43) и `accepted` (2). В самом [architecture-contract.md](doc/architecture/system/architecture-contract.md) во frontmatter указано `status: accepted`, а на строке 16 тела — `**Статус:** current`.
2. **Ложные сигналы `implemented: false`:** у реально работающих документов ядра — `SPEC-cli-implementation`, `SPEC-cli-testing`, `EXAMPLES-cli-usage`, `RUNBOOK-arch-operations`, `VIEW-cli-package`, `VIEW-components`, `VIEW-data` — выставлено `implemented: false` и `status: draft` (а у `ARCH-contract` поле `implemented` опущено и в `index.json` превращается в `false`). Агент, фильтрующий `index.json` по `implemented: true`, теряет основную спецификацию реализации CLI и тестов.
3. **Самоссылка в графе `related`:** `SPEC-cli-implementation` включает собственный идентификатор `SPEC-cli-implementation` в массив `related`, а `ArchitectureStore.validate_related()` не запрещает петли `doc.id in doc.related`.
4. **Абсолютные пути рабочей станции в 5 канонических документах:** вопреки прямому запрету `ARCH-contract` §6.1 и принципам OKF, локальные пути старого окружения зашиты во frontmatter `source_refs` у `ARCH-contract`, `ARCH-audit`, `MAN-software-factory` и в тексте `ADR-0001` и `RUNBOOK-arch-operations` (включая несуществующие файлы `doc.architecture.md` и `doc.architecture-audit.md`).
5. **Нарушение профиля Markdown в `doc/architecture/system/manifest.md`:** в каноническом файле присутствуют **33 ссылки Obsidian `[[Сущности]]`, `[[Флоу]]`, `[[Frontmatter-схемы]]`...** и callout-блоки `> [!note]` / `> [!abstract]`. Поскольку `arch docs check-links` проверяет только стандартные ссылки `[text](path)`, все 33 wikilink-ссылки остаются непроверенными и не работают в обычных Markdown-рендерерах.
6. **Несоблюдение конвенции имён файлов (`ARCH-contract` §4.4):** правило *«Имя файла обычно совпадает с `id` и имеет `.md`»* нарушено в **44 из 45 документов**. Кроме того, внутри доменов смешиваются одиночные файлы (`capability.md`, `flow.md`) и одноимённые подкаталоги (`capabilities/*.md`, `flows/*.md`).

---

## 3. Аудит модели хранения и физической структуры

### 3.1. Дублирование корневого манифеста и конфликт `type: system`

Один из самых жёстких инвариантов проекта нарушен на физическом уровне:
- Корневой [Манифест агентной software factory.md](Манифест%20агентной%20software%20factory.md) (552 строки, **113 944 Б**), `ARCH-contract` §1, `VIEW-data` и `doc/tests/README.md` требуют, чтобы манифест существовал **в единственном экземпляре в корне**, без копий в `doc/architecture/`.
- Одновременно в `doc/architecture/system/manifest.md` хранится второй экземпляр (`id: MAN-software-factory`, 709 строк, **136 985 Б**), на который ссылается `doc/skills/architecture-docs/SKILL.md` как на «единственный манифест».
- Оба файла **разошлись на 23 041 Б**: в корневом манифесте есть принцип `15` о клиентонезависимости среды агента и `15a` о CLI, тогда как в `doc/architecture/system/manifest.md` принцип о среде отсутствует, но добавлены принцип `17` (пересборка системы по документации) и обширные разделы о `task-conf`.
- Одновременно оба документа — `SYS-simple-factory` (`overview.md`) и `MAN-software-factory` (`manifest.md`) — имеют `type: system`, хотя `ARCH-contract` §5.5 фиксирует: *«`system` — Да, один на систему»*.
- Аналогичное раздвоение возникло между корневым файлом `Исследование software factory — пробелы и готовые практики.md` (25 258 Б) и одноимённой статьёй в `data/machinedocs-encyclopedia/Практики/` (32 422 Б).

### 3.2. Блокировка `architecture-delta` правилами `paths.yaml`

В `ARCH-contract` (§1, §3.7, §5.5J, §7.2) и глоссарии (`TERM-architecture-delta`) подробно специфицирован каталог дельт задачи `doc/tasks/<task_key>/stage<N>/architecture-delta/` с YAML-конвертом (`ADDED | MODIFIED | REMOVED | RENAMED`). Однако в [paths.yaml](doc/config/paths.yaml) при включённом `only_declared_paths: true` шаблон `{tasks}/{task_key}/stage{stage}/architecture-delta/{slug}.md` **не объявлен** (так же как не объявлен для подзадач и не создана схема `architecture-delta.schema.json`). Любая попытка агента создать архитектурную дельту по контракту немедленно приводит к отказу `arch docs paths --check` и локального гейта `--gate`.

### 3.3. Рассинхронизация правила `frontmatter_required_for` и `README.md`

В `paths.yaml` записано правило `frontmatter_required_for: ["{architecture}/**/*.md"]`, однако [doc/architecture/README.md](doc/architecture/README.md) не имеет YAML frontmatter, а `ArchitectureStore.load_documents()` содержит специальное исключение в коде (`if path == self.docs / "README.md": continue`). Исключение разумно по смыслу, но не отражено декларативно в `paths.yaml`.

### 3.4. Гранулярность и монолитные документы (проблема чанкинга)

По канонам `data/machinedocs-encyclopedia/Практики/Семантический чанкинг.md` (~100–150 строк на единицу знания) и `data/sdd-research/08-контекст-инженерия-агентов.md` (<200 строк для оперативно загружаемых файлов) большинство доменных файлов `sf` компактны (30–180 строк). Но системный каталог `doc/architecture/system/` перегружен крупными монолитами:

1. `MAN-software-factory` (`system/manifest.md`) — **709 строк / 136 985 Б** (одна секция H2 `## Предлагаемая модель хранения документации и тестов` занимает **56 230 Б**);
2. `ARCH-contract` (`system/architecture-contract.md`) — **1 211 строк / 135 938 Б**;
3. `SPEC-cli-implementation` (`system/implementation-spec.md`) — **841 строка / 57 175 Б** (секция H2 `## 9. CLI (cli.py)` занимает **35 097 Б**);
4. `ARCH-audit` (`system/architecture-audit.md`) — **285 строк / 30 854 Б** (исторический протокол аудита ранних черновиков v1.0→v1.2 размещён в активном слое `system/` с типом `constraints-risks`, конкурируя в поиске с актуальным реестром ограничений `VIEW-open-constraints`).

---

## 4. Аудит корректности использования (CLI, скиллы, задачи)

### 4.1. Отказы адресного чтения `arch docs read` и устаревание `SPEC-cli-implementation`

- Дефолтный лимит `arch docs read` составляет `--max-bytes 32768`. Практический вызов:
  ```bash
  python3 doc/tools/arch/__main__.py docs read "SPEC-cli-implementation#9-cli-clipy" --json
  ```
  завершается с **exit 1 (`SECTION-TOO-LARGE`: `35097 bytes exceeds --max-bytes 32768`)**. Аналогично падает чтение раздела про хранение в `MAN-software-factory` (56 230 Б).
- Сам документ `SPEC-cli-implementation` (призванный по принципу 17 обеспечивать полную пересборку CLI без исходников) **существенно отстал от кода `arch 0.2.0`**: заголовок `## 9. CLI (cli.py)` ссылается на удалённый монолит `cli.py`, а дерево пакета в `§1.1` не содержит 8 реальных модулей (`doc_ops.py`, `flows.py`, `plan_policy.py`, `project_config.py`, `sections.py`, `session_audit.py`, `task_record.py`, `cli/commands/session.py`).

### 4.2. Покрытие стабильными якорями `{#anchor}` и качество `summary`

- Явные стабильные якоря `{#section-id}` присутствуют только в **6 из 45 документов** (`CAP-addressable-contracts`, `REG-cli-command-map`, `REG-cli-validation-rules`, `ENT-verification-evidence`, `FLOW-cli-task-lifecycle`, `SPEC-cli-implementation`). Остальные 39 документов (включая `DOM-task-lifecycle#инварианты`, зашитый в эталонный baseline-сценарий `doc/skills/README.md`!) полагаются на автогенерируемые slug-якоря, которые ломаются при любом редактировании текста заголовка.
- Поле `summary` сформулировано как явный триггер загрузки (*«Загружать при…» / «Точка входа для…»*) только у **11 из 45 документов (24,4%)**. У остальных 34 записей `summary` либо пересказывает тему, либо содержит технические пометки о версиях и датах (`ARCH-contract`, `ARCH-audit`), что снижает точность агентного отбора по `index.json` и `arch list`.

### 4.3. Связность с задачами (`doc/tasks/`), ошибка в `REG-cli-validation-rules` и пропуск в гейте

1. **Ошибка в документации валидатора [cli-validation-rules.md](doc/architecture/system/cli-validation-rules.md):** в таблице обязательных полей `task.json` утверждается, что элементы `related_docs` *«должны совпадать с `TASK_KEY_RE`»*. Фактически во всех 60 заполненных карточках задач в `related_docs` лежат идентификаторы архитектурных документов (`ARCH-contract`, `CAP-doc-integrity` и т.д.), соответствующие `document_id`, а не `TASK_KEY_RE`.
2. **37 битых ссылок в `project_context_refs` ранних задач (`UI-0001`..`UI-0007`):** карточки содержат относительные пути времён прототипа `data/simple/` (`../../../Манифест агентной software factory.md`, `../../../doc.architecture.md`, `../../../cli.skill.plan.md`). Из-за них `arch docs context --task UI-0001 --json` возвращает `complete: false` со статусом `missing`.
3. **Осиротевшие и неиспользуемые документы:** `CAP-role-model-routing` и `RUNBOOK-arch-operations` имеют **0 входящих ссылок** как из `related` других документов, так и из `related_docs` всех 77 карточек задач/подзадач. Всего **21 из 45 архитектурных документов** ни разу не привязан ни к одной задаче.
4. **Осиротевший каталог задачи мимо локального гейта:** команда `arch scan --brief` завершается с **exit 1** из-за инцидента:
   `[TASK] task UI-0032-0005: task.json missing [task.json]` (исследовательская заметка подзадачи положена на верхний уровень `doc/tasks/UI-0032-0005/research/` вместо `doc/tasks/UI-0032/subtasks/0005/`). При этом `arch docs paths --check` и `bash doc/tests/run.sh --gate` этот инцидент **пропускают**, так как `UI-0032-0005` формально подходит под маску `{task_key}`, а `arch scan` не входит в `run.sh --gate`.

---

## 5. Сопоставление с энциклопедиями `data/` и лучшими мировыми практиками (2025–2026)

| Подход / источник | Требование лучших практик | Статус в `sf` | Оценка и выявленный пробел |
|---|---|---|---|
| **Codified Context (3 яруса)** — `data/machinedocs-encyclopedia/Архитектура/Codified Context (3 яруса).md`; Vasilopoulos, Feb 2026 ([arXiv:2602.20478](https://arxiv.org/html/2602.20478v1), [companion repo](https://github.com/nohe-sohbi/codified-context-infrastructure)) | T1: компактная конституция с правилами и таблицей триггеров; T2: специализированные роли/скиллы; T3: атомарные спеки подсистем по запросу + **Drift Guardian** (проверка дрейфа кода относительно спек). | Реализованы все три яруса (`AGENTS.md` → `doc/skills/` → `doc/architecture/` + `arch docs context/read`). | Архитектура ярусов образцовая; не хватает автоматического контроля дрейфа «изменён модуль `doc/tools/arch/*.py` → помечен как требующий сверки связанный раздел `SPEC-cli-implementation` / `REG-cli-command-map`». |
| **Эмпирическая оценка `AGENTS.md`** — `data/sdd-research/08-контекст-инженерия-агентов.md`; Gloaguen et al., ETH Zurich, 2026 ([arXiv:2602.11988](https://arxiv.org/pdf/2602.11988)) | Короткие написанные разработчиком инструкции с неочевидными ограничениями инструментов дают выигрыш (+4–7% против автогенерации), тогда как широкие архитектурные обзоры в контексте вызывают лишнее блуждание агента и рост стоимости токенов на >20%. | `AGENTS.md` (18 строк) и `doc/AGENTS.md` (61 строка) компактны, написаны вручную и задают точные маршруты. Аудит `seesionaudit.md` на практике подтвердил вред чтения больших обзорных файлов (`nextplan.md`). | Входной слой T1 настроен верно; избыточный вес смещён в монолиты внутри `doc/architecture/system/` (57–137 КБ), которые необходимо дробить на адресуемые секции <15–20 КБ. |
| **Context & Harness Engineering** — Anthropic (*Effective Context Engineering for AI Agents*, [обзор](https://agentic-ai.readthedocs.io/en/latest/ContextEngineering/anthropic/)); OpenAI (*Harness Engineering*, [каталог практик](https://github.com/walkinglabs/awesome-harness-engineering), [разбор](https://dev.to/vnayak_hejib/harness-engineering-the-engineering-discipline-behind-reliable-ai-agents-kap)) | Контекст — конечный бюджет внимания; архитектурные ограничения должны исполняться детерминированными гейтами (fitness functions), а против накопления энтропии нужны регулярные циклы «сборки мусора» (lint / garbage collection). Индексные запросы экономят на порядки больше токенов, чем пофайловый `grep` ([разбор](https://alexlavaee.me/blog/context-infrastructure-agent-bottleneck/)). | Внедрены индексное чтение, строгий `paths.yaml`, `check-links`, SHA-256 снимки `evidence` и `docs impact`. | Два ключевых защитных механизма ослаблены: `body_validation.py` ничего не проверяет, а `arch scan` не включён в обязательный `run.sh --gate`. |
| **SDD: OpenSpec + Spec Kit + MADR 4.0** — `data/sdd-encyclopedia/`; обзоры 2026 ([ai-software-architect #38](https://github.com/codenamev/ai-software-architect/issues/38), [academicOps PR #3550](https://github.com/nicsuzor/academicOps/pull/3550), [ai-software-architect #122](https://github.com/codenamev/ai-software-architect/issues/122)) | Разделение живых целевых спек (`specs/`) и дельт изменений (`ADDED/MODIFIED/REMOVED`), плюс изоляция исторических развилок в компактно индексируемых записях MADR 4.0 (с YAML frontmatter и секцией `Confirmation`). | `ADR-0001` включает секцию `Подтверждение / как проверить` и `decision_status`. Однако во всём проекте создан всего **1 ADR**, а исторический отчёт `ARCH-audit` лежит прямо в `system/`. | Нужно: (1) разрешить `stage{stage}/architecture-delta/` в `paths.yaml` (в рамках `UI-0018`); (2) вывести исторические отчёты из оперативного слоя `system/`; (3) фиксировать новые архитектурные развилки отдельными ADR (как уже запланировано в `UI-0028`). |
| **OKF (Google Cloud) & Karpathy LLM Wiki** — `data/machinedocs-encyclopedia/Форматы/OKF (Open Knowledge Format).md`, `Архитектура/LLM Wiki и поддержка Obsidian.md` | Переносимые относительные ссылки внутри бандла, строгий `type`, автогенерация индекса и регулярный lint на сирот (`orphan pages`), противоречия статусов и запрещённый синтаксис. | В `data/machinedocs-encyclopedia/scripts/lint_wiki.py` эти проверки реализованы для энциклопедии, но не перенесены в `arch validate` для канонического `doc/architecture/`. | Добавить в `arch validate` / `arch scan --scope docs` проверки на `[[wikilink]]`, локальные абсолютные пути, самоссылки `related` и осиротевшие документы. |

---

## 6. Приоритизированный план исправлений и развития

### Приоритет P0 — Устранить «театр валидации» и расхождения схем
1. **Восстановить работоспособность `body_validation.py` и покрыть его негативными тестами:**
   - Валидировать извлечённые признаки документа через `Draft202012Validator` по `doc/architecture/schemas/bodies/<type>.json` (либо корректно читать `schema["properties"]`), предварительно очищая fenced code blocks (`_body_without_fences`), удаляя суффиксы `{#anchor}` и согласовав префикс `## `.
   - Добавить в `doc/tools/tests/test_arch.py` тесты, гарантирующие отказ `validate` при отсутствии обязательной секции, таблицы или колонки для каждого типа.
   - Согласовать единый язык шаблонных заголовков (русский) между `ARCH-contract` §5.5 и `schemas/bodies/*.json`, после чего выровнять или переклассифицировать 15 отклонённых документов (в частности, перевести `FLOW-cli-task-lifecycle` и `FLOW-cli-subtask-lifecycle` из `flow` в `implementation-spec` или `rule-set`).
2. **Привести `document.schema.json` и `index.schema.json` в соответствие с `ARCH-contract` §6.2:**
   - Включить `"additionalProperties": false`, явно описав все разрешённые поля (`id`, `type`, `title`, `summary`, `status`, `domain`, `decision_status`, `superseded_by`, `owner`, `implemented`, `aliases`, `related`, `source_refs`, `applies_to`, а при внедрении `UI-0028` — `terms`).
   - Унифицировать регулярное выражение `id` с `paths.yaml`, добавить `allOf`-правила для `decision` → `decision_status` и `superseded` → `superseded_by`.
   - Разрешить в `source_refs` типизированные объекты `{kind, repo, path, ...}` по `ARCH-contract` §6.2 и запретить абсолютные локальные пути (`^/`).
3. **Включить `arch scan` в локальный гейт (`doc/tests/run.sh --brief` и `--gate`):**
   - Устранить инцидент `doc/tasks/UI-0032-0005` (перенести `research/` в карточку родителя `UI-0032` или подзадачи `UI-0032/subtasks/0005/`) и гарантировать, что каталоги задач без `task.json` блокируют гейт.

### Приоритет P1 — Восстановить единственность истины и чистоту корпуса
4. **Ликвидировать раздвоение манифеста и дубль `type: system`:**
   - Слить расхождение (23 КБ) между корневым `Манифест агентной software factory.md` и `doc/architecture/system/manifest.md`, оставив ровно один канонический источник истины и тонкую ссылку со второго места; сохранить `type: system` только за `SYS-simple-factory` (`overview.md`).
5. **Очистить каноническую архитектуру от нерегламентированного синтаксиса и устаревших меток:**
   - Заменить 33 ссылки `[[wikilink]]` и callout-блоки Obsidian в `manifest.md` на валидный CommonMark/GFM и добавить детектор `[[...]]` в `arch docs check-links`.
   - Удалить локальные абсолютные пути рабочей станции из `ARCH-contract`, `ARCH-audit`, `MAN-software-factory`, `ADR-0001` и `RUNBOOK-arch-operations`.
   - Выставить `status: current` и `implemented: true` для работающих спецификаций ядра (`SPEC-cli-implementation`, `SPEC-cli-testing`, `EXAMPLES-cli-usage`, `RUNBOOK-arch-operations`, `VIEW-cli-package`, `VIEW-components`), убрать самоссылку из `SPEC-cli-implementation` и исправить ошибку про `TASK_KEY_RE` для `related_docs` в `REG-cli-validation-rules`.
   - Связать осиротевшие `CAP-role-model-routing` и `RUNBOOK-arch-operations` с доменными картами и `README.md`; вынести исторический отчёт `ARCH-audit` из оперативного слоя `system/` (или перевести его в архивный статус).

### Приоритет P2 — Чанкинг, адресуемость и связка с дорожной картой (`UI-0018`, `UI-0028`, `UI-0029`, `UI-0031`)
6. **Оптимизация под агентное чтение (`arch docs read` / `context` / `search`):**
   - Разбить секции >32 КБ (`SPEC-cli-implementation#9-cli-clipy` и `MAN-software-factory`) на компактные адресуемые подсекции и актуализировать список модулей в `SPEC-cli-implementation` §1.1.
   - Проставить явные стабильные якоря `{#anchor}` во всех цитируемых контрактах (начиная с `DOM-task-lifecycle#invariants` и системных документов).
   - Переписать `summary` у оставшихся 34 документов в формат чёткого условия выбора (`Загружать при изменении…`).
7. **Синхронизация с открытыми задачами бэклога:**
   - **`UI-0031`** (*Согласованность реестра типов архитектурных документов*): дополнить приёмку проверкой реального исполнения `body_validation.py` и обновить `stage1/plan.md` под обязательные разделы `tier: standard`.
   - **`UI-0018`** (*Живые спецификации и артефакты*): декларировать `{tasks}/{task_key}/stage{stage}/architecture-delta/{slug}.md` и схему конверта дельты в `paths.yaml`.
   - **`UI-0028`** (*JSON-канон глоссария*) и **`UI-0029`** (*JSON-модель продуктовых флоу*): результаты аудита полностью подтверждают обоснованность обеих задач.
   - **Контроль бэклога (`taskcontrol.md`)**: связать `arch docs impact` с ревалидацией незапущенных карточек `phase: intake` при изменении `ARCH-contract` и `paths.yaml`.

---

## 7. Открытые вопросы к владельцу (`NEEDS CLARIFICATION`)

1. **Каноническое расположение манифеста:** оставляем ли единственный полный текст манифеста внутри `doc/architecture/system/manifest.md` (с типом `cross-cutting-concept` / `rule-set`, чтобы по нему работали `arch docs search` и `arch docs read`, а в корне — краткий указатель), либо возвращаемся к правилу «полный манифест только в корне песочницы»?
2. **Язык заголовков шаблонов в `ARCH-contract` §5.5:** утверждаем ли русскоязычные заголовки H2 (`## Назначение`, `## Инварианты`, `## Требования`, `## Последствия`) как единственный нормативный стандарт и для текста `ARCH-contract` §5.5, и для `schemas/bodies/*.json`?
3. **Исторические карточки `UI-0001`..`UI-0007`:** следует ли одноразово нормализовать 37 старых `../../../`-путей в `project_context_refs` до проектно-относительных (чтобы `arch docs context` стал `complete: true`), или закрытые карточки ранних этапов заморожены как исторический след?

---

## 8. Протокол выполненных проверок

| Команда | Код выхода | Фактический результат |
|---|---:|---|
| `python3 doc/tools/arch/__main__.py --version` | `0` | `arch 0.2.0` |
| `python3 doc/tools/arch/__main__.py validate --brief` | `0` | `OK validate: architecture` (при неактивном `body_validation.py`) |
| `python3 doc/tools/arch/__main__.py index check` | `0` | `Index is current` |
| `python3 doc/tools/arch/__main__.py docs paths --check` | `0` | `All doc/ paths are declared and valid` |
| `python3 doc/tools/arch/__main__.py task registry check` | `0` | `task registry matches 33 task directories` |
| `python3 doc/tools/arch/__main__.py docs check-links --json` | `0` | `scanned_documents: 45, incident_count: 0` (без учёта `[[wikilink]]`) |
| `bash doc/tests/run.sh --index-only` | `0` | `OK: index freshness and reproducibility` |
| `python3 doc/tools/arch/__main__.py scan --brief` | `1` | `[TASK] task UI-0032-0005: task.json missing [task.json]` |
| `python3 doc/tools/arch/__main__.py docs read "SPEC-cli-implementation#9-cli-clipy" --json` | `1` | `SECTION-TOO-LARGE: 35097 bytes exceeds --max-bytes 32768` |
| `python3 -m unittest discover -s doc/tools/tests` | `0` | `Ran 19 tests — OK` |
| `python3 -m unittest doc/tests/test_doc_type_registry.py doc/tests/test_doc_contracts.py` | `0` | `7 + 17 = 24 tests — OK` |
