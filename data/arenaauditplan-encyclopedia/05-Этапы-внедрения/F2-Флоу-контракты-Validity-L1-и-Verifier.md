---
id: "AAP-STAGE-F2"
title: "Этап F2 (2 недели): Формальные контракты *.flow.json, Validity L1 и независимый Verifier"
description: "Пошаговый план этапа F2 с карточками задач TASK-F2-01..05: внедрение arch-flow.schema.json (DMN UNIQUE/COLLECT), дельт flow-delta.json, контроля устаревания Validity L1 и детерминированного analyze."
status: "canonical"
track: "both"
stage: "F2"
paths: ["flowjson.md", "doc/tools/arch/flows.py", "doc/tasks/UI-0029/", "taskcontrol.md"]
tags: [этап-f2, план-внедрения, flow-json, dmn, validity-l1, suspect-links, verifier, analyze]
aliases: ["F2 Флоу-контракты Validity L1 и Verifier", "Этап F2"]
---

# Этап `F2` (`2 недели`): Формальные контракты `*.flow.json`, `Validity L1` и независимый `Verifier`

> [!abstract] Паспорт этапа `F2`
> - **Трек:** `both` (формализация поведенческих контрактов и контроль устаревания задач в ядре + интеграция с графом кода и субагентом `verifier`).
> - **Закрываемые проблемы:** `PROB-03, PROB-09, PROB-15, PROB-18, PROB-30`.
> - **Реализуемые требования:** `R11, R12`.
> - **Зависимости:** `F0` и `F1`.

---

## Задачи этапа (готовые шаблоны для `arch task new`)

### TASK-F2-01 — Декомпозиция крупных модулей CLI и реализация `arch docs flow validate / build` (`UI-0029-0001..0002`)
- **Тип / Профиль / Риск:** `feature` (`specify`) · `full` · `high`
- **Входы и ссылки:** [[03-Архитектура-и-контракты/Спецификация-архитектурных-флоу-flow-json]], [flowjson.md](<../../../flowjson.md>), `PROB-03`, `PROB-15`, `PROB-18`, `R11`
- **Область работ (`scope.in`):**
  1. Выделить пакет валидации/рендера флоу без дальнейшего раздувания `task_ops.py` и `doc_ops.py`; удалить мёртвую `doc/architecture/schemas/bodies/flow.json` и ввести `doc/architecture/schemas/arch-flow.schema.json`.
  2. Реализовать комбинаторный валидатор таблиц решений DMN (`hit_policy: "UNIQUE"` — `0 gaps / 0 overlaps`, а также каскад `"COLLECT" → "UNIQUE"`) и генератор `<slug>.md` + `doc/architecture/flows.index.json` с проверкой воспроизводимости в `arch gate`.
- **Критерии приёмки (`AC`):**
  - `AC-1`: пропуск комбинации факторов или пересечение двух правил в `UNIQUE`-таблице ловится `arch docs flow validate` с точным указанием отсутствующего вектора входов.

### TASK-F2-02 — Механика дельт `stageN/flow-delta.json` и миграция ключевых реальных флоу `sf` (`UI-0029-0003..0004`)
- **Тип / Профиль / Риск:** `feature` (`change`) · `standard` · `high`
- **Входы и ссылки:** [[03-Архитектура-и-контракты/Спецификация-архитектурных-флоу-flow-json]], `PROB-03`, `R11`
- **Область работ (`scope.in`):**
  1. Реализовать `arch docs flow delta validate / apply` (`ADDED / MODIFIED / REMOVED` правил и переходов по паттерну OpenSpec) и мост `flow correlate` к символам готового графа кода (`codebase-memory-mcp` / `codegraph`) — **строго на реальном коде без игрушечного репо**.
  2. Перевести реальные системные флоу (`FLOW-create-task`, `FLOW-execute-task`, `FLOW-document-session`, `FLOW-task-record`, `FLOW-tracker-inbox`) в `*.flow.json`.
