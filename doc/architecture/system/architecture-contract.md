---
id: ARCH-contract
type: architecture-view
title: "Целевая модель .doc/architecture: хранение, форматы, обновление и CLI"
summary: "Версия: 1.3 — добавлена иерархическая task-conf (типы задач + флоу), конфиг-driven валидация task.json, исследовательская папка research/, детекторы путей и мусора в CLI. CLI/schema реализованы и подтверждены валидатором проекта."
status: accepted
domain: system
related: [MAN-software-factory, ARCH-audit, SYS-simple-factory, DOM-project-knowledge, REG-task-number-registry, VIEW-cli-package, REG-cli-validation-rules]
source_refs:
  - /home/user/doc/config/paths.yaml
  - /home/user/doc/config/task-conf/types/jira-incoming/config.yaml
---

# Целевая модель `.doc/architecture`: хранение, форматы, обновление и CLI

**Версия:** 1.3 — добавлена иерархическая task-conf (типы задач + флоу), конфиг-driven валидация task.json, исследовательская папка research/, детекторы путей и мусора в CLI. CLI/schema реализованы и подтверждены валидатором проекта.
**Статус:** current — проектное решение реализовано, CLI/command surface подтверждено валидатором, task-conf/decomposition/close-policy работают.
**Дата ресёрча:** 2026-11-21.
**Аудит:** [результаты глубокого аудита, сравнительная матрица и остаточные contract gaps](architecture-audit.md).
**Область:** архитектурная документация проекта, её структура, типы артефактов и жизненный цикл; не спецификация всей software factory и не план практического пилота.

> **Короткий вывод.** Хранить архитектурные знания в Markdown в отдельном версионируемом docs-repo под `.doc/architecture/`; группировать документы сначала по системе/домену, а внутри домена — по действительно разным видам артефактов. Применять ISO/IEC/IEEE 42010 как концептуальную основу «интересы и concerns → views», arc42 как проверочный перечень тем, C4 для структуры системы, MADR для существенных решений, Diátaxis только для пользовательских how-to/reference/tutorial/explanation материалов. Контракты API/событий и JSON-схемы не копировать в Markdown: ссылаться на их настоящий источник истины. Агент напрямую правит небольшой Markdown diff в docs-ветке; базовый CLI нужен для точечного чтения, индекса и проверок, а не для обязательного CRUD каждой сущности. Семантику выбирает агент, слияние/approval — человек по принятой политике.

---

## 1. Решения в одном месте

| Область | Выбранное решение | Что сознательно не вводим |
|---|---|---|
| Хранилище | Один canonical docs Git repository; внутри него `.doc/architecture/`. Он отдельный от Git-репозитория продукта, как предполагалось в манифесте. Git даёт версии, branch/diff/review/merge и provenance. | Отдельную docs-платформу, базу данных знаний или вторую копию документации в продуктовых каталогах. |
| Основной формат | Markdown с коротким YAML frontmatter, валидируемым собственной версионируемой JSON Schema. Для переносимости — CommonMark/GFM-профиль, без зависимости от Obsidian-синтаксиса. | Собственный универсальный DSL для всей архитектуры; Markdown, полностью написанный внутри JSON; непроверяемый свободный frontmatter. |
| Организация | Наверху — система; внутри `domains/<domain>/` — сущности, флоу, правила и локальный глоссарий; существенные решения — в общем `decisions/`. | Один монолитный `architecture.md`; папки по каждой комбинации release × feature; отдельный файл на каждый короткий термин или бизнес-правило. |
| Архитектурный охват | Сначала зафиксировать stakeholders/concerns и необходимые views; использовать только views, отвечающие реальным вопросам. arc42 — checklist, не обязательная 12-файловая структура. | Обязательное заполнение всех 12 arc42-разделов, всех C4-уровней или всех UML/BPMN-диаграмм. |
| Сущность | Отдельный Markdown-файл для значимой доменной сущности/агрегата, если у неё есть несколько существенных аспектов или независимый жизненный цикл. Технические DTO/таблицы не документировать поштучно автоматически. | Переписывание полной модели БД/классов в Markdown. |
| Флоу | Файл на значимый пользовательский или межсистемный сценарий; текст/таблица ветвей — источник смысла, диаграмма — полезное представление. BPMN/DMN применять только если содержание и доступный tooling это оправдывают. | Введение самодельного исполняемого workflow-языка или дублирование действующего workflow engine. |
| История | Git commit/PR и ссылки на task/stage — основной след изменений. `base_doc_revision` — Git SHA. Task artifacts сохраняют proposal/evidence. | Ручной changelog/append-only event-log внутри каждого документа, если он дублирует Git и task records. |
| Поиск | Agent-first semantic selection. CLI предоставляет явный index/list/show и буквальный поиск. | Скрытый semantic classifier, fuzzy-выбор canonical документа или автоисправление смысловых связей в CLI. |
| CLI write path | На старте агент/человек правит Markdown обычным файловым patch в docs worktree/ветке, CLI проверяет результат. Типизированный `glossary add` / `flow update` не обязателен. | CLI-команда для каждого типа документа и обязательная маршрутизация любой prose-правки через CLI. |
| Задача | `task.json` — единственный canonical task input. Структура задач регламентируется иерархической `doc/config/task-conf/types/<type>/config.yaml` (поля, allowed_flows, subtask_policy, close_policy) и `doc/config/task-conf/types/<type>/flows/<flow>/config.yaml` (шаги, gate, prompt.md). В задаче предлагаемые docs-изменения идут в `stageN/architecture-delta/`, а не заменяют входной `task.json`. | `task.md` или отдельный hand-authored task document как ещё один источник истины. |
| Агентность | Текущий core — один агент. Агент выбирает смысл, релевантные документы, проектирует содержимое и review-дельту. Человек принимает решения/approval по установленным правилам. CLI детерминирован и не принимает смысловых решений. | Проектирование обязательной multi-agent orchestration или автослияния/публикации. |
| CLI детекторы | `arch docs paths --check` — детектор мусора: выявляет файлы в `doc/` вне `allowed_paths` из `doc/config/paths.yaml`, диагностирует несоответствие frontmatter/типам/статусам. `arch task diagnose <task_key>` — гант-подобная диагностика: тип, флоу, сложность, подзадачи, блокеры закрытия. `arch task close <task_key>` — закрытие только если все подзадачи `phase: completed` (close_policy). | CLI без валидации путей, без детектора мусора, без контроля закрытия задач. |

Эти решения уточняют открытую гипотезу модели хранения из единственного root-манифеста. Сам манифест остаётся единственным файлом манифеста в корне sandbox; его копия в `.doc/architecture` или энциклопедию не создаётся.

---

## 2. Цели, границы и язык статусов

### 2.1 Цели документации

Архитектурная база должна:

1. Дать человеку и агенту краткий путь от системы/домена к нужной сущности, сценарию, правилу, решению или contract.
2. Фиксировать то, что нельзя надёжно восстановить только из кода: границы, назначение, допущения, владельцев concerns, инварианты, намерения, компромиссы, межсистемные сценарии, release-specific поведение.
3. Ссылаться на проверяемые implementation/contracts/tests вместо копирования их содержимого.
4. Изменяться обычным docs-as-code workflow: diff, review, history, branch/merge и локальные проверки. CI/CD и Git-hosted workflow запрещены (см. `MAN-software-factory`, «Запреты в рамках workflow»).
5. Быть пригодной для точечного retrieval. Агент начинает с короткой карты и загружает только документы, связанные с задачей и найденными зависимостями.
6. Разделять подтверждённое текущее состояние, одобренное решение, предложение и нерешённый вопрос.

### 2.2 Не является целью

- Формально заявлять соответствие ISO/IEC/IEEE 42010 только потому, что есть папки и диаграммы.
- Поддерживать параллельно два равноправных описания API, схемы или архитектуры.
- Заставлять каждый проект использовать DDD-термины, BPMN/DMN, C4-картинки, UML, arc42 целиком или одинаковую детализацию.
- Полностью моделировать кодовую базу, все классы, таблицы, endpoints и значения полей в prose.
- Разрешать CLI принимать смысловые решения за агента.
- Измерять экономию/качество через реальный пилот до завершения workflow/contracts и выполнения pilot prerequisites.

### 2.3 Не смешивать три разных статуса

1. **Статус документа:** `status: draft | current | accepted | deprecated | superseded` — lifecycle самого документа. Исполняемый список значений задаёт `doc/config/paths.yaml` (`project.document_statuses`), а JSON Schema и этот раздел обязаны с ним совпадать.
2. **Статус решения:** только для `type: decision`, отдельное `decision_status: proposed | accepted | rejected | deprecated | superseded`; у `superseded` обязателен `superseded_by: ADR-…`.
3. **Статус описываемого объекта:** например, order `pending/confirmed/cancelled`. Это содержимое доменной модели и не равно status metadata документа/решения.

Неутверждённое содержание документа имеет `status: draft`. `accepted` означает, что содержание одобрено (принятый контракт или ADR); `current` — подтверждённое текущее состояние без отдельного акта одобрения. Неутверждённый ADR — `status: current` и `decision_status: proposed`. Proposal/open question явно маркируются; неопределённость (`assumption`, `not verified`) не маскировать под факт. Значения `proposed` и `rejected` принадлежат только `decision_status` и недопустимы как `status` документа.

---

## 3. Основания и применение стандартов/практик

Ни один стандарт не задаёт универсальное дерево папок, которое нужно копировать в этот проект. По официальному описанию ISO/IEC/IEEE 42010:2022 стандарт задаёт требования к структуре и выражению architecture description, но **не определяет формат/носитель, нотацию, инструменты или процесс её создания**. Поэтому ниже выбирается небольшой локальный формат на основании concern/viewpoint, а не заявляется полное соответствие стандарту.

### 3.1 ISO/IEC/IEEE 42010:2022 — каркас описания, не шаблон папок

Использовать понятия:

- **Entity of interest / system** — что именно описывается и где проходит его граница.
- **Stakeholder** — кто имеет существенный интерес.
- **Concern** — какой вопрос/риск/цель архитектура должна объяснить.
- **Viewpoint / view / view component** — по какой принятой конвенции и в каком представлении отвечаем на concern.
- **Correspondence / rationale** — как связаны представления и почему принято важное решение.

Практическое следствие: в `system/overview.md` кратко перечислить цель/границу системы, главные stakeholders и concerns, а затем дать ссылки на views, которые их покрывают. Для малого проекта достаточно небольшой таблицы `Concern → Stakeholder → View/document → Evidence/known gap`. Не нужно конструировать сложный viewpoint registry, пока командный набор viewpoints действительно не переиспользуется.

**Не заявлять conformance** без отдельного gap assessment по полному нормативному тексту и требований проекта/аудита. Официальная карточка ISO 42010:2022 прямо указывает, что standard не задаёт формат или media; public abstract — основание для ориентирования, не замена платному тексту.

### 3.2 arc42 — checklist на полноту, не обязательные 12 файлов

Использовать arc42 как проверку, не забыты ли цели/ограничения, context/scope, solution strategy, building blocks, runtime, deployment, crosscutting concepts, architecture decisions, quality requirements, risks/technical debt и glossary. Содержимое распределять по смысловым файлам и доменам, а не создавать двенадцать пустых разделов.

Для качества записывать только важные, измеримые scenarios: источник/стимул, среда, реакция, измеримый порог. Например, не «система масштабируема», а определённая нагрузка и требуемая latency/throughput/availability, если это реально согласовано. Если метрика неизвестна, указать unresolved decision, не выдумывать число.

