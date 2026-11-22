---
id: ROOT-moc
type: moc
title: Корневое оглавление агентной software factory
summary: "Карта контента (Map of Content) всей песочницы: энциклопедии, исследования, манифест и пример-саффолд simple. Индекс-прежде-всего: сначала смотрите этот файл и section-оглавления, потом открывайте только нужные документы. Для агента и человека."
status: current
domain: system
version: 0.1
related:
  - doc.architecture.md
  - doc.architecture-audit.md
  - Исследование software factory — пробелы и готовые практики.md
  - Манифест агентной software factory.md
---

# 🗂 Корневое оглавление агентной software factory

## Как пользоваться этим оглавлением (индекс-прежде-всего)

Этот файл — единственная точка входа. Навигация рассчитана на агента: чтение идёт от общего к частному, без необходимости перечитывать всю историю.

1. **Сначала это оглавление** — определите, какая область отвечает на ваш вопрос (см. разделы ниже).
2. **Затем входной документ области** — `Главная.md`, `Индекс.md`, `AGENTS.md` или `README.md` внутри папки. Каждый содержит свой `summary` в frontmatter и `related`-связи.
3. **Переходите по ссылкам** — стиль Obsidian `[[путь/к/файлу|alias]]`; открывайте документ и читайте его frontmatter (`id`, `type`, `status`, `summary`), чтобы решить, нужен ли он вам.
4. **Статусы:** `current` — актуально, `draft` — черновик, не окончательное решение, `superseded` — заменено.

> **Принципы:** сеть связей, а не иерархия (Obsidian); документация пишется сначала для агента, потом для человека (Karpathy); каждый документ имеет стабильный `id`, тип и статус; смысловые решения принимаются человеком/владельцем, а не выводятся из ссылок автоматически.

---

## 📄 Корневые документы песочницы (не в `data/`)

Хранятся в корне песочницы, не копируются в энциклопедии.

- [[Манифест агентной software factory.md|Манифест агентной software factory]] — единственный корневой манифест (`status: draft`), принципы, четыре слоя, контракт `task.json`, разделение CLI/агент, роли. `id: MAN-manifesto`.
- [[doc.architecture.md|Целевая модель `.doc/architecture`]] — детальный контракт хранения, форматы, типы артефактов, CLI. `id: ARCH-architecture`.
- [[doc.architecture-audit.md|Аудит архитектуры]] — результаты глубокого аудита, сравнительная матрица, остаточные contract gaps.
- [[Исследование software factory — пробелы и готовые практики.md|Исследование: пробелы и готовые практики]] — исследовательская заметка с аудитом энциклопедий и пробелами модели.

---

## 📚 `data/cli-skills-encyclopedia` — навыки CLI-агентов

**Назначение:** описание навыков (skills) для агентов, работающих с CLI: структура скилла, прогрессивное раскрытие, фронтенд-контракты, примеры.

**Входные документы:**
- [[data/cli-skills-encyclopedia/Главная.md|Главная — cli-skills]] — входная страница энциклопедии.
- [[data/cli-skills-encyclopedia/Глоссарий.md|Глоссарий — cli-skills]] — термины навыков и CLI.
- [[data/cli-skills-encyclopedia/Справочник форматов.md|Справочник форматов — cli-skills]] — форматы файлов и конвенции.

---

## 🏗 `data/machinedocs-encyclopedia` — документация fabricatedocs (машино-доки)

**Назначение:** ядро архитектурной документации фабрики: AGENTS.md для агентов, журнал изменений, индекс, глассарий, разделы Архитектура/Документация/Практики/Форматы/Примеры.

**Входные документы:**
- [[data/machinedocs-encyclopedia/AGENTS.md|AGENTS.md — machinedocs]] — инструкция для агентов, работающих с этой базой знаний.
- [[data/machinedocs-encyclopedia/Главная.md|Главная — machinedocs]] — входная страница.
- [[data/machinedocs-encyclopedia/Индекс.md|Индекс — machinedocs]] — машинный индекс документов.
- [[data/machinedocs-encyclopedia/Журнал.md|Журнал — machinedocs]] — история изменений базы знаний.
- [[data/machinedocs-encyclopedia/Глоссарий.md|Глоссарий — machinedocs]] — термины factory (task.json, task key, source adapter, skill и др.).
- [[data/machinedocs-encyclopedia/Справочник форматов.md|Справочник форматов — machinedocs]].

**Подразделы:** Архитектура, Документация, Практики, Форматы, Примеры — см. `[[data/machinedocs-encyclopedia/Главная.md]]`.

---

## 🏗 `data/sdd-encyclopedia` — стандарты SDD

**Назначение:** энциклопедия Specification-Driven Development: сущности, процессы, инструменты, стандарты, флоу, справочник сущностей.

**Входные документы:**
- [[data/sdd-encyclopedia/Главная.md|Главная — sdd]] — входная страница.
- [[data/sdd-encyclopedia/Глоссарий.md|Глоссарий — sdd]] — термины SDD.
- [[data/sdd-encyclopedia/Справочник сущностей.md|Справочник сущностей — sdd]] — канонические сущности домена.

