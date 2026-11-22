# Архитектурные знания — ориентированные на агента

Этот каталог — лёгкий пример документации, ориентированной на домены. Он фиксирует предполагаемые границы из одного корневого манифеста, а не реализованную фабрику. Будущий производитель документации (сканер кода) — внешний возможный участник; он не входит в текущее ядро. Каноническая архитектура — нейтральный к производителю Markdown с коротким YAML frontmatter и явными ссылками/ID. Производители могут предлагать изменения, но проверка/принятие контролирует достоверность.

## Начать здесь

- [Обзор системы](system/overview.md) — архитектурная ориентация.
- [Индекс системы](index.json) — сгенерированная компактная карта метаданных; перестроить с помощью `python3 doc/tools/arch/__main__.py index build`.
- `python3 doc/tools/arch/__main__.py docs tree` — JSON-оглавление всех индексируемых Markdown-записей по каталогам.
- [Адресуемые контракты документации](system/addressable-contracts.md) — стабильные якоря разделов, ограниченное чтение, поиск, контекст задачи и влияние изменений.
- [Глоссарий](glossary.md) — словарь задач и архитектурной терминологии.
- [Политика номеров задач](system/task-number-registry.md) — CLI-реестр, выделение UI-номеров и правила коллизий.

## Навигация по доменам

- [Task intake](domains/task-intake/README.md)
- [Task lifecycle](domains/task-lifecycle/README.md)
- [Project knowledge](domains/project-knowledge/README.md)
- [Execution and verification](domains/execution-verification/README.md)
- [Model routing](domains/model-routing/README.md)

## Навигация по точкам зрения

- [Context](system/context.md)
- [Components](system/components.md)
- [Data and records](system/data.md)
- [Quality attributes](system/quality.md)
- [Security and trust boundaries](system/security.md)
- [Constraints and risks](system/constraints-risks.md)

## Протокол для читателя/агента

1. Начните с [architecture-read](../skills/architecture-read/SKILL.md). При известном ключе сначала возьмите ID и ссылки из карточки. Используйте эту карту, когда домен ещё неизвестен.
2. Уточните расположение и статус записи через `arch list --id <id> --json` либо фильтр по домену и типу. Для вопроса по термину используйте `arch docs search <query> --json`, для точного правила — `arch docs read <DOC-ID#section-id> --json`, для задачи — `arch docs context --task <key> --case <CASE-N> --json`. Для конкретного пробела используйте ссылки или `related` на глубину 1.
3. Свяжите извлечённое правило со сценарием приёмки. Черновики дают контекст, принятые решения подтверждают договорённость, проверка реализации показывает фактическое поведение.
4. При изменении канонического правила следуйте [architecture-docs](../skills/architecture-docs/SKILL.md).

## Соглашения о записях

- Один сфокусированный архитектурный факт/поток/возможность/сущность/решение на страницу там, где это полезно.
- Стабильный uppercase `id`, lowercase `type`, краткий `summary`, жизненный цикл `status` и `domain` в YAML frontmatter.
- `related` содержит точные ID; обычные относительные ссылки Markdown обеспечивают навигационный контекст.
- JSON Schema используется для frontmatter/index/подобных task машинных контрактов; Markdown каноничен для повествовательной архитектуры. `index.json` генерируется только.
- Избегайте дублирования принятого факта на нескольких страницах; ссылайтесь на его каноническую страницу.

## Статус

Всё в этом scaffold — черновик примера документации, а не 증거 рабочего CLI, системы задач, интеграции, развертывания или CI. Неизвестные варианты перечислены в [constraints and risks](system/constraints-risks.md).