### 3.3 C4 — выбрать уровень детализации по вопросу

- **System context**: система, основные люди и внешние системы.
- **Container**: отдельно запускаемые/развёртываемые приложения, сервисы, stores и связи; container в C4 не означает Docker-образ.
- **Component**: важная внутренняя структура одного container — только если это помогает команде решать задачу.
- **Code**: обычно не поддерживать вручную; смотреть код или генерировать по необходимости.
- **Dynamic/deployment/landscape** — дополнительные views только для соответствующих runtime, infrastructure или portfolio concerns.

C4 — обозначение абстракций и диаграмм; он не предписывает инструмент. Официальный сайт явно говорит, что не нужно применять все четыре уровня; для большинства команд достаточно context и container. В нашем проекте Mermaid может быть удобным текстовым носителем диаграммы, но Mermaid сам по себе не делает диаграмму C4-корректной: нужно соблюдать выбранные C4-уровень, элементы, границу и легенду.

### 3.4 MADR / ADR — решение и rationale

Один ADR фиксирует одно существенное архитектурное решение, контекст/вопрос, рассматриваемые реальные варианты, outcome, причины и consequences. Для большинства записей достаточно компактного шаблона; полную таблицу pros/cons добавлять только когда она помогает review. Решение, которое заменило принятое, создаёт новый ADR со ссылкой `supersedes`, а старый сохраняется и получает статус. Текущее состояние архитектуры отражается в актуальных model/view documents, а не подменяется бесконечной лентой ADR.

### 3.5 Diátaxis — только для пользовательского слоя

Diátaxis различает tutorial, how-to, technical reference и explanation по потребности читателя. Это полезно для операционных инструкций, обучения и developer/user docs, но это **не** типы архитектурной модели. Не преобразовывать каждый файл `entities/` или `flows/` в tutorial/how-to. Если в архитектурной базе появится самостоятельная инструкция для человека, поместить её в соответствующий пользовательский раздел/портал, сохраняя ссылку от архитектуры.

### 3.6 Форматы и каноничность

- **Markdown profile:** зафиксировать subset: CommonMark headings/paragraphs/lists/blockquote/fenced code/links + GFM pipe tables; разрешить fenced `mermaid` only if CI can parse it. Не использовать raw HTML, Obsidian `[[wikilink]]`, vault-specific callout/embeds и renderer-specific heading fragments в canonical docs. Связи — обычные relative Markdown file links + stable IDs в тексте. Renderer/parser и версии validator pin-ятся в tooling config; один test fixture проверяет одинаковый рендер. Это проектный markdown profile, не новая спецификация.
- **YAML frontmatter:** YAML 1.2 — язык сериализации, но `--- YAML ---` frontmatter — распространённая конвенция, а не отдельный универсальный стандарт документации. Утвердить собственную JSON Schema для разрешённых полей; парсить безопасным loader, отвергать дубли ключей и неподдерживаемые YAML tags/типы.
- **JSON Schema:** использовать Draft 2020-12 для валидации metadata/index/change-set структур, где это полезно. JSON Schema проверяет форму/ограничения данных, не смысл бизнес-определения.
- **OpenAPI:** если интерфейс HTTP описывается OpenAPI, контрактом остаётся OpenAPI-файл/реестр, валидируемый инструментами проекта; в архитектурной заметке — ссылка, назначение, потребители и решения. На дату ресёрча официальный индекс публикует OAS 3.2.1; выбирать версию по support матрице и валидатору проекта, не мигрировать контракт лишь ради номера.
- **AsyncAPI:** для message-driven API рассматривать спецификацию AsyncAPI; её файл — источник protocol/channel/message contract, а не копия в narrative документах.
- **Схемы данных:** использовать уже существующие JSON Schema/Protobuf/Avro/SQL/ORM definitions как источник технических деталей. Архитектурный текст описывает доменную семантику и направляет к ним.
- **Диаграммы:** предпочитать текстовые исходники, которые можно review и валидировать. Диаграмма, являющаяся единственным источником сложной бизнес-логики, — риск: добавить явное пояснение/path records либо использовать подходящую спецификацию процесса.

### 3.7 Spec-Driven Development: стабильная модель vs дельта задачи

Сравнение OpenSpec и Spec Kit относится к **workflow изменений**, а не к выбору стандарта архитектурных диаграмм. Их полезный общий принцип — не смешивать «что система сейчас должна делать», «что предлагается изменить», «как реализовать» и «какие шаги выполнить».

- **OpenSpec** хранит текущие capability specs отдельно от change proposals. Proposal объясняет why/what/impact; delta spec фиксирует ADDED/MODIFIED/REMOVED behavior требования и WHEN/THEN сценарии; design и tasks включаются, когда нужны; после реализации/проверки дельты синхронизируются/архивируются в main specs. CLI структурно проверяет артефакты. Мы перенимаем разделение current state/change delta и стабильную capability boundary, но не копируем OpenSpec командный runtime, схему папок, весь набор artifact names или его CLI. Вместо параллельной change description используем существующие `task.json` + `stageN/architecture-delta/` + stage plan/evidence.
- **GitHub Spec Kit** разделяет project constitution, функциональные requirements/specification, clarification, technical plan (с optional data-model/contracts/research/quickstart), dependency-ordered tasks и optional checklist/analyze gates. Specification фокусируется на what/why; plan — на how. Мы перенимаем явную проверку ambiguity, testable acceptance scenarios и cross-artifact consistency. Но Spec Kit tasks.md не становится canonical task input: у нас `task.json` остаётся единственным canonical intake, а stage plan и runtime verification artifacts остаются в уже определённом task contract.

**Архитектурная модель** должна сохранять одобренное долговременное знание: system/domain/capability/entity/data/flow/interface/decision views. **Task delta** временно описывает, как эта модель должна измениться в рамках задачи. После approval и проверки accepted delta обновляет current-state документ; необработанная proposal не смешивается с current state.

Рекомендуемая последовательность для задачи:

```text
task.json
  → targeted clarification (только если блокирует решение)
  → behavior delta на затронутые capability specs (только если меняется требуемое поведение)
  → design/architecture delta (если изменение архитектурно znacimo)
  → stage plan (проверяемые действия, текущий формат task workflow)
  → implementation + tests/evidence
  → consistency review + required approvals
  → sync accepted deltas в canonical architecture docs
```

Этапы не являются жёсткой линейной бюрократией: мелкий bug/refactor может обойтись без architecture delta/spec update; изменение требований возвращает на clarification/specification, не требует додумывать её в design. Capability specs добавляются и поддерживаются только для устойчивых behavior boundaries, которые реально нужны нескольким будущим задачам.

---

## 4. Размещение и дерево

### 4.1 Физический корень

Рекомендованный физический вариант — **один отдельный Git repository для проектной архитектурной документации** (URL/host пока является deploy-конфигурацией). Его корень содержит `.doc/architecture/`. Продуктовый Git repository может ссылаться на этот repo/commit; он не хранит вторую редактируемую копию.

Это даёт обычное version control/review и поддерживает договорённость, что architecture store не находится внутри product repository. Локальная копия этого docs-repo в sandbox — обычный worktree. Не принимать решения о конкретном host/доступе/backup без уточнения инфраструктуры. Если отдельный docs-repo организационно невозможен, временный локальный корень не считать canonical shared store; сначала утвердить другое versioned размещение.

### 4.2 Рекомендуемое дерево

```text
<architecture-docs-repo>/
├── README.md                         # краткий human entrypoint: цель, правила, команды
└── .doc/
    └── architecture/
        ├── README.md                 # scope, naming, ссылки на ключевые views
        ├── index.json               # generated machine index; не редактировать вручную
        ├── schemas/
        │   ├── document.schema.json # JSON Schema для общего frontmatter/envelope
        │   └── index.schema.json    # JSON Schema для generated index.json
        ├── system/
        │   ├── overview.md           # scope, stakeholders, concerns, views map
        │   ├── context.md            # C4 System Context + external parties/boundaries
        │   ├── containers.md         # C4 Container view, only when useful
        │   ├── data.md               # logical data ownership/flows/classification, if material
        │   ├── quality.md            # measurable quality scenarios and constraints
        │   ├── security.md           # trust boundaries/threats/control refs, if material
        │   ├── deployment.md         # deployment/operation views, when they answer concerns
        │   ├── verification.md       # test/evidence mapping, if not covered elsewhere
        │   ├── constraints-risks.md  # only material constraints/risks/debt
        │   └── cross-cutting/        # only genuinely cross-domain concepts
        ├── domains/
        │   └── <domain>/
        │       ├── README.md         # optional curated domain entrypoint
        │       ├── glossary.md       # domain-scoped definitions; not one file per word
        │       ├── capabilities/     # durable behavior contract per meaningful capability
        │       │   └── CAP-<domain>-<slug>.md
        │       ├── rules.md          # grouped rules with stable IDs only when referenced
        │       ├── data.md           # domain data concepts/ownership, when not in entities
        │       ├── entities/
        │       │   └── ENT-<domain>-<slug>.md
        │       ├── flows/
        │       │   └── FLOW-<domain>-<slug>.md
        │       └── integrations/     # optional context pages that reference contracts
        │           └── INT-<domain>-<slug>.md
        └── decisions/
            └── ADR-0001-<short-title>.md
```

**Не считать каждую строку дерева обязательной.** `containers.md`, `deployment.md`, `security.md`, `cross-cutting/` или domain README создаются, когда есть материал и потребитель. Пустые template files не создавать. `index.json` и schema — инфраструктурные файлы документационной базы, а не отдельная содержательная архитектура.

### 4.3 Почему домен прежде типа

Сначала domain-контекст помогает агенту и человеку загрузить связанный ubiquitous language, entities, flows и rules, а не искать их в несвязанных общих папках. Внутренние подпапки по виду артефакта дают привычную точку поиска и позволяют валидировать type. Сквозные системные views и решения остаются наверху, но у них есть явные domain/ID links.

Если проект невелик и содержит мало документов, можно на старте держать все содержимое домена прямо в его `README.md`; выделять файл/папку при появлении независимого жизненного цикла, объёма или точки ссылок. Не дробить ради формальной чистоты.

### 4.4 Идентификаторы и имена

- `id` стабилен при переименовании заголовка и уникален в пределах всего docs-root.
- Практичная читаемая форма: `ENT-orders-order`, `FLOW-orders-checkout`, `ADR-0007-use-outbox`. Префиксы — локальная договорённость, а не внешний стандарт. Для кратких правил — например `BR-orders-014` только если rule cross-reference нужен в flow/test/change history.
- Имя файла обычно совпадает с `id` и имеет `.md`; заголовок может меняться без переименования файла. Переезд/ID rename делается явным Git move + исправлением всех refs.
- Не выдавать новый ID за вывод из названия автоматически. CLI может проверить уникальность и соответствие filename/ID; выбор подходящего domain/смысла — задача агента/владельца.

---

## 5. Что хранится и что не хранится

### 5.1 Системный уровень

`system/overview.md` — единственная короткая стартовая карта, не полное описание. Включает:

- идентификацию объекта описания, цель, scope/non-goals и внешнюю границу;
- главных stakeholders и их architectural concerns;
- таблицу `concern → view/document → stakeholder/audience → known gap`;
- короткую solution strategy и важные constraints (или ссылки на отдельные ADR/quality docs);
- главные system/domain links, внешние системы и contract references;
- unresolved questions и владельца/следующее действие, если он известен.