---

## 🔬 `data/sdd-research` — исследования SDD (12 заметок)

**Назначение:** цикл исследовательских заметок по SDD: от сущностей и стандартов требований до внедрения в CI/CD и безопасности.

**Все заметки:**
1. [[data/sdd-research/01-сущности-sdd.md|01 — сущности SDD]]
2. [[data/sdd-research/02-стандарты-и-форматы-требований.md|02 — стандарты и форматы требований]]
3. [[data/sdd-research/03-инструменты-и-фреймворки.md|03 — инструменты и фреймворки]]
4. [[data/sdd-research/04-хранение-docs-as-code.md|04 — хранение docs-as-code]]
5. [[data/sdd-research/05-шаблоны.md|05 — шаблоны]]
6. [[data/sdd-research/06-качество-и-трассируемость.md|06 — качество и трассируемость]]
7. [[data/sdd-research/07-история-и-эволюция.md|07 — история и эволюция]]
8. [[data/sdd-research/08-контекст-инженерия-агентов.md|08 — контекст-инженерия агентов]]
9. [[data/sdd-research/09-bdd-исполняемые-спеки.md|09 — BDD, исполняемые спеки]]
10. [[data/sdd-research/10-внедрение-sdd-в-команду.md|10 — внедрение SDD в команду]]
11. [[data/sdd-research/11-sdd-в-ci-cd.md|11 — SDD в CI/CD]]
12. [[data/sdd-research/12-безопасность-в-спеках.md|12 — безопасность в спеках]]
- [[data/sdd-research/README.md|README — sdd-research]] — обзор цикла.

---

## 🏭 `data/simple` — пример-саффолд агентной software factory

**Назначение:** documentación/инструментальный пример, не рабочая фабрика. Единая папка `doc/` с архитектурой (`.doc/` слита в `doc/` по требованию), тасками, скиллами, CLI и тестами.

**Структура `simple/doc/`:**
- `architecture/` — архитектурная документация (domains, system, schemas, glossary, index.json).
- `skills/` — черновики скиллов: `create-task`, `go-to-task`, `задокументируй`.
- `tasks/UI-0001/` — пример задачи: `task.json`, `stage1/plan.md`, `stage1/verification.json`.
- `tests/` — приёмочные тесты среды (`run.sh`).
- `tools/` — детерминированный CLI `arch.py` (list/show/index/validate/task-key) и юнит-тесты.

**Ключевые файлы:**
- [[data/simple/README.md|README — simple]] — статус саффолда и границы.
- [[data/simple/doc/tasks/UI-0001/task.json|task.json UI-0001]] — единственный canonical task input примера (`source.type: ui`, `task_number: 0001`, `task_key: UI-0001`).
- [[data/simple/doc/tasks/UI-0001/stage1/plan.md|планステージ 1]] — план исполнения задачи UI-0001.
- [[data/simple/doc/tools/arch.py|arch.py CLI]] — детерминированная архитектурная CLI.

Связано: [[Манифест агентной software factory.md|Манифест]] (не копируется в `simple/`), [[doc.architecture.md]].

---

## 🤖 `data/subagents-encyclopedia` — саб-агенты

**Назначение:** энциклопедия паттернов и сред для мультиагентных систем (в текущем ядре фабрики — один агент; саб-агенты — возможное будущее расширение).

**Входные документы:**
- [[data/subagents-encyclopedia/Главная.md|Главная — subagents]]
- [[data/subagents-encyclopedia/Глоссарий.md|Глоссарий — subagents]]
- [[data/subagents-encyclopedia/Справочник сред.md|Справочник сред — subagents]]

---

## 🔗 Перекрёстные связи (кратко)

| Область | Связано с | Смысл |
|---|---|---|
| `Манифест` | `doc.architecture.md`, `simple/`, все энциклопедии | Единственный корневой контракт; все области ссылаются на него, копии не создаются. |
| `doc.architecture.md` | `data/machinedocs-encyclopedia/` | Контракт хранения ссылается на базу знаний machinedocs. |
| `sdd-research` | `sdd-encyclopedia`, `Манифест` | Исследования опираются на стандарты SDD и корневой манифест. |
| `simple/` | `Манифест`, `doc.architecture.md` | Саффолд выводит описание из корневого манифеста; копия манифеста туда не помещается. |

---

## 🏷 Легенда статусов и типов

- **Статус документа:** `draft` (черновик) → `current` (актуально) → `deprecated` → `superseded` (заменено, в `superseded_by` указано новое).
- **Тип документа (`type`):** `moc`, `manifest`, `architecture-view`, `domain`, `capability-spec`, `glossary`, `entity`, `flow`, `rule-set`, `integration`, `decision`, `task`, `skill`, `research`.
- **Frontmatter** на каждой странице: `id`, `type`, `title`, `summary`, `status`, `domain`, `related` — читается агентом перед чтением тела документа.

---

> Это оглавление — derivadaя карта, не источник истины. Источник истины для задач — `task.json`; для архитектурных решений — корневой манифест и `.doc/architecture/`; изменения вносятся владельцами областей с последующим обновлением связей здесь.
