---
id: "AAP-ARCH-FLOWJSON"
title: "Спецификация формальных архитектурных флоу *.flow.json (v2.0), ревизия 8 FLOW-* и 6 правил нарезки"
description: "Загружайте для понимания концепции Spec-Anchored архитектурных флоу, аудита UI-0029 по 12 критериям, миграции 8 текущих FLOW-*, стандартов DMN/XState/Arazzo и правил декомпозиции флоу."
status: "canonical"
track: "track-b-core"
stage: "F2"
paths: ["flowjson.md", "doc/tasks/UI-0029/", "doc/architecture/schemas/bodies/flow.json", "doc/tools/arch/flows.py", "doc/tools/arch/task_ops.py"]
tags: [flow-json, dmn, statecharts, arazzo, ui-0029, flow-split, anti-drift, спека]
aliases: ["Спецификация архитектурных флоу flow-json", "Спецификация *.flow.json"]
---

# Спецификация формальных архитектурных флоу `*.flow.json` (`v2.0`), ревизия 8 `FLOW-*` и 6 правил нарезки

> [!abstract] Кратко
> Архитектурные флоу `*.flow.json` выступают нормативным «позвоночником» `Spec-Anchored` документации `sf v3.0`: они объединяют каркас **АШОСС** (*Акторы, Шаги, Ошибки, Состояния, Границы* из [Флоу.md](<../../machinedocs-encyclopedia/Документация/Флоу.md>)), триаду нотаций из [Стандарты описания флоу.md](<../../sdd-encyclopedia/Флоу/Стандарты описания флоу.md>) и формальную проверку полноты таблиц решений **OMG DMN 1.6 (`0 gaps / 0 overlaps`)** в связке с готовыми внешними графами кода (`codebase-memory-mcp` / `colbymchenry/codegraph`). Полная JSON Schema и 20 CLI-команд вынесены в парную заметку [[03-Архитектура-и-контракты/Схемы-индекс-и-скилл-flow-audit]].

## 1. Доменная граница и почему текущий набросок в `UI-0029` покрывает лишь `~35–40%`

- **Жёсткое разграничение:** `Task Flows` (`doc/config/task-conf/`, схема `schemas/flow.schema.json`) описывают *конвейер шагов агента при работе над задачей*, тогда как `Architectural Flows` (`doc/architecture/domains/**/flows/*.flow.json`, схема `schemas/arch-flow.schema.json`) описывают *поведение, ветвления и жизненный цикл самого программного продукта* (`sf` на этапе самоприменения или внешнего продукта вроде `PHP/Laravel CRM`). Валидация на игрушечном репо запрещена (`CONF-07`).
- **Двенадцать дефицитов текущего черновика `UI-0029` (`PROB-03`, `GAP-FLOW-01..05`):**
  1. нет JSON Schema и правил стыковки с `index.json`;
  2. нет типизированных входных факторов (`factors[]` с `allowed_values`) → невозможно проверить пропуски комбинаций;
  3. нет политики срабатывания `hit_policy` (`UNIQUE` для `task init`, `PRIORITY/FIRST` для `select-flow`, каскад `COLLECT → UNIQUE` для `diagnose → close`);
  4. нет каскадных узлов `decisions[]` (плоский список ведёт к комбинаторному взрыву);
  5. не разделена природа решателя `decision_maker` (`deterministic | agent_judgment | human_approval`);
  6. нет автомата состояний `lifecycle` (`ENT-*`, `initial/intermediate/terminal`, `state_unchanged_on_disk`);
  7. нет контракта мутаций и атомарности (`read_only | atomic | compensated`, `rollback`);
  8. нет формальной модели идемпотентности (`event_id`, `expected_revision`);
  9. нет структурированного `retry_policy` (`retry_when`, `max_attempts`, `on_exhausted` из *OpenAPI Arazzo v1.1*);
  10. выпали глобальные `invariants` и обязательный блок границ `not_included`;
  11. в `refs` пропущены `ENT-*`, соседние `FLOW-*`, скиллы и термины глоссария `TERM-*` (`UI-0028`);
  12. нет машинных полей `exit_code / http_status / error_code` и статуса `oracle_status` (`verified | missing_oracle | manual_only`).

---

## 2. Поимённая ревизия всех 8 существующих `FLOW-*` в `doc/architecture/`