`context.md` отвечает «кто/что взаимодействует с системой и где интерфейсная граница». `containers.md` — «какие отдельно запускаемые/развёртываемые блоки и stores есть и как они связаны». Component/deployment/runtime views — добавлять по concern, а не автоматически.

`quality.md` фиксирует небольшое число приоритетных, измеримых quality scenarios и важные constraints. `security.md` фиксирует архитектурные trust boundaries, principals, protected assets и links на threat-model/controls; не копирует секреты, credentials или полные результаты сканеров. Подробные операционные процедуры — отдельные how-to/runbook, не смешивать с архитектурным объяснением.

### 5.2 Domain-level документация

#### Domain overview / glossary

Для каждого bounded context/реальной области — краткая ответственность и граница, владельцы/consumers если известны, upstream/downstream domains, термины с контекстным значением и aliases. Один термин, означающий разное в двух domains, получает domain-qualified definition. Небольшой глоссарий — раздел `README.md`, не отдельный документ на слово.

#### Entity document

Создавать файл для доменной сущности/aggregate/value object только если это помогает объяснить значимую модель; термины и простые DTO можно перечислить в glossary/contract. Рекомендуемые разделы:

1. **Назначение и граница:** что это представляет в языке конкретного домена; чего не представляет.
2. **Identity:** бизнес-идентичность/правило уникальности, если существенно.
3. **State/lifecycle:** существенные состояния, события/разрешённые переходы, конечные/недопустимые состояния.
4. **Invariants:** утверждения, которые должны оставаться истинными; ссылка на rule/test IDs.
5. **Attributes:** только смысловые/архитектурно важные данные, ограничения, nullable/default/units/sensitivity и настоящий owner/source. Для полного технического field list — ссылка на schema/contract/database definition.
6. **Relationships:** цель, направление/cardinality и ownership; не заменять неявным расположением файла.
7. **Behavior/flows/rules:** ссылки на связанные flows и business rule IDs.
8. **Examples:** минимальные валидный и, если важно, невалидный пример; пометка fixture/code/test source, если пример должен оставаться исполнимым.
9. **Evidence/refs:** code/schema/API/test paths или IDs; известные gaps и вопросы.

Не записывать список всех полей таблиц, который автоматически дублирует OpenAPI/ORM/schema; не придумывать свойства, relations или state, которых нет в подтверждённых source/owner decision.

#### Flow document

Создавать файл для значимого end-to-end или cross-system сценария: trigger, actor, preconditions, result/postconditions, affected entities, boundaries и ссылки на rules/contracts. Фиксировать happy path и применимые failure/alternate paths: auth/validation отказ, external timeout, duplicate/retry/idempotency, частичный успех/compensation — только если они реальны для этого сценария.

Для flow, по которому надо связать ветви с тестами/releases, использовать небольшую таблицу `path_id | guard/condition | action/side effect | outcome/next state | failure/retry/compensation | test ref`. Полный default/else и известные конфликтующие guards должны быть явными. Таблица/пояснения несут смысл; Mermaid-диаграмма прилагается, если реально улучшает чтение, и помечается как visualization. Если простая диаграмма исчерпывающе объясняет простой процесс и path-level traceability не нужна — не добавлять таблицу ради таблицы.

Не создавать кастомный YAML workflow graph/исполняемый DSL для описания всех flows. Если сам процесс уже существует как BPMN/DMN/state machine/workflow engine spec и у команды есть проверяющие инструменты, тот файл — source of truth, а Markdown содержит rationale, границы и ссылки. BPMN уместен для сложного бизнес-процесса с participants/events/gateways; DMN — для существенной decision logic/decision table. Простая линейная процедура не требует стандарта ради стандарта.

#### Business rules

Группировать связанные правила в `rules.md` по domain/process/topic. Стабильные `BR-*` IDs выдавать только rules, на которые реально ссылаются flows/tests/tasks/decisions. Записывать условие/входные факты → outcome/action, scope, precedence/default, исключения и release applicability если они отличаются. Отдельный файл на каждое короткое правило не нужен. Сложная таблица решений должна ссылаться на свою каноническую таблицу/DMN; не иметь две редактируемые версии.

### 5.3 Architecture decisions

`decisions/ADR-NNNN-<slug>.md`, по одному архитектурно значимому решению на файл. Рекомендуемый минимальный шаблон:

```markdown
---
id: ADR-0007
type: decision
status: current
decision_status: proposed
---

# Use transactional outbox for event publication

## Context and problem
## Decision drivers
## Considered options
## Decision outcome
## Consequences
## Confirmation / how to verify
## Links
```

Для малозначимого выбора не создавать ADR без пользы; если decision materially impacts architecture, compatibility, security, data, deployment or quality trade-off — фиксировать rationale. Непринятый ADR не описывать как реализованный current state. После acceptance обновить актуальную view/document и пометить ADR. Изменение решения — новый ADR со ссылкой на прежний, не тихая перепись rationale.

### 5.4 Contracts и другие источники истины

Реальный contract/source определяется тем, что команда уже поддерживает и валидирует: OpenAPI, AsyncAPI, JSON Schema, Protobuf, Avro, SQL migrations, configuration, IaC, code/tests либо owner-approved policy. Архитектурная заметка содержит:

- зачем contract существует и кто потребители;
- repo/path/URL + version/ref, нужный для воспроизведения;
- какие архитектурные ограничения или решения следуют из него;
- известные несовпадения/границы и связанный test/owner;
- при необходимости — конкретную operation/schema pointer, а не скопированный длинный fragment.

Если source внешней интеграции не pin-ится в Git, фиксировать проверяемую URL/версию/дату доступа только там, где этого требует change/provenance; не считать динамический URL неизменным evidence.

### 5.5 Реестр типов архитектурных артефактов и форматы

**Критически важный вывод аудита:** предыдущая версия описывала намерения и поля ряда документов, но не задавала полные форматы для capability/spec, data, glossary, interfaces/integrations, quality, security, deployment/operations, constraints/risks и verification. Поэтому её нельзя было считать «все форматы описаны» или implementation-ready. Ниже — обязательный минимальный contract для тех типов, которые вообще создаются. Наличие формата не означает, что нужно создать файл для каждого типа.

Исполняемый список допустимых `type` — `doc/config/paths.yaml` (`project.document_types`); эта таблица обязана содержать ровно те же типы и строку формата для каждого. Для типов с проверяемой структурой тела есть JSON Schema в `doc/architecture/schemas/bodies/`; остальные помечены `prose-only` и проверяются ревью, а не схемой. Согласованность списка, таблицы, body-схем и статусов проверяет `doc/tests/test_doc_type_registry.py`.

| Type | Обязателен? | Канонический формат и назначение |
|---|---|---|
| `system` | Да, один на систему | Markdown: назначение, граница области, архитектурные точки зрения, домены. Body-схема `system.json`. |
| `system-overview` | Зарезервирован: создаётся при появлении concern «обзор системы для стейкхолдеров» | prose-only Markdown: identity/scope, stakeholders/concerns map, links to views, source/evidence, open gaps. |
| `system-context` | Для материальной внешней границы системы | Markdown: актёры и внешние системы, информационный поток, trust boundary. Body-схема `system-context.json`. |
| `component-view` | По concern «структура компонентов» | Markdown: таблица компонентов с ответственностью и границами. Body-схема `component-view.json`. |
| `architecture-view` | По concern | prose-only Markdown + C4/Mermaid/таблица: convention/level/scope/audience/legend/sources/known issues. |
| `data-view` | Для материальных границ данных | Markdown: таблица записей с форматом, властью и жизненным циклом; политика форматов. Body-схема `data-view.json`. |
| `domain` | По каждому реальному bounded context | Markdown: responsibility, boundary, owner/consumers, relationships to other domains, terms, key capabilities. Body-схема `domain.json`. |
| `capability` | По крупной возможности домена | Markdown: результат, не цели и нерешённое. Body-схема `capability.json`. |
| `capability-spec` | Если есть устойчивое поведение, важное для дальнейших задач | Markdown: Purpose, Scope, normative Requirements and testable WHEN/THEN Scenarios, related flow/entity/contract/test references. Body-схема `capability-spec.json`. |
| `entity` | По необходимости (`data-concept` — синоним) | Markdown: meaning, identity, lifecycle/invariants/relationships, significant attributes, data ownership/classification, authoritative schema ref. Body-схема `entity.json`. |
| `glossary` | Да, но может быть частью domain overview | Markdown table/headings: stable term ID, preferred term, domain-context definition, aliases, non-preferred terms, example, technical mapping, refs. Body-схема `glossary.json`. |
| `rule-set` | Если правила не помещаются/не читаются в capability/entity docs | Markdown table/sections: stable ID if cross-referenced, applicability, condition → outcome, precedence/default, exceptions, owner/evidence. Body-схема `rule-set.json`. |
| `flow` | Для значимого behavior/runtime path | Markdown: trigger/actors/preconditions/outcomes, steps/guards/failure paths, side effects and references; optional diagram. Body-схема `flow.json`. |
| `integration` | Зарезервирован: создаётся при появлении material external or cross-domain contract | prose-only Markdown: producer/consumer, direction, purpose, protocol, contract pointer/version, identity/security, compatibility/failure behavior, owner/tests. |
| `cross-cutting-concept` | Зарезервирован: создаётся, когда паттерн/ограничение действует в нескольких domains | prose-only Markdown: purpose, scope, invariant/pattern, allowed variation, exceptions, affected views and source refs. |
| `quality-attributes` | По согласованным architecture quality concerns | Markdown: таблица «атрибут → сценарий/реакция → открытая мера или решение». Body-схема `quality-attributes.json`. |
| `quality-view` | Зарезервирован: создаётся, когда нужны сценарные записи качества с measure/evidence | prose-only Markdown scenario records: source, stimulus, environment, response, measure, validation/evidence, affected views/decisions. |
| `security-view` | If security/trust boundary is architectural | Markdown threat/control records; never store credentials/secrets. Body-схема `security-view.json`. |
| `deployment-operations-view` | Зарезервирован: создаётся, когда deployment/operability становятся материальным concern | prose-only Markdown + optional C4 deployment diagram/IaC refs; topology, failure/restore/observability/runbook refs. |
| `constraints-risks` | Только значимые/неочевидные constraints or risks | Markdown table with stable IDs when referenced, effect, owner, mitigation, status and review trigger. Body-схема `constraints-risks.json`. |
| `decision` | Для significant architecture decisions | One MADR-style ADR per decision; decision status remains distinct from doc status. Body-схема `decision.json`. |
| `verification-map` | Зарезервирован: создаётся, если acceptance/test mapping нельзя вывести из кода и CI | prose-only Markdown table mapping capability/requirement/flow path → automated/manual test/evidence; tests remain in product repo. |
| `testing-spec` | Для стратегии тестирования | prose-only Markdown: цель и охват, уровни, unit/integration/E2E, фикстуры, команды. |
| `implementation-spec` | Для технической спецификации реализации | prose-only Markdown: структура пакета, модули, контракты вывода, ссылки на тесты. |
| `runbook` | Для операционных процедур | prose-only Markdown: диагностика, восстановление после сбоев, откат, команды. |
| `examples` | Для справочных примеров | prose-only Markdown: примеры входов и ожидаемого вывода, привязанные к действующим командам. |

#### A. System overview и architecture view

