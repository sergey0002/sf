# Хранение и оформление спецификаций: docs-as-code

Спецификация в SDD — это файл в репозитории, а не страница в wiki. Этот файл разбирает,
где и как хранить спеки, в каких форматах, как их версионировать, рендерить и проверять.

## 1. Принцип docs-as-code

Документация обрабатывается как код:

| Принцип | Реализация |
|---|---|
| Plain text | Markdown (.md) — diff'ится, grep'ится, мерджится |
| Версионный контроль | Git: история, blame, ветки, PR-ревью |
| Ревью | Pull requests — спеки ревьюятся как код |
| CI | Линтеры Markdown, link checkers, валидаторы схем, тесты на документацию |
| Генерация | Статический сайт из Markdown (MkDocs, Docusaurus, Sphinx, Hugo, Antora) |
| Диаграммы как код | Mermaid, PlantUML, C4 — диаграммы в текстовом виде, версионируются |
| Автоматизация | Хуки, скрипты генерации (adr-tools, spec-kit scripts) |

**Почему не wiki/Confluence:** документы в wiki дрейфуют от кода, не версионируются
вместе с ним и недоступны агентам как контекст. Спека, живущая рядом с кодом, всегда
в одном коммите с изменениями, которые она описывает.

## 2. Форматы

| Формат | Применение |
|---|---|
| **Markdown** | Основной формат спек, ADR, конституций, proposal, tasks |
| **OpenAPI / JSON Schema** | Машиночитаемые контракты API (`contracts/api-spec.json`) |
| **YAML** | Конфигурация (openspec/config.yaml, .openspec.yaml), задачи с тегами маршрутизации |
| **Mermaid** | Диаграммы в Markdown: sequence, ER, flowchart, C4 |
| **PlantUML** | Богатые UML-диаграммы, рендерятся в CI |
| **Gherkin (.feature)** | Исполняемые сценарии приёмки |
| **AsciiDoc** | Альтернатива Markdown в enterprise (docToolchain, Antora) |

## 3. Структура репозиториев по инструментам

### GitHub Spec Kit
```
project/
├── .specify/
│   ├── memory/constitution.md      # принципы проекта
│   ├── templates/                  # шаблоны артефактов
│   └── scripts/                    # автоматизация (.sh/.ps1)
├── specs/
│   └── 001-feature-name/           # одна папка на фичу, префикс-номер
│       ├── spec.md
│       ├── plan.md
│       ├── tasks.md
│       ├── data-model.md
│       ├── research.md
│       ├── quickstart.md
│       ├── contracts/
│       └── checklists/
└── .github/prompts/                # промпты по фазам
```

### Kiro
```
project/
├── .kiro/
│   ├── specs/<name>/
│   │   ├── requirements.md         # или bugfix.md
│   │   ├── design.md
│   │   └── tasks.md
│   └── steering/                   # контекст проекта
└── AGENTS.md
```

### OpenSpec
```
project/
├── openspec/
│   ├── specs/<domain>/spec.md      # текущее состояние системы
│   ├── changes/<change-name>/
│   │   ├── proposal.md
│   │   ├── design.md
│   │   ├── tasks.md
│   │   └── specs/<domain>/spec.md  # дельта
│   ├── changes/archive/<date>-<name>/   # история
│   └── config.yaml
```

### ADR
```
docs/adr/
├── README.md                       # индекс (decision log)
├── 0001-record-architecture-decisions.md
├── 0007-use-postgresql-for-orders.md
└── ...
```

## 4. Соглашения об именовании

| Сущность | Конвенция | Пример |
|---|---|---|
| Фича (Spec Kit) | `NNN-kebab-case` | `001-model-routing/` |
| Изменение (OpenSpec) | kebab-case глагольная фраза | `add-dark-mode/` |
| ADR | `NNNN-title-with-dashes.md` | `0007-use-postgresql-for-orders.md` |
| Архив OpenSpec | `<date>-<name>` | `2025-01-24-add-dark-mode/` |
| Спека Kiro | kebab-case | `.kiro/specs/user-auth/` |
| Домены OpenSpec | по capability | `specs/auth/`, `specs/payments/` |

Номера ADR дают хронологию и удобные ссылки («см. ADR-7»). Нумерация спек Spec Kit
последовательная — при параллельной работе нескольких людей возможны коллизии;
рекомендуется префикс с датой или веткой.

## 5. Версионирование и жизненный цикл

- **Git — единственный источник истории.** Спеки коммитятся вместе с кодом; PR объединяет
  изменение спеки и кода в одну атомарную единицу.
- **Immutable checkpoints:** после утверждения spec.md/plan.md не переписываются;
  изменения — только добавления (clarifications, refinements).
- **ADR — append-only журнал:** принятое решение не редактируется; отмена — новый ADR
  со статусом «Superseded by ADR-XXXX», старый помечается как superseded.