| № | ID и текущий путь | Текущее содержимое на `f8cb406` | Целевое действие при миграции в `UI-0029` |
|---:|---|---|---|
| 1 | `FLOW-create-task` (`task-intake/flows/create-task.md`) | Ветвления `P1..P4` (`task new / init`), отказы коллизий и советы по `CASE` | **Перевести в `create-task.flow.json`** (`UNIQUE`, $2\times3\times2=12$ комбинаций покрыты на 100%); советы по написанию `CASE` вынести в скилл |
| 2 | `FLOW-task-lifecycle` (`task-lifecycle/flow.md`) | Смесь пересказа шагов агента `task-conf` и системных `select-flow / diagnose / advance / close` | **Разделить и перевести ядро в `task-lifecycle.flow.json`** с каскадом `diagnose-blockers (COLLECT) → close-gate (UNIQUE)` |
| 3 | `FLOW-execute-task` (`task-lifecycle/flows/execute-task.md`) | Линейный пересказ 6 шагов агента | Пометить `superseded_by: FLOW-task-lifecycle` и выделить реальный движок `flows.py` в `FLOW-task-flow-execution` |
| 4 | `FLOW-cli-task-lifecycle` (`task-lifecycle/cli-task-lifecycle.md`) | Справочник 4 CLI-команд и раскладки папок | Вывести из `type: flow`: ветки влить в `FLOW-create-task`/`FLOW-task-lifecycle`, сигнатуры — в `REG-cli-command-map` / `SPEC-cli-implementation` |
| 5 | `FLOW-cli-subtask-lifecycle` (`task-lifecycle/cli-subtask-lifecycle.md`) | Иерархия `subtasks/<NNNN>/` и правила детей | **Преобразовать в `subtask-lifecycle.flow.json`** (`subtask_policy`, ацикличность `depends_on`, готовность волн) |
| 6 | `FLOW-verify-task` (`execution-verification/flow.md`) | 6 шагов проверки на снимке и пути отказа | **Перевести в `verify-task.flow.json`** (`case-coverage-v1`, `plan-policy`, свежесть SHA-256 `snapshot_files`, `Oracle-First`) |
| 7 | `FLOW-document-session` (`execution-verification/flows/document-session.md`) | Дерево решений из 3 веток (`P1..P3`) | **Прямой перевод в `document-session.flow.json`** с постусловием неизменности `task.json` |
| 8 | `FLOW-kilo-session-audit` (`execution-verification/flows/kilo-session-audit.md`) | Гибрид `22.2 КБ`: процесс + 140 строк SQL/JSON-схемы `kilo.db` | **Разделить:** ветвления (`1 / >1 / 0 кандидатов → exit 20 vs 0`) в `kilo-session-audit.flow.json`, SQL-рецепты и схему — в `SPEC-kilo-session-audit` |

Плюс закрываются **2 слепые зоны домена `project-knowledge`** (где сейчас `0` флоу): создаются `FLOW-docs-validation-and-indexing` и `FLOW-docs-retrieval-and-impact` (см. матрицу всех 32 модулей в [[03-Архитектура-и-контракты/Схемы-индекс-и-скилл-flow-audit]]).

---

## 3. Шесть операциональных правил нарезки флоу и механизм `Flow Split` без поломки ссылок

Как показано на реальном модуле [task_ops.py](<../../../doc/tools/arch/task_ops.py>) (`1 820` строк), наивное правило «1 файл кода = 1 флоу» порождает нечитаемый God-object на 40+ веток. Применение **6 правил нарезки** делит `task_ops.py` на 4 чистых сцепленных флоу (`FLOW-create-task`, `FLOW-subtask-lifecycle`, `FLOW-verify-task`, `FLOW-task-lifecycle`):

1. **Граница ведущей сущности и домена (`Primary Entity`):** смена `ENT-*` или домена → отдельный `*.flow.json`.
2. **Точка покоя на диске (`Quiescent State`):** остановка между внешними вызовами (например, `scaffolded` после `task new`) → граница флоу со сцепкой `next: {"kind": "flow", "target": "FLOW-..."}`.
3. **Ортогональность факторов (`2–4` фактора в узле):** несвязанные оси проверок разводятся в каскадные узлы `decisions[]` или дочерний флоу.
4. **Правило переиспользования (`PROMOTE vs KEEP_LOCAL`):** подпроцесс, вызываемый из `≥2` разных флоу (`FLOW-verify-task`), выделяется в самостоятельный `FLOW-*`.
5. **Нижний порог против «атомарной пыли»:** чистые утилиты без доменных развилок (`tmp+rename`, константы, обёртки) остаются в `steps[]` или `exempt_globs`.
6. **Когнитивные бюджеты размера:** `1–4` узла `decisions[]`, `2–15` веток суммарно, generated `<slug>.md ≤ 150` строк (`<15 КБ`); при превышении `flow validate` выдаёт `flow_split_recommended`.

**Безопасное расщепление (`superseded_branches`) и 4 штатных режима пополнения:**
- При расщеплении разросшегося флоу старые адреса веток записываются в массив `superseded_branches` родителя → все исторические задачи и ADR остаются валидными, а `arch docs read FLOW-old#branch` прозрачно перенаправляет агента на новый `FLOW-sub#branch`.
- В существующих больших базах (`100K–10M LOC`) действует градуированный режим **`Touch-to-Codify` (`--ratchet`)**: покрываются в первую очередь затронутые диффом модули (`measure → warn → enforce`), не замораживая разработку всего legacy-проекта.

## Связи

- [[Главная]] · [[Глоссарий]] · [[01-Аудит-текущей-системы/Аудит-архитектурной-документации-и-схем]] · [[03-Архитектура-и-контракты/Схемы-индекс-и-скилл-flow-audit]] · [[03-Архитектура-и-контракты/Двухтрековая-архитектура-sf-v3-и-граница-ядра]] · [[05-Этапы-внедрения/F2-Флоу-контракты-Validity-L1-и-Verifier]]