- **Критерии приёмки (`AC`):**
  - `AC-1`: все 5 системных `*.flow.json` проходят `flow validate`, привязаны к реальным Python-символам и тестам `doc/tests/` и автоматически рендерят `.md` и `flows.index.json`.

### TASK-F2-03 — Внедрение `Validity L1` (`task snapshot / audit / impact`) и ревизия `45` задач `intake`
- **Тип / Профиль / Риск:** `feature` (`change`) · `standard` · `high`
- **Входы и ссылки:** [[03-Архитектура-и-контракты/Двухтрековая-архитектура-sf-v3-и-граница-ядра]], [taskcontrol.md](<../../../taskcontrol.md>), `PROB-09`, `R11`
- **Область работ (`scope.in`):**
  1. Реализовать команды `arch task snapshot`, `arch task audit` и `arch task impact` со строгим разделением статусов `current | stale | conflicted | superseded | unknown` (где `unknown ≠ current`) и кэшем блокировок `task_leases` в `.sf/intent.sqlite`.
  2. Прогнать `arch task audit` по всем `45` открытым карточкам `intake` и разрешить коллизии (`UI-0030` vs `UI-0029`, `UI-0031` vs `UI-0028`).
- **Критерии приёмки (`AC`):**
  - `AC-1`: пересечение по `scope.out` или изменение входного `DOC-ID / FLOW-ID` автоматически помечает зависимые открытые задачи как `conflicted` / `stale` и блокирует старт реализации до пересмотра.

### TASK-F2-04 — Стандартизация пофункционального протокола `Independent Verifier` (по Winninger)
- **Тип / Профиль / Риск:** `feature` (`change`) · `standard` · `medium`
- **Входы и ссылки:** [[02-Исследования-и-инструменты/Эмпирические-законы-контекста-и-слабых-моделей]], [[03-Архитектура-и-контракты/Конвейер-верификации-оракулы-и-песочница]], `PROB-30`, `R12`
- **Область работ (`scope.in`):**
  1. Добавить JSON-отчёт `stageN/verifier-report.json` (по одной записи на каждую изменённую функцию диффа с ответами на 4 вопроса Winninger и сверкой `model_verifier != model_implementer`) и проверять его наличие в `acceptance.py` для `risk ≥ medium`.
- **Критерии приёмки (`AC`):**
  - `AC-1`: совпадение идентификатора модели `verifier` с моделью `implementer` или неразобранный `finding` уровня `high/critical` блокирует `task close`.

### TASK-F2-05 — Детерминированная сверка `arch analyze` (биекция `AC ↔ CASE ↔ flow rule ↔ diff`)
- **Тип / Профиль / Риск:** `feature` (`change`) · `standard` · `medium`
- **Входы и ссылки:** [[03-Архитектура-и-контракты/Конвейер-верификации-оракулы-и-песочница]], `PROB-02`, `PROB-03`, `R12`
- **Область работ (`scope.in`):**
  1. Реализовать команду `arch analyze <task_key>` (без вызова LLM), проверяющую, что каждый `AC-N` и каждая затронутая строка таблицы решений `flow-delta.json` имеют зелёный `CASE-N` в `verification.json`, а все затронутые файлы входят в `allowed_edit_spans`.
- **Критерии приёмки (`AC`):**
  - `AC-1`: любой осиротевший `AC` без теста или правка файла вне `allowed_edit_spans` возвращают структурированный отчёт расхождений с кодом `!= 0`.

## Связи

- [[Главная]] · [[03-Архитектура-и-контракты/Спецификация-архитектурных-флоу-flow-json]] · [[03-Архитектура-и-контракты/Конвейер-верификации-оракулы-и-песочница]] · [[04-Реестр-проблем-и-требований/Мастер-реестр-проблем-PROB-01-PROB-38]] · [[05-Этапы-внедрения/F1-Контекст-оракулы-и-первый-продуктовый-срез]] · [[05-Этапы-внедрения/F3-Песочница-волны-роутинг-и-Cold-Resume]]