```markdown
# <System or view title>

## Purpose and scope
## Stakeholders and concerns
| Concern ID | Concern/question | Stakeholder | View/document that addresses it | Evidence / known gap |
## Boundary and context
## Selected view(s) and conventions
## Key findings / architecture constraints
## Related domains, capabilities, contracts and ADRs
## Open questions / known issues
## Sources and evidence
```

For a C4 context/container view the diagram must state its scope/level and a legend; a companion table may identify each person/system/container, responsibility, owner and interface. Add the diagram only if it says something the table/text cannot say more clearly. Do not label a view C4 if it does not follow the relevant abstraction semantics.

#### B. Domain и domain glossary

Domain overview format:

```markdown
# <Domain name>

## Purpose and boundary
## Owner / consumers
## Upstream and downstream domains
## Capabilities
## Core data concepts
## Cross-domain rules and invariants
## Glossary
## Interfaces and flows
## Related decisions / open questions
```

Glossary entry format inside a domain glossary (not one file per term):

```markdown
### <Preferred term> — `TERM-<domain>-<slug>`

- **ID:** TERM-<domain>-<slug>
- **Definition:** One domain-specific, concise meaning.
- **Aliases:** Other accepted names, or `none`.
- **Avoid:** Known misleading/obsolete homonyms, if any.
- **Example / non-example:** Only if needed to disambiguate.
- **Technical mapping:** Code/schema/API identifiers with source refs; omit if none.
- **Related:** Other term/domain/entity/capability IDs.
```

В ссылках на term entry в первой версии использовать обычную ссылку на файл glossary без heading fragment и видимый stable ID; Markdown heading anchors различаются между renderer implementations. CLI проверяет, что ссылка на файл существует, а referenced `TERM-*` ID уникален в каталоге. Для небольшого glossary ID хранится в heading/body, не в per-term frontmatter; это правило входит в schema/lint profile.

#### C. Durable capability/spec

This fills the missing behavior contract between product intent and architecture. Use a durable capability boundary (not a ticket/implementation task) that can own behavior over time. Keep the current, agreed contract here; a task proposes a delta against it.

```markdown
# <Capability>

## Purpose
## Scope and exclusions
## Actors and preconditions
## Requirements
### Requirement: <stable requirement ID and one SHALL behavior>
The system SHALL ...
#### Scenario: <observable case>
- **WHEN** ...
- **THEN** ...
## Important domain rules / data effects
## Interfaces and linked flows
## Acceptance / verification refs
## Open questions / known limitations
## Sources / rationale
```

Requirements describe **what** externally observable behavior is required, not internal implementation. Each requirement states one behavior; scenarios are concrete and testable, with expected observable outcomes. Unknowns are marked `NEEDS CLARIFICATION` (or an equivalent explicit unresolved list) and block design where they affect correctness. Do not introduce requirements solely to satisfy tooling. If no behavior changes (pure refactor/tooling/docs), no capability delta is required.

#### D. Entity / data concept / data view

Use an entity file only for a concept with meaningful identity/lifecycle/invariants. Use `data.md` for a cross-domain data map; use `data-concept` for a concept that is not an entity. Keep physical/serialized field details in schema/contract source. Recommended entity template:

```markdown
# <Entity>

## Domain meaning and boundary
## Identity and lifecycle
## Invariants
## Significant attributes
| Name | Domain meaning | Type/constraint | Nullable/default | Sensitivity | Authoritative source |
## Relationships and cardinality
## Ownership and lifecycle of data
## State transitions / events
## Capabilities, rules and flows
## Schema / code / tests
## Open questions / evidence
```

A `system/data.md` data architecture view, only when relevant, records:

- data domains and authoritative source/owner per important concept;
- system/component responsible for create/read/update/delete and permitted consumers;
- important cross-boundary data flows and classifications;
- consistency/transaction/eventual consistency assumptions;
- retention/deletion/backup/restore/lineage obligations when applicable;
- schema evolution, migration and backward-compatibility constraints;
- refs to actual database migrations, schema files, event contracts and tests.

Do not put personal data, live credentials, production sample records or secrets in examples. Avoid copying entire database catalogs into the architecture store.

#### E. Flow и business rule

Flow template:

```markdown
# <Flow>

## Purpose and capability
## Trigger, actors and participating systems
## Preconditions and authorization
## Successful outcome / postconditions
## Main and alternate paths
| Path/step ID | Guard / event | Actor | Action and side effect | Outcome / next state | Failure/retry/compensation | Test ref |
## Idempotency, consistency and timing (when relevant)
## Data/entities/rules/contracts touched
## Diagram (optional; explicitly a view of the path records)
## Known gaps and source refs
```

Do not require all columns when they do not apply, but use a fixed header/profile per flow format so the agent and validator can parse it. Requirements under capability own externally visible behavior; flow gives the runtime explanation. Avoid conflicting copies: put each normative rule once and link it elsewhere.

Business-rule row format:

```markdown
| ID | Applies when / inputs | Outcome / action | Precedence/default | Exceptions | Release applicability | Owner / decision | Test/evidence |
```

If a rule depends on a complex set of conditions, provide a decision table with complete default/no-match and conflict policy, or use DMN if the project can review/validate it. Do not invent a per-rule file structure.

#### F. Integration и contract reference

```markdown
# <Integration name>

## Purpose and boundary
## Producer / consumer / direction
## Protocol and operation/channel
## Authoritative contract
| Kind | Repository/path/URL | Version or ref | Operation/schema pointer | Validator |
## Authentication, authorization and data classification
## Delivery / ordering / idempotency / compatibility assumptions
## Timeouts, retry, failure and recovery behavior
## Ownership, dependencies and change/consumer impact
## Related flows, requirements, tests and ADRs
```

The actual OpenAPI/AsyncAPI/schema/IDL is the normative interface contract; the Markdown reference is explanatory/architectural, not a second contract. A missing or unreachable contract is an explicit gap, not a reason to invent a schema in the summary.

#### F2. Cross-cutting concept

```markdown
# <Concept or pattern>

## Purpose and concerns addressed
## Scope and applicability
## Invariant / selected approach
## Permitted variation and explicit exceptions
## Affected domains, views, capabilities and decisions
## Evidence / source refs / unresolved questions
```

Create this only for a genuinely shared concept (for example, identity propagation or error handling) whose reuse helps prevent cross-domain inconsistency. Do not restate every domain's implementation details here.

#### G. Quality, security, constraints and risks

Quality scenario format:

```markdown
### QAS-<domain>-<number>: <quality concern>
- **Source/stakeholder:**
- **Stimulus:**
- **Environment:**
- **Response:**
- **Measure/threshold:** (approved value or `NEEDS CLARIFICATION`)
- **Verification/evidence:** test, SLO, benchmark or review ref
- **Affected view/decision:**
```

Security/threat record format:

```markdown
### THR-<domain>-<number>: <threat or abuse case>
- **Asset / data:**
- **Actor / capability:**
- **Entry point / trust boundary:**
- **Threat / misuse scenario:**
- **Impact:**
- **Preventive/detective controls:**
- **Residual risk / exception owner:**
- **Verification / evidence:**
- **Related flows, contracts and ADRs:**
```

Constraint/risk register row:

```markdown
| ID | Type (constraint/risk/debt) | Statement and scope | Effect if violated | Mitigation / decision | Owner | Status / review trigger | Evidence |
```

Only architecturally relevant constraints/risks belong here. If there is a formal threat-model, risk register or compliance system, link it as the source of truth rather than maintaining two versions.

#### H. Deployment и operations view

```markdown
# <Deployment/operations concern>

## Scope and environments
## Runtime units and placement (diagram/table; cite IaC source)
## Network/trust boundaries and dependencies
## Scaling, availability and failure assumptions
## Backup/restore and recovery objectives (only agreed values)
## Observability: key signals, SLO/alert references
## Operational ownership and runbooks
## Deployment/migration/rollback constraints
## Sources: IaC, config, локальные проверки, dashboards, runbooks, tests
```

Do not copy live values/secrets from configuration. Treat `deployment.md` as a view over the IaC/config source; keep step-by-step human action in a runbook/how-to.

#### I. Verification map

```markdown
| Contract/requirement/path ID | Expected observable behavior | Test ID or suite | Location/command | Evidence location | Status/waiver owner |
```

This is an index of assurance links, not a replacement for executable tests or recorded local verification artifacts. `not run`/unknown is not pass. Add the map only when links cannot be discovered reliably from the test harness and stable IDs.

#### J. Task/stage architecture delta

OpenSpec's useful pattern is to make a change proposal an explicit **delta from current specs**, then merge it into current-state specs after implementation/verification. Use that principle without importing its CLI, artifact tree, or creating a second task description. In this project the delta stays in `stageN/architecture-delta/`, references the canonical architecture doc and task, and does not replace `task.json`.

For each canonical document affected, use one small Markdown change record with YAML envelope:

```yaml
---
change_id: <stable task-stage-document change key>
canonical_doc_id: FLOW-orders-checkout
operation: MODIFIED # ADDED | MODIFIED | REMOVED | RENAMED
base_doc_revision: <docs-repo Git SHA>
target_release: <configured release ID, or omit if common>
task_ref: <source-aware task key from task.json>
stage_id: stage1
status: proposed
related_ids: [CAP-orders-checkout, ENT-orders-order]
evidence_refs: [<acceptance/test/decision refs>]
---

## Why / evidence
## Proposed content
## Compatibility, impact and unresolved questions
```

`MODIFIED` carries the entire replacement of only the addressed stable section/block, with enough context to review; it does not copy unchanged pages. `REMOVED` gives reason and migration/consumer impact. `RENAMED` identifies old→new ID and all refs to update. If several IDs in one file change, separate records can share one compact diff. Apply only after the required review; store committed result under canonical docs and preserve task-stage delta for provenance.

#### K. Change checklist / consistency analysis

Inspired by Spec Kit's optional clarify/checklist/analyze gates: before implementation, check requirements clarity, boundary/scope, scenarios and edge cases, internal consistency across capability ↔ flow ↔ data ↔ contracts ↔ tests, and compliance with project principles. This is a reviewer/agent checklist, not an extra mandatory canonical document per task. Record its result/evidence in the existing stage verification artifact. Unresolved requirement ambiguity goes back to clarification; design inconsistency goes back to design; do not paper over it by adding boilerplate.

---

## 6. Metadata, schema и индекс

### 6.1 Минимальный frontmatter

```yaml
---
id: ENT-orders-order
type: entity
title: Order
summary: "Доменный заказ; загружать при изменении checkout, lifecycle, order invariants или связанных контрактов."
domain: orders
status: current
related:
  - FLOW-orders-checkout
source_refs:
  - kind: code
    repo: product
    path: src/orders/
  - kind: contract
    repo: product
    path: schemas/order.json
    pointer: /properties/status
---
```

**Минимальные обязательные поля:**

- `id` — стабильный уникальный ID.
- `type` — из зарегистрированного конечного набора `doc/config/paths.yaml` (`project.document_types`); полный перечень, формат и условие применения каждого типа — в §5.5. Создавать такой документ/type только при наличии concern и потребителя; не добавлять новые types из-за отдельной команды и не оставлять объявленный тип без строки формата.
- `title` — человекочитаемое имя.
- `summary` — короткий load-when/зачем читать, не просто повтор заголовка.
- `status` — ограниченный enum документа.
- `domain` — для domain-bound docs; системные документы могут иметь `domain: system`.

