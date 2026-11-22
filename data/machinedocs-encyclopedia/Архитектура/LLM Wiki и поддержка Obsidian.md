---
title: "LLM Wiki и поддержка Obsidian"
description: "Загружайте при проектировании, ingest, навигации или lint долгоживущей Markdown-базы знаний, которую поддерживают LLM-агенты."
paths: []
tags: [архитектура, llm-wiki, obsidian, agents]
aliases: ["LLM Wiki", "Karpathy LLM Wiki", "Поддержка Obsidian агентами"]
---

# LLM Wiki и поддержка Obsidian

> [!abstract] Кратко
> Karpathy описывает паттерн, где агент накапливает знания в связанном Markdown wiki, интегрирует новые
> источники в существующие заметки и регулярно проверяет ссылки, пробелы и противоречия. В этом vault
> паттерн применён как Obsidian + тематические документы + `Индекс.md` + `AGENTS.md` + журнал + lint;
> исходные публикации представлены provenance-ссылками, а не локальным неизменяемым архивом.

## Первичный источник и границы интерпретации

- Andrej Karpathy, **LLM Wiki** (idea file, 2026-04-04): https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- В gist описаны три слоя: curated raw sources (неизменяемые), LLM-maintained wiki и schema/instructions.
- Основные операции: ingest нового источника с обновлением нескольких связанных страниц; query с citations;
  периодический lint (contradictions, stale claims, orphan pages, missing concepts/links).
- `index.md` описан как content-oriented каталог страниц с одной строкой summary; `log.md` — хронологический
  append-only журнал. Имена этих файлов — предложение/пример для паттерна, не спецификация Obsidian.
- Gist подчёркивает, что это idea file / абстрактная схема, а не нормативный стандарт и не controlled study.
  Применение к данному vault является осознанным implementation choice.

## Реализация в этой энциклопедии

| Роль паттерна | Локальный артефакт | Правило |
|---|---|---|
| Entry point для человека | [[Главная]] | Тематические разделы, Mermaid карта, curated стартовые страницы |
| Полный content index для агента | [[Индекс]] | Одна строка trigger-description на страницу; links относительны от root vault |
| Schema / agent rules | [[AGENTS.md]] | Как искать, создавать, цитировать, линковать и проверять заметки |
| Entity/term index | [[Глоссарий]] | Краткие определения → canonical article, без дублирования статей |
| Append-only event trace | [[Журнал]] | Дата, ingest/lint/update type, короткий результат |
| Link / metadata lint | `scripts/lint_wiki.py` | Broken wikilinks, локальные relative Markdown links, frontmatter, H1, orphan checks, index coverage |
| Index refresh | `scripts/build_index.py` | Rebuild и `--check` для detection of stale index |
| Thematic synthesis | Папки `Практики/`, `Архитектура/`, `Документация/` | Canonical pages, explicit sources, limits, related links |

### Что не реализовано буквально

- **Нет raw-source archive directory.** Внешние публикации цитируются URL/DOI в исследовательских страницах;
  URL могут устареть, а содержимое источника не захвачено и не заморожено в vault. Для критичных/часто
  используемых источников можно отдельно добавить локальные разрешённые PDF/HTML captures с датой и
  лицензией, не переписывая оригиналы.
- **Не каждое чат-сообщение становится отдельной заметкой.** В vault заносятся устойчивые результаты,
  решения, методологии и проверяемые выводы; transient discussion не превращается в вечную инструкцию.
- **Wiki-страницы не считаются source of truth для исполняемого кода.** Для code/runtime claims указывать
  repo path + commit/trace/test, когда они доступны; производные выводы отделять от evidence.
- **Генерация индекса не означает истинность текста.** Linter проверяет механическую связность и формат,
  не подтверждает правильность external claims, качество evidence или логическую корректность рекомендации.

## Инструкции для агентного ingest

1. Прочитай [[Индекс]], затем релевантные canonical pages, а не загружай весь vault.
2. Сохрани источник как URL/DOI и его bibliographic/source type; локальный архив добавляй только с правом хранения.
3. Извлеки claims с source pointers; отдельно укажи method-owner/vendor/case/peer-reviewed статус, область,
   ограничения и уверенность. Не своди рекомендации/интерпретации с первичным результатом.
4. Обнови самую подходящую canonical note; создай новую только если понятие/синтез не помещается без
   дублирования. Обнови backlinks/ссылки, глоссарий для устойчивых терминов, `Индекс.md`, `Журнал.md`.
5. Отдельно пометь contradiction/conflict между sources с датой/версией; не стирай устаревшее утверждение,
   пока его статус и замена не описаны.
6. Проверь `python3 scripts/build_index.py --check` и `python3 scripts/lint_wiki.py`; при ошибке исправь источник,
   а не отключай проверку.
7. Финально сообщи новые/изменённые страницы, добавленные источники, уверенность/ограничения и lint results.

## Правила навигации в Obsidian

- `[[wikilinks]]` дают концептуальные переходы/backlinks и отображаются в graph. Уникальные имена заметок
  поддерживают короткую ссылку; в index и при неоднозначности используются relative Markdown paths.
- Index — full list; Главная — curated MOC; Glossary — ontology entry; related links — local semantic neighborhood.
  Эти роли дополняют, а не заменяют друг друга.
- У каждого нового термина должен быть либо `[[Глоссарий]]` definition, либо inline definition в canonical page;
  новый документ должен быть достижим из индекса и связан с соседними понятиями.
- Link quantity не цель: прямые связи отражают предметную/операционную связь, а не просто совпадение слова.

## Масштаб и стоимость контекста

В исходном gist заявлено, что для умеренного масштаба индекс помогает навигации без embedding RAG; это личное
описание паттерна, не универсальный capacity benchmark. По мере роста vault контролировать размер индекса,
поиск, дубль/устаревание и budget. Добавляй поисковый инструмент только после измеримого поиска-узкого места;
периодически проверяй recall/precision навигации и cost. Не расширяй always-on контекст множеством
глобальных инструкций и повторов.

## Связи

- [[Главная]] · [[Индекс]] · [[AGENTS.md]] · [[Журнал]] · [[Глоссарий]] · [[Frontmatter-схемы]] · [[Index-First подход]] · [[Docs-as-Code и CI]] · [[Актуальность и staleness]] · [[Структурированный Markdown]] · [[Семантический чанкинг]] · [[Управление контекстом многоагентных систем]]
