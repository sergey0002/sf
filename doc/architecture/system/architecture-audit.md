---
id: ARCH-audit
type: constraints-risks
title: Глубокий аудит doc.architecture.md
summary: "Дата: 2026-11-21. Объект: первоначальная версия doc.architecture.md и актуализированная версия 1.2."
status: draft
domain: system
related: [ARCH-contract, MAN-software-factory, SYS-simple-factory]
source_refs:
  - /home/user/doc.architecture-audit.md
---

# Глубокий аудит `doc.architecture.md`

**Дата:** 2026-11-21
**Объект:** первоначальная версия `doc.architecture.md` (первый draft, около 5.5 тыс. слов) и актуализированная версия 1.2 (аудит v1.1 плюс последующее требование о будущей code-scanning documentation program).
**Результат:** v1.0 была концептуально хорошей, но не полной спецификацией. После аудита основной документ расширен до v1.1: добавлены durable capability specs, SDD delta lifecycle, полный реестр типов артефактов, точные section contracts/templates, черновой JSON Schema и пример generated index. В v1.2 добавлена совместимость с будущим отдельным code scanner через typed source refs и provenance boundary. Это не означает, что CLI, scanner или формат уже реализованы в проекте.

---

## 1. Executive verdict

**Первоначальный документ нельзя было честно считать полностью определившим все форматы.** В нём были согласованы направления (Markdown, index, entities, flows, ADR, direct edits vs CLI), но у нескольких важных типов существовали только названия/перечни полей, без полного формата. Особенно недоставало стабильной модели поведения/capabilities, data architecture, точной glossary записи, change delta, cross-artifact consistency gate и согласованной семантики статуса.

Основное архитектурное направление подтверждено: один доступный агенту, версионируемый docs-root; небольшая карта + точечное чтение; структурный CLI вместо смысловой эвристики; Markdown как удобное reviewable содержимое; текущая спецификация отдельно от предложения по её изменению. Однако первая версия переопределила некоторые выводы: общая сущность/flow модель без durable capability requirements не даёт полноценный SDD contract; типовая папка без конкретного документа-шаблона не равна определённому формату; `status` одновременно использовался для документа и decision lifecycle.

### Статус по критериям

| Критерий | Версия 1.0 | Версия 1.1 после аудита |
|---|---|---|
| Scope и guardrails | Хорошо: one-agent, `task.json`, no pilot, root manifest rule | Сохранены; no change в accepted scope |
| Architecture description model | Хорошая основа: ISO 42010, arc42, C4 | Дополнено mapping concerns → views и ограничением claims о conformance |
| SDD / change lifecycle | Частично: task-stage delta есть, но не было stable behavior-spec layer и полного delta contract | Добавлены capability specs, ADDED/MODIFIED/REMOVED/RENAMED delta и mapping OpenSpec/Spec Kit без второго task input |
| Entities / data | Entity fields были частично описаны; системная data model отсутствовала | Добавлены data view, ownership/lifecycle/consistency/privacy/retention/schema refs и entity template |
| Glossary | Упоминалась, но запись термина не имела точного формата | Добавлен domain-qualified term record, aliases, avoid terms, technical mapping и stable IDs |
| Flows / business rules | Основные понятия были, но не хватало полного behavior-to-test contract | Добавлены flow table contract, paths/guards/outcomes/failures/test refs и rule-table format |
| Other architecture types | Упомянуты, но не у каждого был body template | Добавлены contract/integration, quality, security/threat, constraints/risks, deployment/operations, verification, cross-cutting templates |
| Metadata/index | Был список полей и общий принцип; schema/index shape не был задан | Добавлен Draft 2020-12 envelope schema, statuses, условный domain field, index example |
| Agent-first retrieval | Верно описан index-first/direct editing | Дополнены explicit load triggers, no all-doc dump, path-only references, agent semantic routing |
| Readiness | Требовал доработки перед контрактным tabletop | V1.2 — CLI/schema реализованы: task-conf иерархия (типы + флоу), конфиг-driven валидация task.json, CLI команды (types, flows, type-prompt, flow-prompt, decompose, diagnose, close, docs paths --check), детектор мусора, контроль закрытия задач. Подтверждено валидатором проекта. |