**Опциональные поля — только если нужны:** `related` stable IDs; `source_refs` typed repository/path/symbol/contract/test references; `owner` или `reviewer` если определены в governance; `applies_to` release IDs только когда реальное поведение меняется по release; `last_verified` только при существующем процессе ручной semantic verification. Не требовать `tags`, `maxAgeDays`, `last_verified`, `upstream_commit`, `updated_at` для каждого файла без потребителя. Git commit уже даёт дату изменения; механически проставленная дата не доказывает свежесть смысла.

`source_refs` — относительные, структурированные ссылки: `kind` + `repo` alias + repo-relative `path`, optionally `symbol` или schema `pointer`; для внешнего source — `url`. Не использовать local absolute path. Текущие canonical docs обычно ссылаются на **живой location** без `revision`; immutable evidence в task/scanner record pin-ится к Git commit (`revision`, full SHA-1/SHA-256 form supported by repo). Не смешивать stable location и evidence snapshot.

### 6.2 Schema policy

- Хранить одну общую schema для envelope плюс `if/then` constraints по `type`; type-specific body — Markdown и review, не пытаться полностью моделировать prose.
- Пинить `$schema` на JSON Schema Draft 2020-12 и валидатор в lock/config проекта.
- `additionalProperties: false` использовать на строгой metadata-оболочке, если расширение через review/schema update предусмотрено; не скрывать опечатки в новых полях. Существующие optional fields расширять осознанно.
- Требовать уникальность `id`, `id`/filename match, разрешённые status/type, относительные ссылки и корректную сериализацию. Значения дат/идентификаторов — простые строки с явным форматом; не полагаться на YAML implicit type coercion.
- Schema не доказывает, что entity description корректен, flow покрывает требование или решение одобрено.
- `status` относится к document lifecycle; `decision_status` обязателен только для `decision`. При deprecated/superseded значении требовать replacement/reason по type-specific validation.