- **OpenSpec archive:** дельты сливаются в живые спеки, папка изменения уходит в
  `changes/archive/` — аудит истории без мусора в актуальных спеках.
- **Конституция:** версионируется отдельно; изменения — PR с обоснованием и bump версии.
- **Semantic versioning** для публичных API: изменения контрактов требуют bump версии.

## 6. Организация документации: Diátaxis

Фреймворк Daniele Procida (2017) для структуры документации по потребностям читателя.
Отвечает на вопрос «что писать», docs-as-code — «как доставлять».

| Тип | Назначение | Пример в SDD-контексте |
|---|---|---|
| **Tutorials** | Обучение через практику | «Ваша первая спека за 5 минут» |
| **How-to guides** | Решение конкретной задачи | «Как написать delta spec» |
| **Reference** | Точные факты о механизме | Справочник команд `/speckit.*`, параметры CLI |
| **Explanation** | Контекст и понимание | «Почему конституция существует», ADR |

## 7. Публикация: генераторы сайтов

| Генератор | Формат | Особенности |
|---|---|---|
| **MkDocs (+ Material)** | Markdown | Самый дешёвый старт, один YAML, поиск, тёмная тема |
| **Docusaurus** | MDX | React-экосистема, версионирование документации |
| **Sphinx** | reStructuredText/MyST | Python-экосистема, автогенерация API-документации |
| **Hugo** | Markdown | Скорость, Go-экосистема |
| **Antora** | AsciiDoc | Мультирепозиторная документация, enterprise |

Типовой пайплайн: push в main → CI собирает сайт → деплой на GitHub Pages/Netlify.
ADR-папка публикуется как отдельный раздел сайта для доступа не-инженеров (PM, security,
аудиторы), которые не ходят лазить по приватному репозиторию.

## 8. Диаграммы как код

- **Mermaid** — sequence, flowchart, ER, state, C4; рендерится прямо в GitHub и MkDocs.
- **PlantUML** — полный UML; рендер в CI (plantuml.jar) или через сервер.
- **C4 Model** — 4 уровня абстракции (Context, Container, Component, Code) для архитектуры;
  связывается с ADR: решение ссылается на затронутые контейнеры/компоненты.
- **Structurizr** — C4 как код с экспортом диаграмм.

Правило: диаграмма, которую нельзя обновить за 5 минут, устареет. Текстовая диаграмма
обновляется в том же PR, что и код.

## 9. CI-проверки документации

| Проверка | Инструмент | Что ловит |
|---|---|---|
| Линт Markdown | markdownlint, prettier | Стиль, форматирование |
| Битые ссылки | lychee, linkchecker | Мёртвые ссылки в спеках |
| Валидация OpenAPI | spectral, openapi-spec-validator | Корректность контрактов |
| Структура OpenSpec | `openspec validate` | Корректность дельт (ADDED/MODIFIED/REMOVED) |
| Структура Spec Kit | check-prerequisites.sh | Наличие конституции, spec, plan, tasks |
| Тесты на документацию | pytest/mkdocs-macros | Примеры кода в доках работают |
| Spell check | codespell, cspell | Опечатки |

## 10. Monorepo vs polyrepo

- **Monorepo:** спеки рядом с кодом каждого сервиса (`services/x/specs/`) + корневые
  `docs/adr/`, `openspec/` для кросс-сервисных решений. Плюс: атомарные коммиты.
  Минус: навигация в большом репозитории.
- **Polyrepo:** спеки в репозитории сервиса; кросс-репо решения — в отдельном
  architecture-репозитории, на который ссылаются из AGENTS.md/CLAUDE.md каждого проекта.
  Важно: один авторитетный источник на решение, а не копии.

**Доступность для агентов:** указатель в `AGENTS.md`/`CLAUDE.md` на индекс ADR и спеки
домена — агент читает применимые решения перед изменением границы. Указатель должен быть
конкретным (решения по бронированию для изменения бронирования), а не «читай все документы».

## 11. Антипаттерны хранения

- Спеки в Confluence/wiki без зеркала в Git → дрейф от кода.
- Переписывание spec.md задним числом → потеря истории; только аддитивные изменения.
- ADR, редактируемые после принятия → потеря аудита решений.
- Диаграммы картинками (PNG) в репозитории → нельзя diff'ить и обновлять.
- Одна гигантская спека на весь продукт → разбить по доменам (OpenSpec) или фичам (Spec Kit).
- Спека без владельца → назначить owner в атрибутах требования (ISO 29148).

---

## Источники

- Sourcegraph — Docs as Code: A Practical Guide
- Diátaxis: https://diataxis.fr/
- OpenSpec docs (getting-started, writing-specs)
- Spec Kit — структура .specify/ и specs/
- ADR best practices: docsio.co, catio.tech, withstoa.com
- C4 Model: https://c4model.com/