---

## 2. Сравнение с SDD-подходами

### OpenSpec: что применимо

Официальный OpenSpec workflow разносит **main/current specs** и **change proposals**. В default schema отдельные artifacts отвечают на разные вопросы: proposal — зачем/что меняется; delta specs — какие behavior requirements добавляются/меняются/удаляются; design — как реализовать, когда требуется; tasks — исполнение. Delta применяется к main specs после выполнения workflow. OpenSpec также допускает пропуск design/spec artifacts, если они не соответствуют change; его CLI list/show/validate/archive работает с явными artifacts.

**Что было слабым в исходном документе:** `architecture-delta` была описана для task stages, но не было постоянного канонического capability spec, относительно которого delta формируется. Entity/flow descriptions не заменяют нормализованный текущий контракт пользовательского/системного поведения. Кроме того, в файле не было точного transition rule, когда proposal становится current docs.

**Что исправлено в v1.1:** добавлена `capability-spec` как долгоживущий behavior contract; `stageN/architecture-delta/` объявлена proposal-only; даны ADDED/MODIFIED/REMOVED/RENAMED semantics и явный merge/sync только после approval/verification. Это заимствует паттерн, не устанавливает OpenSpec как зависимость и не заменяет `task.json`.

### GitHub Spec Kit: что применимо

Официальный Spec Kit workflow разделяет project principles/constitution, что/почему spec, clarification, technical plan, dependency-ordered tasks, implementation и optional checklist/analyze gates. В его guidance specification focuses on behavior/intent, technical choices принадлежат plan; clarification и analyze помогают вернуть обнаруженную неопределённость на правильный источник. Templates могут включать data model, contracts, research и quickstart как optional supporting artifacts.

**Что было слабым:** нет отдельного формата durable capability requirements с testable scenarios; не полностью определена проверка связности между requirements, architecture design, data/contracts и verification. Также не было оговорки, какие SDD artifacts нельзя привносить из toolkit из-за уже закреплённого `task.json` contract.

**Что исправлено:** добавлен durable capability template с `Requirement` / observable `Scenario` и `NEEDS CLARIFICATION`; добавлены consistency checklist и explicit workflow ordering. Scope guardrail сохранён: `task.json` — единственный canonical task intake, нет `task.md`, stage plan remains existing task workflow, для trivial/refactor/doc-only изменений нет искусственного spec artifact.

### Переносимость выводов

OpenSpec и Spec Kit — рабочие инструменты/шаблоны, а не стандарты архитектурного описания. Их артефакты пригодны как проверенные workflow patterns, но копирование их CLI, phase count, file tree и шаблонов целиком увеличило бы overhead и конфликтовало бы с `task.json`. В v1.1 приняты только различия источников истины и возврат ambiguity/consistency issues на этап, который их создаёт.

---

## 3. Полнота видов архитектурного знания

### Данные и предметные модели

В первой версии `entity` описывала identity, state, invariants, attributes и relationships — полезно, но недостаточно для system data architecture. Не были систематизированы authoritative source/owner, read/write responsibilities, cross-boundary data flows, consistency model, classification/privacy, retention/deletion, schema migration и compatibility.

В v1.1 это разведено на три уровня:

1. `system/data.md` — системные data boundaries, ownership, flows и cross-cutting lifecycle concerns, если они существенны;
2. domain `entity`/`data-concept` — доменный смысл, lifecycle, invariants и значимые атрибуты;
3. настоящий contract/schema/migration в своём поддерживаемом product source — технический source of truth.