**Draft generic schema (envelope, JSON Schema 2020-12).** Исполняемые источники истины — `doc/config/paths.yaml` (наборы `document_types`/`document_statuses`) и `doc/architecture/schemas/document.schema.json`; фрагмент ниже должен оставаться с ними синхронным:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:architecture-docs:document.schema.json",
  "title": "Architecture document frontmatter",
  "type": "object",
  "required": ["id", "type", "title", "summary", "status"],
  "properties": {
    "id": {"type": "string", "minLength": 3, "maxLength": 96, "pattern": "^[A-Za-z][A-Za-z0-9._:-]*$"},
    "type": {
      "enum": ["system", "system-overview", "system-context", "component-view", "architecture-view", "data-view", "domain", "capability", "capability-spec", "entity", "glossary", "rule-set", "flow", "integration", "cross-cutting-concept", "quality-attributes", "quality-view", "security-view", "deployment-operations-view", "constraints-risks", "decision", "verification-map", "testing-spec", "implementation-spec", "runbook", "examples"]
    },
    "title": {"type": "string", "minLength": 1},
    "summary": {"type": "string", "minLength": 1},
    "status": {"enum": ["draft", "current", "accepted", "deprecated", "superseded"]},
    "decision_status": {"enum": ["proposed", "accepted", "rejected", "deprecated", "superseded"]},
    "domain": {"type": "string", "minLength": 1},
    "owner": {"type": "string", "minLength": 1},
    "superseded_by": {"type": "string", "minLength": 3},
    "related": {"type": "array", "uniqueItems": true, "items": {"type": "string", "minLength": 3}},
    "source_refs": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["kind"],
        "properties": {
          "kind": {"enum": ["code", "contract", "test", "task", "external"]},
          "repo": {"type": "string", "minLength": 1},
          "path": {"type": "string", "minLength": 1},
          "symbol": {"type": "string", "minLength": 1},
          "pointer": {"type": "string", "minLength": 1},
          "revision": {"type": "string", "pattern": "^[0-9a-fA-F]{40}([0-9a-fA-F]{24})?$"},
          "url": {"type": "string", "format": "uri"}
        },
        "additionalProperties": false,
        "allOf": [
          {
            "if": {"properties": {"kind": {"enum": ["code", "test"]}}, "required": ["kind"]},
            "then": {"required": ["repo", "path"]}
          },
          {
            "if": {"properties": {"kind": {"enum": ["contract", "task"]}}, "required": ["kind"]},
            "then": {"anyOf": [{"required": ["url"]}, {"required": ["repo", "path"]}]}
          },
          {
            "if": {"properties": {"kind": {"const": "external"}}, "required": ["kind"]},
            "then": {"required": ["url"]}
          }
        ]
      }
    },
    "applies_to": {"type": "array", "uniqueItems": true, "items": {"type": "string", "minLength": 1}}
  },
  "additionalProperties": false,
  "allOf": [
    {
      "if": {"properties": {"type": {"const": "decision"}}, "required": ["type"]},
      "then": {"required": ["decision_status"]}
    },
    {
      "if": {"properties": {"type": {"enum": ["domain", "capability-spec", "glossary", "entity", "data-view", "flow", "rule-set", "integration"]}}, "required": ["type"]},
      "then": {"required": ["domain"]}
    },
    {
      "if": {"properties": {"status": {"const": "superseded"}}, "required": ["status"]},
      "then": {"required": ["superseded_by"]}
    },
    {
      "if": {"properties": {"decision_status": {"const": "superseded"}}, "required": ["decision_status"]},
      "then": {"required": ["superseded_by"]}
    }
  ]
}
```

Это schema draft для review, не утверждённая исполняемая реализация и не замена type-specific content templates. Перед кодированием нужно проверить выбранным Draft 2020-12 validator и добавить fixtures для каждого type, conditional branch, unknown property, duplicate ID/path, parse failure. `additionalProperties: false` значит новый metadata field требует versioned schema/template update.

### 6.3 Индекс

`index.json` — generated machine view frontmatter, не отдельный источник истины. Минимальная запись: `id`, `type`, `title`, `summary`, `domain`, `status`, relative `path`, `related`, typed `source_refs`, `applies_to` когда задан.

```json
{
  "index_schema_version": 1,
  "documents": [
    {
      "id": "ENT-orders-order",
      "type": "entity",
      "title": "Order",
      "summary": "Domain order, lifecycle and invariants; load for checkout or order-state changes.",
      "domain": "orders",
      "status": "current",
      "path": "domains/orders/entities/ENT-orders-order.md",
      "related": ["CAP-orders-checkout", "FLOW-orders-checkout"],
      "source_refs": [
        {"kind": "code", "repo": "product", "path": "src/orders/"},
        {"kind": "contract", "repo": "product", "path": "schemas/order.json", "pointer": "/properties/status"}
      ]
    }
  ]
}
```

Stable JSON shape is in `schemas/index.schema.json` (or combined with doc schema if no separate validator is needed); this generated example is not hand-maintained. Include `applies_to` only when specified in the source document.

Правила:

- Пересобирать детерминированно; сортировка и сериализация стабильны, timestamps/build machine-specific paths в output не включать.
- Хранить в docs-repo или генерировать/обновлять так, чтобы доступный агенту index не отставал от source docs. Generated файл коммитится, а свежесть проверяется локально: `arch index check` и `bash doc/tests/run.sh --gate` падают при drift. CI/CD и Git-hosted workflow запрещены решением владельца; проверка всегда локальная и read-only относительно проверяемого checkout.
- Человекочитаемый root `README.md` — короткая карта; он не обязан повторять весь JSON index. Domain README создавать, только если нужен curated entrypoint.
- Индекс строить только из явных полей; не делать LLM-based categorization/indexing в CLI. Agent semantic selection выполняется после чтения небольшого индекса.

---

## 7. Изменение документации: workflow агента/человека

### 7.1 Обычное архитектурное изменение вне задачи

1. Получить ясное подтверждение, что именно является фактом, решением, proposal или гипотезой; при неразрешённой смысловой неопределённости спросить, не заполнить пробел догадкой.
2. Прочитать root `README.md` и компактную часть `index.json`; сделать semantic selection релевантных docs/code/contracts/tests. CLI может предоставить `list/show/grep`, но не решает релевантность.
3. Прочитать только необходимые документы и непосредственно связанные источники. Расширять context по refs/обнаруженной зависимости, не отправлять весь docs-repo/транскрипт модели по умолчанию.
4. Подготовить **минимальный смысловой diff**: изменить существующую canonical запись, если речь про её содержание; создать отдельную только если есть самостоятельная единица знания/стабильные ссылки/другая аудитория.
5. Если это неутверждённая рекомендация, у документа — `status: draft`; для решения в ADR поставить `status: proposed`. Обозначить неизвестное и не менять current-state representation так, будто proposal уже внедрён.
6. Запустить CLI validation на изменённых документах; затем необходимые полные index/link/schema checks. Исправлять смысловой diff — агент/человек; CLI не должен авточинить semantic text.
7. Human review/approval по policy, затем commit/merge в canonical docs repo. Не публиковать и не merge-ить автоматически без разрешённого approval workflow.

### 7.2 Изменение, связанное с `task.json`

1. `task.json` остаётся единственным canonical normalized input; source-aware task ID, source refs, target release/scope берутся оттуда, а не из нового task description.
2. Агент использует index-first retrieval и готовит семантическую architecture delta в соответствующем `stageN/architecture-delta/`, со ссылкой на canonical document IDs, operation, reason/evidence, target release (если релизное различие реально), `base_doc_revision` (Git SHA), task/stage и affected entity/rule/flow IDs. Delta не является второй постоянной архитектурной истиной.
3. До предусмотренного owner review canonical документ не заменяется недосмотренным proposal. После принятия update делается в docs-repo, а task/stage сохраняет provenance/evidence. Если documentation change не нужна, это фиксируется `architecture_delta: none` с основанием в stage evidence.
4. После update: проверка refs/schema/index, review docs diff вместе с code/tests/acceptance, commit/PR refs фиксируются в task/stage; актуальная архитектура отражает согласованное поведение, а не неподтверждённый план.
5. Исходный `task.json` snapshot не редактировать задним числом. Новые вопросы/решения сохранять в соответствующем stage artifact по согласованной схеме.

### 7.3 Изменение release-specific поведения

Одна система/доменная сущность описывается один раз. Если поведение поддерживаемых releases различается, в том же документе сделать краткую таблицу/секции `applies to release → behavior → change/task/commit ref`. Не клонировать всё дерево в `releases/<version>/`. Если читателю нужна опубликованная versioned docs-site, это отдельный derived publishing concern; не менять из-за него canonical model автоматически.

---

## 8. CLI: что нужно, а что пока лишнее

### 8.1 MVP — четыре группы предсказуемых команд

Синтаксис условный; имена могут адаптироваться, поведение/границы важнее конкретного CLI бренда.

```text
arch list [--type entity] [--domain orders] [--status current] [--format json]
arch show ENT-orders-order [--format markdown|json]
arch index build
arch index check
arch validate [--changed | --all]
```

Рекомендуемая семантика:

1. **`list`** выдаёт компактные явные metadata records для фильтров по точным полям; не применяет semantic similarity.
2. **`show <id>`** разрешает ровно ID и возвращает path/metadata/content или явную ошибку `not found`/duplicate ID. По умолчанию не загружает всю базу.
3. **`index build/check`** строит generated `index.json` детерминированно / проверяет отсутствие drift.
4. **`validate`** проверяет YAML/frontmatter и JSON Schema; уникальные IDs и filename refs; относительные links/anchors; разрешённые `related` IDs; ссылки на task/stage/release/contract по зарегистрированной грамматике; синтаксис Mermaid/Markdown, если это поддерживается tooling. `--changed` — быстрая локальная проверка, полный check — локальный gate (`bash doc/tests/run.sh --gate`).

Можно объединить `list/show` с уже имеющимся grep/search CLI. Это не повод создавать полноценный search service. Machine report — стабильный JSON с `code`, file/path/JSON Pointer, message и exit code; ошибки actionable и не требуют чтения лога модели.

### 8.2 Write operations: принятое решение

**Базовый способ:** агент вносит обычный минимальный filesystem diff в docs-repo worktree/ветке; человек может сделать то же. Документ — обычный Markdown, frontmatter проверяется CLI. Commit/PR обеспечивает review, Git history и merge-conflict detection; обязательных проверок на стороне Git-хоста нет.

**Не делать обязательными** команды `glossary add term`, `entity edit`, `flow update`, `adr close` в первой версии. Они дублируют редактируемость Markdown и навязывают структурированный payload, хотя семантический выбор/текст всё равно производит агент. Сам вызов CLI не снижает token consumption. Он может помочь только если сокращает подаваемый контекст/output или устраняет измеримые ошибки.

Допустимое convenience, если несколько повторяемых схем уже согласованы: `arch new <type> --id ...` генерирует пустой scaffold и отказывается перезаписать файл. Это не семантическая запись и может быть отложено; создавать пустые документы автоматически по ходу без подтверждения нельзя.

**Позже, только при доказанной нужде:** `arch apply --change-set <file> --base <git-sha>` может применить несколько явных изменений атомарно с conflict detection. Смысл change-set пишет/утверждает агент/человек; CLI не выбирает документы и не переписывает контент. Перед внедрением доказать, что обычный Git branch/PR + validator недостаточны (например, shared filesystem без надёжного VCS/частые lost-update случаи). При canonical docs Git repository эта команда не обязательна.

### 8.3 Что CLI категорически не делает

- Не извлекает intent из текста task/chat и не решает, какие architecture docs затронуты.
- Не ищет «похожий» домен для семантического auto-link; точный grep/metadata filter — лишь кандидаты для агента.
- Не сочиняет entities, rules, transitions, ADR outcomes и business definitions.
- Не объявляет смысл корректным, документ актуальным или approval полученным по одному наличию поля/ссылки.
- Не исправляет broken links/ID/release applicability автоматически без explicit change.
- Не меняет/не нормализует исходный `task.json` незаметно.
- Не запускает произвольный shell/code из frontmatter и не пишет secrets в docs/logs.

### 8.4 Требования к информированности вывода CLI для агентов

Вывод CLI должен быть настолько информативным, чтобы агент мог принять решение о следующем действии без чтения логов модели и без угадывания причин ошибки. Это базовое требование, закреплённое в `data/cli-skills-encyclopedia/Практики/Agent-Friendly CLI Design.md` и `data/cli-skills-encyclopedia/Примеры/Пример agent-friendly CLI.md`.

#### 8.4.1 Структурированный вывод

Для команд-проверок `--brief` даёт короткий успешный результат с именем и областью проверки. Ошибка сохраняет диагностику в stderr и ненулевой код. Большой список можно сократить до первых записей с явным числом оставшихся и способом раскрытия. Действующие примеры — `validate --brief` и `scan --scope <scope> --brief`. Для запросов состояния компактный режим сохраняет необходимые поля и ссылки, например `task diagnose --json --brief`.

Групповой прогон для агента раскрывает метку, код и вывод провалившегося шага. Успешный итог перечисляет проверенные области. Воспроизводимый read-only прогон проверяет существующий индекс. Пересборка запускается отдельно при изменении его источников. Стадийное evidence хранит критерии, команду, проверенный снимок и исход. Диагностику и большие логи добавляют по ссылке.

- **JSON в stdout, всё остальное в stderr.** Любой машинный результат — в формате JSON (`--json` по умолчанию для всех команд, возвращающих данные). Плоский вывод preferred over вложенного; консистентные типы полей.
- **Единый envelope ответа:** `{ok, code, data, errors, hints}` где `errors` — массив структурированных объектов с `code`, `message`, `field`, `suggestion`, `exit_code`.
- **`--fields`** для выбора подмножества полей (экономия токенов агента), **`--quiet`** для голых значений без обёртки, **`--brief`** для сокращённого текстового режима.
- **JSON Lines** для стриминга списков и больших выборок.

#### 8.4.2 Exit-коды как control flow агента

Exit-коды документированы, семантические (не только 0/1), используются как сигналы для следующего шага агента:

| Код | Смысл | Действие агента |
|-----|-------|-----------------|
| 0 | Успех | Продолжить цепочку |
| 1 | Общая ошибка | Прочитать stderr, исправить |
| 2 | Ошибка аргументов/флагов | Исправить вызов CLI |
| 5 | Конфликт (существует уже) | Пропустить или `--if-not-exists` |
| 10 | Ошибка авторизации | Обновить креды / env |
| 20 | Не найдено | Проверить имя/путь/ID |
| 75 | Временная ошибка | Повторить (retry) |

#### 8.4.3 Ошибки — actionable и самодокументирующиеся

Каждая ошибка должна содержать:
- **`code`** — стабильный идентификатор ошибки;
- **`message`** — человек-читаемое описание на языке документации (ru/en);
- **`field`** — поле ввода, вызвавшее ошибку (если применимо);
- **`suggestion`** — точная команда или шаг для исправления (например, `use --if-not-exists`, `task_key must match directory name`);
- **`exit_code`** — семантический код для ветвления агента;
- Примеры исправления в `--help`.

Ошибка без `suggestion` считается дефектом CLI.

#### 8.4.4 Samoodokumentirovanie (self-documenting)

Для каждого проектного CLI ведётся один короткий скилл оператора с группировкой по операциям. Он задаёт точку входа, типичные аргументы, ожидаемый результат, изменения состояния и ссылку на точный `--help` или раздел контракта. Для обычной работы достаточно этого интерфейса. Когда задача меняет CLI или обнаруживает воспроизводимое расхождение, агент открывает только нужный символ и связанный тест. Публичное изменение синхронизируется с help, скиллом и проверкой контракта. [Операторский справочник Arch CLI](../../skills/arch-cli/SKILL.md)

- Полный `--help` с usage, аргументами, флагами, примерами, режимами вывода и документированными exit-кодами.
- Примеры обязательны — не только описания флагов, но и контекст использования.
- Help версионируется и держится стабильным (контракт, а не случайная документация).
- Help ≤ ~1500 токенов, чтобы не раздувать контекст агента (см. `data/cli-skills-encyclopedia/Практики/Токен-эффективность.md`).

#### 8.4.5 Компонуемость и цепочки

- Встроенная фильтрация (`--status`, `--type`, `--domain`, `--field`) наряду с поддержкой пайпов (`| jq`, `| grep`).
- Агент должен иметь возможность составить цепочку: `arch task diagnose <key> --json | ...` → принять решение → `arch task close <key>`.
- Идемпотентность: повторный вызов той же команды не создаёт побочных эффектов.
- Batch-операции для массовых действий.

#### 8.4.6 Dry-run и подтверждения

- **`--dry-run`** — структурированный diff/plan без применения изменений (JSON).
- **`--yes/--force`** — обход интерактивного подтверждения для деструктивных операций.
- Интерактивный промпт без `--yes` не допускается (агент зависнет).
- Sekrety только через env/secret store, never через флаги CLI или task JSON (см. манифест, раздел про role-based model CLI).

#### 8.4.7 TTY-aware вывод

- Если stdout — TTY: rich-вывод (цвета, таблицы) для человека.
- Если stdout — pipe/не TTY: clean JSON без ANSI, без спиннеров, без прогресс-бара в machine mode.
- Агент всегда работает в non-TTY режиме, поэтому его вывод должен быть чистым JSON.

#### 8.4.8 Связь с data/ энциклопедиями (MOC навигация)

Все требования этого раздела коррелируют со страницами в `data/cli-skills-encyclopedia/`, доступными через MOC навигацию (`data/cli-skills-encyclopedia/Главная.md`):

| Требование | Источник в data/ |
|------------|-----------------|
| Структурированный вывод, exit-коды, stdout/stderr | `Практики/Agent-Friendly CLI Design.md` |
| Actionable ошибки, suggestion, exit-коды | `Примеры/Пример agent-friendly CLI.md` |
| Help-текст как контракт, примеры, лимит токенов | `Форматы/Help-текст CLI.md` |
| Композиция команд, цепочки, фильтрация | `Практики/Работа агентов с CLI.md` |
| Токен-эффективность, бюджеты, cut defaults | `Практики/Токен-эффективность.md` |
| JSON Schema и Self-Description | `Форматы/JSON Schema и Self-Description.md` |
| Progressive Disclosure | `Форматы/Progressive Disclosure.md` |
| Безопасность CLI (secrets, env, не через флаги) | `Безопасность MCP и инструментов.md` (в machinedocs-encyclopedia) |

CLI не fuzzy-матчит архитектурные документы и не принимает семантических решений за агента — это pozostaje на стороне агента/скиллов (см. манифест, раздел 15).

---

## 9. Integrity checks и quality gates

### 9.1 Детерминированные проверки (первый уровень)

- корректный UTF-8/Markdown parse, H1/title policy, ровно один корректный YAML frontmatter;
- safe YAML parsing, отсутствие duplicate keys/unsupported tags, структурная JSON Schema validation;
- допустимый type/status, обязательные поля, unique stable IDs, ID↔filename consistency;
- ссылки `related`/`source_refs` на существующие IDs/repository aliases/relative paths/contracts, broken links, зарегистрированные external reference formats;
- ссылки task/stage/artifact/release имеют существующий schema-valid target в доступной области; live external Jira lookup — только отдельный явно вызванный adapter/network check;
- generated index актуален/детерминирован, неизвестные документы не теряются;
- синтаксис поддерживаемых Mermaid blocks/Markdown links/examples; contract refs валидируются внешними официальными tools там, где доступен сам contract;
- CLI не переписывает semantic body при `check`; report имеет точный file/path and exit code.

### 9.2 Проверки, которые остаются агенту/доменному reviewer

- Правильно ли выбран domain/document и описывает ли текст реальный смысл.
- Не противоречит ли новый факт коду, owner decision, acceptance criterion, API contract и другим release section.
- Полны ли ветви важного пользовательского/системного flow, реалистичны ли guards/retry/compensation.
- Важна ли decision для ADR, получено ли согласие и статус не перепутан ли.
- Соответствуют ли новые docs изменениям code/tests и не устарели ли соседние docs.

Автоматический parser/LLM self-report не даёт доказательства семантической актуальности. Не маркировать `verified` от факта, что линтер или локальная проверка прошла.

---

## 10. Token efficiency без переусложнения

Токены определяются прежде всего тем, какой контекст получает модель и какой объём output она создаёт. Использование CLI не является отдельной экономией модели. Эффект возможен только если workflow реально сокращает context/iterations/errors.

Рекомендации:

1. Сначала загрузить root README и компактный `index.json`/отфильтрованный список, а не страницы целиком.
2. `arch show ID` — только после semantic selection; получить нужные 1–3 документы, потом расширять context по evidence.
3. Передавать модели минимум: task intent/`task.json` необходимые поля, релевантные выдержки/docs, точные refs, текущий diff и проверяемые acceptance/evidence. Не пересылать всю энциклопедию, весь transcript или копии contract по умолчанию.
4. Править ближайший раздел небольшим patch, не переписывать полный MD файл и не генерировать вторую человекочитаемую задачу из `task.json`.
5. Избегать отдельного model call только ради форматирования `arch add`; CLI validators не требуют LLM.
6. Если write API когда-нибудь сравнивается с прямой правкой, одинаковые условия измерения: input tokens, output tokens, число model/agent iterations, document correctness/repair rate, time/cost. Это tabletop acceptance/eval design сейчас; эмпирический pilot возможен только после обязательных preconditions из workflow, не запускать ради проверки гипотезы о токенах до них.

Ожидаемая исходная гипотеза: прямая Markdown-правка обычно дешевле для одиночной небольшой prose update; structured CLI может быть лучше для повторяемых объектов и сложных cross-reference validation, но только если его компактный API сужает контекст и не добавляет round trips. Это гипотеза, а не измеренный результат.

---

## 11. Что изменяется с текущего наброска манифеста

Эта записка деталирует раздел «Предлагаемая модель хранения документации и тестов» единственного root-манифеста. Рекомендуемые уточнения, которые следует перенести в манифест при его следующей явной редакции:

1. Закрепить docs-repo + `.doc/architecture/` как canonical физическую схему, сохранив repo host в конфигурации.
2. Оставить один generated `index.json` и root README; не требовать локальных индексов по каждому domain. Domain README — только когда он полезен человеку.
3. Зафиксировать общий versioned JSON Schema и templates для всех реально поддерживаемых artifact types; не ограничиваться декларативным перечнем полей и не пытаться валидировать свободную prose машиной.
4. Добавить устойчивые domain capability specs с требованиями и WHEN/THEN сценариями там, где нужно сохранять поведение от задачи к задаче; task proposal/delta остаётся отдельной от accepted current spec.
5. Включить data model/data-flow/ownership/retention/compatibility, glossary entry format, integration/contract reference, quality, security, operations, constraints/risks и verification map в полный artifact format registry. Не создавать каждый артефакт без material concern.
6. Сохранить `base_doc_revision` как Git SHA; Git commits/PRs + `task.json`/stage refs — provenance. Не вести дублирующий per-document append-only history log, если Git/task refs покрывают audit need; если audit требует отдельного append-only record, добавить его после формального требования и threat analysis.
7. Оставить прямое Markdown редактирование как нормальный write path; typed CRUD/atomic apply — deferred, не обязательная capability. CLI MVP — explicit list/show, deterministic index build/check, validation.
8. Для C4 использовать concern-driven views; context/container обычно достаточно. Для flow не создавать собственный DSL; использовать явный Markdown/table/diagram или уже принятый BPMN/DMN/workflow source.
9. Не копировать API/schema contracts и не создавать релизные копии всей документации; ссылки + применимость по релизу в одном canonical doc.

Это не дублирует манифест и не является его копией. Манифест остаётся единственным root manifest; данный файл — отдельная детализированная design decision/research deliverable. Внедрять workflow/CLI или начинать практический пилот эта записка не предлагает.

---

## 12. Что необходимо зафиксировать до реализации

Модель хранения/форматов/CLI границы выбрана. До практического implementation/pilot остаются только проектные конфигурационные значения и operational contracts:

- URL/access-control/backup/ownership отдельного docs Git repository; обеспечить, что sandbox/agent worktree получает его read/write (по policy) под настроенным docs-root и CLI/skill используют один и тот же root, а не сетевой fetch на каждый файл;
- реальные domain names/owners и кодовые repository aliases для `source_refs`;
- release IDs и разрешённая грамматика `applies_to`/release refs;
- выбранный Markdown renderer/GFM subset и наличные schema/link/Mermaid validators;
- точные approval/code-owner policy для архитектурных decisions и docs merge;
- schema evolution policy для frontmatter и generated index.

Если это всё ещё не определено, использовать placeholder как unresolved и не выдумывать участников/версии/release list. Tabletop walkthrough после specification — completeness check, не agent run/empirical pilot. Любой будущий pilot по-прежнему требует репозитория, acceptance oracle, надёжного локального gate, изолированного sandbox, ownership/approval, baseline/eval set и stop/rollback пути.

---

## 13. Исследованные внутренние материалы энциклопедии

Внутренний ресёрч сверялся с текущими заметками, а не создавался как изолированный platform comparison:

- [Исследование формата документации проекта и входящей задачи](<../../../data/machinedocs-encyclopedia/Практики/Исследование формата документации проекта и входящей задачи.md>) — `task.json`, one-agent workflow, CLI/agent boundary, docs skill, integrity CLI, open questions.
- [Docs-as-Code и CI](<../../../data/machinedocs-encyclopedia/Архитектура/Docs-as-Code и CI.md>) — links/schema/index checks и review.
- [Index-First подход](<../../../data/machinedocs-encyclopedia/Архитектура/Index-First подход.md>) и [Frontmatter-схемы](<../../../data/machinedocs-encyclopedia/Форматы/Frontmatter-схемы.md>) — compact map, load-trigger metadata, точечное retrieval.
- [Сущности](<../../../data/machinedocs-encyclopedia/Документация/Сущности.md>) и [Флоу](<../../../data/machinedocs-encyclopedia/Документация/Флоу.md>) — identity/invariants/lifecycle, actors/steps/error paths/state.
- [Актуальность и staleness](<../../../data/machinedocs-encyclopedia/Практики/Актуальность и staleness.md>) — human verification против автоматических timestamp/max-age.
- [Структурированный Markdown](<../../../data/machinedocs-encyclopedia/Форматы/Структурированный Markdown.md>), [пример структуры docs](<../../../data/machinedocs-encyclopedia/Примеры/Пример структуры docs.md>) и [пример пакета документации фичи](<../../../data/machinedocs-encyclopedia/Примеры/Пример пакета документации фичи.md>) — атомарность, шаблоны и references.
- [Корневой манифест software factory](<../../../Манифест агентной software factory.md>) — один root manifest; single-agent scope; `task.json`; source-aware intake; model/CLI split; task/stage delta and human approvals.

### Итог внутренней сверки

Сохраняются сильные полезные идеи текущего наброска: один индекс, stable IDs, domain grouping, explicit relationships, `task.json` как canonical task input, `architecture-delta`, release provenance, structural CLI validation, semantic routing агентом. Смягчаются потенциально избыточные части: отдельные индексы на каждый раздел, обязательная CLI-write path для любого Markdown, ручной changelog на каждой сущности, обязательное описание всех branches/fields и обязательная полная формализация всех типов.

---

## 14. Внешние источники

Проверены на 2026-11-21; ссылки ведут на первичные страницы/официальные источники, если они доступны. Содержание стандарта ISO 42010 полностью не извлекалось из платного текста; использован его официальный abstract и открытые материалы. Этот документ не декларирует formal conformance.

1. ISO, [ISO/IEC/IEEE 42010:2022 — Software, systems and enterprise — Architecture description](https://www.iso.org/standard/74393.html). Официальный abstract: требования к структуре/выражению architecture description; не устанавливает формат, носитель, process, tools, notation.
2. arc42, [Template home and sections](https://docs.arc42.org/home/) и [Section 9 — Architecture Decisions](https://docs.arc42.org/section-9/). 12 тем как проверочный шаблон, lean/thorough guidance, ADR options; не обязательная physical folder structure.
3. C4 Model, [Diagrams](https://c4model.com/diagrams). Tool-independent hierarchy and supporting views; context/container достаточны для большинства teams, остальные уровни — по ценности.
4. MADR, [About and applying MADR](https://adr.github.io/madr/). Один значимый decision на ADR, Markdown, lightweight structured options/outcome.
5. Diátaxis, [Overview](https://diataxis.fr/). Four user documentation modes: tutorial/how-to/reference/explanation; not an architecture entity taxonomy.
6. CommonMark, [project and specification links](https://commonmark.org/). Motivation for choosing a defined Markdown subset because Markdown implementations diverge.
7. YAML, [Version 1.2.2 specification](https://yaml.org/spec/1.2.2/). Defines YAML data language; frontmatter delimiters are a convention layered on Markdown.
8. JSON Schema, [Specification index](https://json-schema.org/specification) and [Draft 2020-12](https://json-schema.org/draft/2020-12). Structural schemas/validation; current specification index says 2020-12.
9. OpenAPI Initiative, [Official version index](https://spec.openapis.org/oas/). On review date includes OAS 3.2.1 and published schemas; tool compatibility still must be checked.
10. AsyncAPI Initiative, [AsyncAPI 3.0.0 specification](https://www.asyncapi.com/docs/reference/specification/v3.0.0). Machine-readable, protocol-agnostic description for message-driven APIs.
11. OpenSpec, official [Getting Started](https://openspec.dev/docs/getting-started), [spec-driven schema](https://openspec.dev/docs/schemas/spec-driven), [CLI reference](https://openspec.dev/docs/cli): separate current specs from change proposals, capability-based delta specs, structural validation, sync/archive lifecycle. The workflow/tool is a reference, not a project requirement.
12. GitHub Spec Kit, official [Agentic SDD reference](https://github.github.io/spec-kit/reference/agentic-sdd.html), [Quickstart](https://github.github.io/spec-kit/quickstart.html), and [repository/templates](https://github.com/github/spec-kit): what/why spec, technical plan, clarification, tasks, optional checklist/analyze and implementation. A toolkit/template, not a normative standard.
13. OpenAI, [Harness Engineering](https://openai.com/index/harness-engineering/): practitioner report on repository-local knowledge, maps and CI checks as an engineering report, not a standards document.

### Evidence limits

Official standards explain concepts/requirements but do not prescribe our tree or prove a folder scheme reduces agent tokens. C4/arc42/Diátaxis/MADR are frameworks/practices, not interchangeable normative standards. Token-efficiency judgement is a design hypothesis; no pilot, token measurements, usability study, CI/schema acceptance test, or repository-specific ownership audit has been performed. Version/tool adoption must be rechecked when actual toolchain is known.

---

## 15. Future compatibility: architecture documentation generated by code scanning

**Out of scope for the current project/core.** A separate future program/service with its own work queue may scan product repositories, construct/consult a code graph, use MCP servers and dedicated skills, and coordinate specialized subagents to extract evidence and draft architecture documentation. This is a compatibility constraint for the storage design, **not** a request to implement the scanner, choose its stack, add its queue to `task.json`, or design multi-agent orchestration in the current single-agent core.

### 15.1 What the documentation architecture should make possible

- Stable architecture IDs, bounded type/domain metadata, explicit relationships and a generated machine index let a future producer find/update candidate records without relying on filenames alone.
- `source_refs` use repository aliases + repository-relative paths, optional symbols/schema pointers, and optional immutable commit revision. This supports navigation from a claim to code/schema/test and reproducible comparison against a pinned source revision; no workstation-local absolute paths.
- A future scan run can record its own run ID, source repository + commit, scanner/graph/skill/MCP versions/config, and evidence pointers in **its own scan/evidence artifact**. Do not insert ephemeral graph-node IDs or scanner run data as if they were stable business entity IDs.
- The documentation corpus remains readable and editable without that scanner, graph server, MCP tools or agent orchestration. Generated source indexes and diagrams, if later needed, are derived views with a declared input/version, not a second canonical system model.

### 15.2 Candidate-generation и acceptance boundary

The scanner may generate evidence-backed **candidate findings или document deltas** в отдельной branch/review area. Он не должен молча перезаписывать принятые canonical документы, изобретать доменную семантику из имён классов/таблиц, помечать контент `current`/`verified` только потому, что код был распарсен, или одобрять свою интерпретацию. Его output должен различать прямые code observations от inferred meaning, указывать точный source revision/locations, перечислять unresolved questions и показывать минимальный diff. Агент/владелец проверяет семантическую интерпретацию и продвигает принятые обновления через обычный docs Git review/merge path.

Код — evidence implementation, не proof business intent или completeness. Static scanners часто могут report direct facts (dependency edges, public declarations, schema fields, endpoint/test locations); значения такие как «это авторитетное Order state», business purpose, external promise, exception rationale, и accepted architectural decision требуют других источников или owner validation. Conflicting code/docs должны стать discrepancy candidate, не разрешаться тем sources, которые easiest to parse.

### 15.3 Keep responsibilities separate

- Future scanner program owns its queue, scan scheduling, graph/MCP adapters, specialist skills/subagents и evidence collection; это separately specified когда initiative resumes.
- Current docs CLI owns deterministic frontmatter/index/link/reference checks, explicit reads и ordinary Git-safe changes; он не приобретает semantic code-understanding authority потому, что существует будущий scanner.
- Current factory stays one agent. Future scanner may use multiple subagents inside its own system без изменения factory current scope.
- Не делать `.doc/architecture` зависимым от scanner-specific output formats; source refs и stable document contracts — interoperability boundary.

---

## 16. Task-conf: иерархическая конфигурация типов и потоков задач

Структура, что именно лежит в задачах, задаётся иерархической конфигурацией в `doc/config/task-conf/`. Каждый тип задачи — папка `types/<type>/` с двумя файлами:

- `config.yaml` — конфиг типа: `id`, `title`, `description`, `complexity_default`, `complexity_allowed`, `allowed_flows`, `default_flow`, `subtask_policy`, `close_policy`, `required_fields`, `forbidden_in_scope`.
- `prompt.md` — стартовый промпт типа (по принципу скилла), исполняемый при начале работы над задачей этого типа.

Внутри типа подпапка `flows/<flow>/` с файлами:

- `config.yaml` — конфиг flujo: `id`, `title`, `type`, `description`, `subtask_policy`, `close_policy`, `steps` (с `id`/`name`/`action`/`output`/`gate`).
- `prompt.md` — стартовый промпт flujo, регламентирующий, как агент выполняет задачу этого типа и этого flujo.

Такой подход означает: **структура конфига задаёт, что лежит в задачах** — `allowed_flows` определяет, какие flujo доступны для типа; `subtask_policy` (`required`/`optional`/`forbidden`) — нужно ли создавать подзадачи; `close_policy` — может ли задача закрыться при незакрытых подзадачах; `required_fields` — какие поля `task.json` обязательны; `steps` с `gate` — порядок действий и условия перехода между этапами.

### Зарегистрированные типы задач

| task_type | Назначение | Потоки (flows) | Подзадачи | Закрытие |
|---|---|---|---|---|
| `jira-incoming` | Вcoming задача из Jira | `jira-process` | required | все подзадачи должны быть закрыты |
| `research` | Исследование, анализ, ресёрч | `research-first` | optional | все подзадачи должны быть закрыты |
| `planning` | Планирование, декомпозиция | `research-first`, `standard-implementation` | optional | все подзадачи должны быть закрыты |
| `audit` | Аудит, проверка соответствия | `research-first` | optional | все подзадачи должны быть закрыты |
| `feature` | Новая функциональность | `standard-implementation`, `research-first` | required | все подзадачи должны быть закрыты |
| `bugfix` | Исправление дефекта | `standard-implementation`, `minimal-scaffold` | optional | все подзадачи должны быть закрыты |
| `docs` | Документация | `docs-only` | optional | все подзадачи должны быть закрыты |
| `refactor` | Рефакторинг | `standard-implementation`, `minimal-scaffold` | optional | все подзадачи должны быть закрыты |
| `subtask` | Лист работы внутри родительской задачи | нет | forbidden | все подзадачи должны быть закрыты |
| `scaffold` | Создание заготовки | `minimal-scaffold` | forbidden | все подзадачи должны быть закрыты |

### Поля task.json, добавляемые структурой task-conf

Каждый `task.json` содержит дополнительные поля, определяемые конфигом типа/флоу:

- **`task_type`** — один из зарегистрированных типов (см. `arch task types`).
- **`flow`** — идентификатор flujo, закреплённый за задачей; должен быть в `allowed_flows` для выбранного `task_type`. CLI валидирует совместимость при `arch task validate`.
- **`complexity`** — `low` / `medium` / `high` / `critical`; стартовое значение берётся из `complexity_default` типа.
- **`estimate_hours`** — положительное число часов работы агента; ставит агент по перечню работ. Необязательное поле.
- **`subtasks`** — массив `{id, title, status, path}`; задаётся при декомпозиции через `arch task decompose`. Запись может содержать выбранные агентом `task_type`, `flow`, `complexity` и `estimate_hours` ребёнка.
- **`implementation_plan`** — требуется для типов, где указано в `required_fields`.
- **`research_docs`** — массив研究-документов задачи, см. раздел 17.

### Валидация полностью конфиг-driven

Валидация `task.json` (`arch task validate`) загружает все правила из YAML-конфигов:
- `doc/config/paths.yaml` (секция `project`): `task_types`, `phases`, `risk_levels`, `source_types`, базовые `task_schema_required_fields`.
- `doc/config/task-conf/types/<type>/config.yaml`: `required_fields`, `allowed_flows`, `complexity_allowed`, `subtask_policy`, `close_policy`.

В Python-коде нет хардкода enum'ов, обязательных полей или допустимых значений — всё читается из конфига.

---

## 17. Исследовательская папка задачи: `research/` и CLI

### Исследовательская папка `research/`

Внутри каждой задачи может быть папка `doc/tasks/<task_key>/research/` со свободными Markdown-документами для исследований, гипотез, ссылок на кодовую базу и внешние источники (интернет). Это место для сбора сырой информации, которая ещё не превратилась в принятое решение или канонический документ.

Связь с задачей фиксируется в поле `research_docs` родительского `task.json` — массив объектов:

```json
{
  "id": "res-001",
  "title": "Гипотеза о кэшировании заказов",
  "path": "doc/tasks/UI-0009/research/order-cache-hypothesis.md",
  "source_type": "web",
  "source_ref": "https://example.com/article",
  "summary": "Почему кэширование заказов может снизить нагрузку на БД на 40%",
  "status": "hypothesis"
}
```

Поля `research_docs`:

| Поле | Описание |
|------|----------|
| `id` | Стабильный идентификатор исследования внутри задачи |
| `title` | Человекочитаемое название |
| `path` | Путь к `.md` файлу, должен быть под `doc/tasks/<task_key>/research/` и заканчиваться на `.md` |
| `source_type` | `web` — интернет-источник; `code` — кодовая база; `internal` — внутренний документ/знание |
| `source_ref` | URL, путь к коду или ссылка на внутренний документ |
| `summary` | Краткое суть исследования / гипотезы |
| `status` | `hypothesis` — недоказанная гипотеза; `confirmed` — подтверждено evidence; `rejected` — опровергнуто; `archived` — больше не актуально |

Правила работы с `research/`:

1. **Свободное содержимое** — внутри `.md` файлов можно фиксировать любые гипотезы, ссылки, выдержки из кода, заметки из интернета, черновики.
2. **Не каноническая документация** — research-файлы не являются канонической архитектурной документацией. Если исследование приводит к принятому решению, соответствующий канонический документ (сущность, флоу, правило, ADR) создаётся отдельно в `doc/architecture/` с ссылкой на research-файл как на источник.
3. **Связь с таском** — каждый research-файл регистрируется в `research_docs` родительского `task.json`; без регистрации файл считается не 연결ным к задаче и выявляется валидатором.
4. **CLI не семантически анализирует** — CLI только проверяет путь, наличие обязательных полей и корректность `source_type`/`status`. Семантическую оценку гипотез и их подтверждение/опровержение выполняет агент/скилл.
5. **Подзадачи могут иметь свои research/** — рекурсивно, каждая подзадача может иметь свою папку `research/` с собственными файлами.

### CLI: детерминированные команды для работы с задачами и путями

| Команда | Назначение |
|---------|-----------|
| `arch task types` | Список всех типов задач из `task-conf` с их `allowed_flows`, `subtask_policy`, `close_policy`. |
| `arch task flows --type <type>` | Список разрешённых flujo для типа задачи. |
| `arch task type-prompt --type <type>` | Вывод стартового промпта типа (как скилл агента). |
| `arch task flow-prompt --type <type> --flow <flow>` | Вывод стартового промпта flujo. |
| `arch task decompose <task_key> --subtask-id NNNN --subtask-title "..."` | Создание подзадач через CLI. Каждая подзадача получает собственную `task.json` и `stage1/`. |
| `arch task diagnose <task_key>` | Гант-подобная диагностика: тип, флоу, сложность, фаза, подзадачи, блокеры закрытия. |
| `arch task close <task_key>` | Закрытие задачи — отказывает с ненулевым exit code, если есть подзадачи с `phase != completed`. |
| `arch docs paths --check` | Обходит настроенные корни документации и выявляет файлы вне `allowed_paths`. Проверяет frontmatter, типы и статусы. |
| `arch docs paths --resolved` | Возвращает JSON с полями `project_root`, `config`, `doc_root` и `roots`. Пути внутри проекта относительны к `project_root`. Явно внешний YAML или справочник указан абсолютным путём. |

Проект выбирается через `--root` или по размещению CLI. По умолчанию загружается `doc/config/paths.yaml` в этом проекте. Явный `--config` заменяет этот выбор и может быть абсолютным либо относительным к корню проекта. `doc_root` и `roots` разрешаются относительно проекта. `roots.index` — относительный файл внутри `roots.architecture`. Шаблон `{architecture}/{index}` расширяется до единственного проектного пути этого файла. Ошибки YAML, несовместимые типы и выход рабочего корня через путь или символическую ссылку дают отказ до выполнения команды. Настроенные корни читаются по файловой системе независимо от Git. При переносе сохраняйте разрешимость Markdown-ссылок на другие каталоги или используйте стабильные ID в `related`.
| `arch task validate <task_key>` | Валидация `task.json` полностью конфиг-driven (без хардкода в Python). |
| `arch task status <task_key>` | Состояние задачи, этапы, верификация, тип, флоу, сложность. |

### Контроль закрытия задач на уровне CLI

Задача с `close_policy: all_subtasks_required` (все текущие типы) может быть закрыта только через `arch task close <task_key>` после выполнения двух условий:

1. Все подзадачи в `doc/tasks/<task_key>/subtasks/<subtask_id>/` имеют `phase: completed`.
2. Получен approval владельца задачи.

`diagnose` и `close` проверяют карточку и детей из объединения объявленных записей с непосредственными каталогами. Перед фактическим закрытием агент сверяет критерии, актуальность evidence и применимое одобрение. Подробности в [описании жизненного цикла](../domains/task-lifecycle/flow.md).

This nuance captured in root manifest как future/out-of-scope note. Until separate design approved, no scanner directory, queue schema, generated-candidate type, graph technology, MCP list или multi-agent runtime added to this architecture.