Не следует заставлять проект создавать полный data catalog, если данных/consumers мало. Надо, однако, явно задавать ссылку на source и отмечать unknown owner/retention/consistency, если они блокируют безопасное решение.

### Глоссарий

Первый документ говорил о domain-specific language, но не задавал term-level contract: canonical label, context, aliases, disambiguation, technical mapping, examples и stable reference. В v1.1 добавлен один формат записи внутри glossary/domain page. Важно не делать один файл на слово, но и не терять контекст омонимов между domains. Для проектного CLI остаётся машинно проверяемая договорённость о `TERM-*` IDs; сами определения остаются семантическим текстом.

### Capabilities, requirements и flows

Flow-документ объясняет поведение во времени, но не всегда отвечает на вопросы «что система обязана делать?» и «по каким observable scenarios мы проверяем acceptance?». Поэтому flow не должен быть единственной функциональной спецификацией.

В v1.1:

- capability spec — owner долговременных требований/сценариев;
- flow — runtime realization/branches/side effects;
- entity/data view — concepts/state/ownership;
- business rules — decision predicates/outcomes;
- contract — protocol/message shape;
- test/verification map — pointers к независимому oracle/evidence.

Это снижает неоднозначное дублирование: у каждого утверждения есть один canonical owner; остальные artifacts ссылаются на stable IDs. Branch table полезна только для flow, где нужно связать path с tests/releases; обязательного custom workflow DSL не появляется.

### API, event integrations, операции и quality

Первый документ правильно запрещал копировать contracts, но практически не задавал архитектурную карточку интеграции, поэтому agent не мог понять producer/consumer, direction, compatibility, auth, retries/failure behavior, owner и test path по одному URL. В v1.1 добавлен concise interface-reference template при сохранении OpenAPI/AsyncAPI/schema source of truth.

Также добавлены conditional formats:

- quality scenario — concern/stimulus/environment/response/measure/evidence;
- threat record — asset/actor/boundary/scenario/impact/control/residual risk/evidence;
- deployment/operations view — environments/runtime placement/availability/restore/observability/runbook/IaC refs;
- constraints/risk/debt row — scope/effect/mitigation/owner/status/review trigger;
- verification map — behavior ID → test location/command/evidence.

Эти данные присутствуют только если они не авторитетно описаны в IaC, SLO, CMDB, security/risk system или test harness. Иначе — ссылка на source, не копия.

---

## 4. Agent-first quality audit

Критерий не «Markdown удобно человеку», а «агент быстро получает только проверяемый необходимый контекст и не должен догадываться».

### Хорошо уже было

- Index-first retrieval и запрет полного dump.
- Explicit paths/IDs/refs вместо вывода по расположению.
- Понятное разделение agent semantic responsibility vs deterministic CLI.
- Не навязывать все diagrams/arc42 sections; не создавать файлы для галочки.
- Ссылаться на contracts/tests/code, не копировать машинно-истинные источники.

### Что требовало усиления

- **Progressive disclosure:** простая карта должна быть всегда доступна, но весь корпус — по запросу. Теперь требования к README/index/load-trigger, list/show and context expansion сформулированы отдельно.
- **Stable behavior requirements:** добавлена capability spec, чтобы агент мог видеть accepted intent, а не восстанавливать его из ticket или реализации.
- **One source of truth per claim:** между entity, capability, flow, rule, schema и тестом раньше не были назначены достаточные owners по типу утверждения. Теперь разнесены их роли и ссылки.
- **Explicit unknowns:** добавлен `NEEDS CLARIFICATION`/draft state, статусы документа/ADR/domain object разведены.
- **Retrieval-safe IDs:** ordinary page link + stable ID предпочтительнее нестабильных Markdown heading fragments; glossary/reference IDs требуют unique check.
- **Evidence:** content must link to code/contract/test or clearly mark rationale/decision/proposal; linter cannot approve semantic truth.
- **Agent access:** отдельный docs repo бесполезен, если sandbox не монтирует его. В v1.1 добавлено требование same configured docs-root for skill/CLI.

### Остаточный anti-pattern risk

Чрезмерная полнота шаблонов может породить бюрократическую пустоту. Все поля/документы отмечены как conditional; шаблон — schema of a useful artifact, не checklist обязательных файлов. Особо не навязывать entities на каждый класс, glossary file на каждый term, ADR на каждый выбор, flow diagram на каждый endpoint, data catalog для малого продукта.

---

## 5. Проверка «для всего ли описаны форматы»

### Ответ: в v1.0 — нет; в v1.1 — есть проектный контракт для каждого заявленного типа, но не все типы обязательны

Формат готов как **reviewable Markdown/schema draft** в смысле:

- определён каталог type names и назначение;
- для каждого type указано, когда он появляется;
- задан общим frontmatter envelope и lifecycle fields;
- у каждого content type заданы required/recommended sections или table schema;
- определено, какие данные canonical в другом source;
- task delta имеет explicit envelope и operations;
- index имеет JSON shape/example;
- есть validate/check expectations.

Это **не означает**, что уже существуют исполняемые файлы `document.schema.json`, `index.schema.json`, templates или CLI. JSON Schema draft внутри документа синтаксически проверена и прогнана через установленный JSON Schema Draft 2020-12 validator на все 17 `type` values, а также на отрицательные проверки (decision без `decision_status`, entity без `domain`, code source-ref без `repo/path`, external source-ref без `url`); structured code source-ref проходит validation. JSON-пример индекса тоже parse-ится. Это проверка design snippet, не schema-файл/CI/toolchain implementation. Полный fixture suite и проверка YAML/frontmatter/link/Markdown behavior всё ещё нужны в tabletop/contract validation.

### Матрица охвата v1.1

| Artifact | Template/format есть в основном doc? | Canonical information owner | Статус создания |
|---|---:|---|---|
| System overview + concerns/views | Да | `system/overview.md` | One per system |
| C4/context/container/deployment view | Да (convention/section template) | Architecture view | По concern |
| Domain overview | Да | domain README/overview | Per real domain |
| Durable capability spec + scenarios | Да | capability spec | Если behavior contract useful |
| Glossary term | Да | domain glossary | Context-dependent |
| Entity/data concept | Да | entity doc + actual schema refs | Значимые concepts |
| System/domain data view | Да | `data.md` + linked source contracts | Если data concern material |
| Flow and branch/path table | Да | flow doc | Значимые flows |
| Business rule set/table | Да | grouped `rules.md`/DMN when justified | Если separate reusable rules |
| Integration / API / event reference | Да | linked OpenAPI/AsyncAPI/IDL | Material integration |
| Cross-cutting concept | Да | cross-cutting note | Only cross-domain invariant |
| Quality scenario | Да | quality view/SLO/test refs | Agreed quality concern |
| Security/threat record | Да | security view/threat model | Trust/risk concern |
| Constraints, risks, debt | Да | grouped register | Material risks only |
| Deployment/operations | Да | view over IaC/SLO/runbooks | When concerns justify |
| Verification map | Да | test suite + evidence refs | If mapping not discoverable |
| ADR/MADR | Да | one decision per ADR | Significant decisions |
| Change delta | Да | task stage delta until accepted | Only for relevant task stages |
| Frontmatter/index | Draft JSON schema + sample | JSON Schema and generated index | Need validator fixtures |

### Leftover contracts that must be resolved before implementation

1. Exact `schemas/document.schema.json` and `schemas/index.schema.json` must be materialized from the draft examples, then validated by a real Draft 2020-12 implementation.
2. A fixture set must cover every type, every status branch, decision-specific metadata, system vs domain docs, references, duplicates, missing fields and invalid YAML. Examples must include actual v1.1 Markdown documents, not only blank templates.
3. Confirm exact `domains` and `release ID` registry, docs-root mount and owners. They cannot be safely fabricated in a generic design.
4. Pick actual Markdown renderer/parser and pinned versions; confirm GFM table, Mermaid block и link-check behavior match the declared profile.
5. Define how literal source refs map between docs repo and multiple product repos (aliases/path normalization); references must remain unambiguous and avoid hardcoded local machine paths.
6. Resolve whether external task refs are structurally checked only or live-validated via an explicitly invoked adapter. A disconnected external tracker should not make local docs validation flaky.
7. Tabletop walkthrough should test combinations: small bug/no architecture change, new capability with entity/flow, API/event compatibility change, data migration/privacy change, proposal rejected, task relink/backport across releases, and docs-only change.

These are contract completion/validation items, not reasons to run a practical agent pilot now.

---

## 6. Changes applied to `doc.architecture.md`

1. Changed the version/status to v1.1 and labelled it as a detailed draft, not an implemented/validated system.
2. Added explicit Spec Kit/OpenSpec comparison and separated long-lived current behavior specs from task deltas.
3. Added `capability-spec` и acceptance scenario structure.
4. Added data architecture и domain data contract coverage: sources, ownership, lifecycle, consistency, classification/privacy, retention и migrations, where relevant.
5. Added exact term/glossary record format.
6. Added full type registry и templates для system/domain/view/capability/glossary/entity/data/flow/rules/integration/cross-cutting/quality/security/risks/deployment/verification/ADR/task delta.
7. Added concrete Draft 2020-12 frontmatter schema и generated `index.json` example; corrected document status vs ADR decision status.
8. Added structured `source_refs` (repository alias, relative path, optional symbol/pointer/revision) to preserve compatibility with a future code-scanning documentation producer, while keeping scan runs/evidence и semantic approvals separate.
9. Added stronger retrieval/access и quality consistency requirements для agents.
10. Kept no-pilot, single-agent core, canonical `task.json`, root-manifest и direct Markdown edit constraints; explicitly marked the future scanner как отдельный out-of-scope program.

The original root manifest was not copied и не был тихо изменён. Transfer back into that root manifest — separate explicit update, since this user turn requested an audit/revision of the architecture design document.

---

## 7. Research sources

### Primary / official sources

- [OpenSpec Getting Started](https://openspec.dev/docs/getting-started) — current vs delta specs, proposal/apply/sync/archive lifecycle.
- [OpenSpec spec-driven schema](https://openspec.dev/docs/schemas/spec-driven) — proposal, one delta spec per capability, ADDED/MODIFIED/REMOVED, optional design, task artifact.
- [OpenSpec CLI](https://openspec.dev/docs/cli) — explicit list/show/validate/archive surface; most workflow decisions remain in agent skill.
- [GitHub Spec Kit Agentic SDD reference](https://github.github.io/spec-kit/reference/agentic-sdd.html) — specification, clarification, planning, checklist, tasks, analysis and implementation; quality gates are optional based on ambiguity.
- [GitHub Spec Kit Quickstart](https://github.github.io/spec-kit/quickstart.html) — explicit behavior/intent before implementation and artifact validation.
- [ISO/IEC/IEEE 42010:2022 official page](https://www.iso.org/standard/74393.html) — architecture-description structure/concepts; no prescribed file format/tool.
- [arc42 template](https://docs.arc42.org/home/) — broad architecture topic checklist and lean/thorough guidance.
- [C4 diagrams](https://c4model.com/diagrams) — scoped hierarchical views; not all levels needed.
- [MADR](https://adr.github.io/madr/) — lightweight decision record format.
- [Diátaxis](https://diataxis.fr/) — four reader documentation needs; used only for people-facing docs.
- [JSON Schema 2020-12](https://json-schema.org/specification), [YAML 1.2.2](https://yaml.org/spec/1.2.2/), [CommonMark](https://commonmark.org/), [OpenAPI official index](https://spec.openapis.org/oas/), и [AsyncAPI 3.0.0](https://www.asyncapi.com/docs/reference/specification/v3.0.0) — format/contract references.
- OpenAI [Harness Engineering](https://openai.com/index/harness-engineering/) — practitioner report on repository-local knowledge, maps and CI checks; non-normative.

### Method limitations

This is a design audit, not independent product evaluation. There was no existing product repo/schema/CI/workflow to validate against, no stakeholder interviews, no security or data-governance assessment, no empirical token comparison, no pilot, и no executable specification implementation. Recommendations should be adapted when the real system-of-interest, owners, release policy, source contracts и toolchain are known.

---

## 8. Реализованный CLI и task-conf (v1.2)

Ключевой вывод аудита v1.1 — «CLI/schema ещё не реализованы» — устранён. На момент v1.2 внедрено:

### 8.1 task-conf иерархическая конфигурация

`doc/config/task-conf/types/<type>/` — каждый тип задачи как папка с `config.yaml` (поля, `allowed_flows`, `subtask_policy`, `close_policy`, `complexity_allowed`) и `prompt.md` (стартовый промпт агента). Внутри `flows/<flow>/` — `config.yaml` (шаги, gate) и `prompt.md` (стартовый промпт flujo).

Зарегистрировано 9 типов задач и 11 flujo. Тип `jira-incoming` — для входящих задач из Jira с единственным flujo `jira-process`.

### 8.2 task.json — поля, добавляемые структурой task-conf

- `task_type` — валидируется против `project.task_types` из `paths.yaml`.
- `flow` — валидируется против `allowed_flows` типа в task-conf.
- `complexity` — валидируется против `complexity_allowed` типа.
- `subtasks` — массив `{id, title, status, path}`; `subtask_policy` (`required`/`optional`/`forbidden`) проверяется.
- `implementation_plan`, `research_docs` — требуются для типов, где указано в `required_fields`.

### 8.3 Валидация полностью конфиг-driven

`arch task validate <task_key>` загружает все правила из YAML-конфигов:
- `doc/config/paths.yaml` (секция `project`): `task_types`, `phases`, `risk_levels`, `source_types`, базовые `task_schema_required_fields`.
- `doc/config/task-conf/types/<type>/config.yaml`: `required_fields`, `allowed_flows`, `complexity_allowed`, `subtask_policy`, `close_policy`.

В Python-коде нет хардкода enum'ов, обязательных полей или допустимых значений — всё читается из конфига.

### 8.4 CLI команды

| Команда | Назначение |
|---------|-----------|
| `arch task types` | Список всех типов задач из task-conf |
| `arch task flows --type <type>` | Разрешённые flujo для типа |
| `arch task type-prompt --type <type>` | Стартовый промпт типа |
| `arch task flow-prompt --type <type> --flow <flow>` | Стартовый промпт flujo |
| `arch task decompose <key> --subtask-id NNNN --subtask-title "..."` | Создание подзадач |
| `arch task diagnose <key>` | Гант-подобная диагностика с блоками закрытия |
| `arch task close <key>` | Закрытие — отказ если есть незакрытые подзадачи |
| `arch docs paths --check` | Детектор мусора: файлы вне `allowed_paths`, frontmatter, типы, статусы |

### 8.5 Исследовательская папка `research/`

`doc/tasks/<task_key>/research/<slug>.md` — свободные Markdown-документы для гипотез, ссылок на код и интернет. Связь с задачей через поле `research_docs` в `task.json` (`id`, `title`, `path`, `source_type: web|code|internal`, `source_ref`, `summary`, `status: hypothesis|confirmed|rejected|archived`).

### 8.6 Контроль закрытия задач

Задача с `close_policy: all_subtasks_required` закрывается только если все подзадачи имеют `phase: completed`. `arch task close` отказывает с ненулевым exit code и перечисляет блокеры.