---
id: "AAP-AUDIT-CORE"
title: "Рентген репозитория sf v0.2.0 и ядра arch CLI на снимке f8cb406"
description: "Загружайте, когда нужны точные замеренные цифры по дереву репозитория sf (640 файлов, 77 задач), сильные стороны ядра arch CLI, 8 форензик-улик, аудит 10 принципов Манифеста и команды воспроизводимости замеров."
status: "canonical"
track: "both"
stage: "F0"
paths: ["doc/tools/arch/", "doc/tasks/", "doc/config/", "doc/skills/", "doc/tests/run.sh", "seesionaudit.md"]
tags: [аудит, форензика, arch-cli, task-json, windows, fcntl, метрики]
aliases: ["Рентген репозитория и ядра CLI", "Форензика репо sf"]
---

# Рентген репозитория `sf v0.2.0` и ядра `arch` CLI на снимке `f8cb406`

> [!abstract] Кратко
> На ревизии `f8cb406` (`arch 0.2.0`) репозиторий насчитывает **`640` файлов (`4 343 152` байт / `4.14 MiB`, `68 081` строка)**, `17` коммитов, `1` ветку `master` и `0` тегов. У `sf` уже создано уникальное по инженерной строгости governance-ядро (JSON/YAML-канон, атомарная запись с журналом, идемпотентный inbox трекера, строгий `CliEnvelope`), но проект застрял в **самореференции (`77` задач о самой фабрике при `0` продуктовых задач)**, собственное event-ядро (`task_record.py`) **не подключено к созданию задач (`0/77` `state.json`/`events.jsonl`/`intent_digest`)**, **`23/29` закрытых задач не имеют `approvals`**, а POSIX-вызовы `fcntl` и `bash/tar` блокируют запись и гейт на **нативном Windows владельца**.

## 1. Количественный срез всех подсистем репозитория (`f8cb406`)

*(Эвристика расчёта токенов для русскоязычных артефактов ≈ `bytes / 2.6` ±30%, для кода/ASCII ≈ `bytes / 3.8` либо `tiktoken o200k_base`).*

| Подсистема | Фактический объём и состав (`f8cb406`) | Реальный статус реализации |
|---|---|---|
| **Корневые проектные документы (`10` файлов, `404.5 КБ`, `2 979` строк)** | [nextplan.md](<../../../nextplan.md>) (`126.5 КБ`, ~49k tok), [Манифест](<../../../Манифест агентной software factory.md>) (`113.9 КБ`, ~44k tok), [seesionaudit.md](<../../../seesionaudit.md>) (`41.5 КБ`, опечатка в имени файла!), [taskcontrol.md](<../../../taskcontrol.md>) (`39.3 КБ`), [worktree.md](<../../../worktree.md>) (`34.4 КБ`), [README.md](<../../../README.md>) (`20 КБ`, ~8k tok), [AGENTS.md](<../../../AGENTS.md>) (`2.3 КБ`) | 4 монолита >100 КБ (включая `ARCH-contract`); критичные механизмы (`task control`, `git/worktree CLI`, `model routing`) остаются проектными черновиками |
| **Движок CLI (`doc/tools/`, `37` файлов, `491.5 КБ`, `12 154` строки)** | `32` модуля `arch/*.py` (**`11 486–11 494` строк Python**, ~`45` команд в `allowed_commands`: [task_ops.py](<../../../doc/tools/arch/task_ops.py>) — 1820 строк, [doc_ops.py](<../../../doc/tools/arch/doc_ops.py>) — 1322, [session_audit.py](<../../../doc/tools/arch/session_audit.py>) — 1222, [validation.py](<../../../doc/tools/arch/validation.py>) — 909) | В [fs_atomic.py](<../../../doc/tools/arch/fs_atomic.py>) (`L38–48`) ленивый `import fcntl` + `os.O_DIRECTORY` роняет **все write-команды на нативном Windows** (при этом read-only команды работают!); event-ядро [task_record.py](<../../../doc/tools/arch/task_record.py>) не подключено в [schema.py](<../../../doc/tools/arch/schema.py>) (`0/77` карточек!) |
| **Хранилище знаний (`doc/architecture/`, `67` файлов, `706.1 КБ`, `8 118` строк)** | `45` документов в `index.json` (**`12 implemented: true / 33 implemented: false` — 73% не реализовано!**), `155` `related`-ссылок (`0` битых), [architecture-contract.md](<../../../doc/architecture/system/architecture-contract.md>) `135.9 КБ` (~52k tok) | Честная маркировка `implemented`, но `body_validation.py` — полный no-op (`15/45` документов нарушают body-схемы, см. [[01-Аудит-текущей-системы/Аудит-архитектурной-документации-и-схем]]), `8` хардкодов локальных путей и дубль манифеста |
| **Конфигурация (`doc/config/`, `105` файлов, `117.9 КБ`, `3 496` строк)** | [paths.yaml](<../../../doc/config/paths.yaml>) + [plan-defaults.yaml](<../../../doc/config/task-conf/plan-defaults.yaml>) (константы тиров продублированы в `acceptance.py`) + `102` файла `task-conf/` по `13` типам задач | Избыточная дробность (`13` типов × flows × prompts) при `0` продуктовых задач |
| **Каталог скиллов (`doc/skills/`, `15` файлов, `127.2 КБ`, `1 020` строк)** | **4 действующих скилла + 5 черновых**: [go-to-task/SKILL.md](<../../../doc/skills/go-to-task/SKILL.md>) (`20.6 КБ`), [create-task/SKILL.md](<../../../doc/skills/create-task/SKILL.md>) (`15.1 КБ`), [arch-cli/SKILL.md](<../../../doc/skills/arch-cli/SKILL.md>) (`14.5 КБ`), `architecture-docs` (`11.6 КБ`), `plan-task` (`11.3 КБ`) | Суммарный **входной пакет одной задачи ≈ `65 КБ` (`~25 000` токенов)** *до чтения единой строки кода продукта*! |
| **Корпус задач (`doc/tasks/`, `240` файлов, `1.15 МБ`, `19 598` строк)** | **`33` родителя + `44` подзадачи = `77` карточек `task.json`** (`45 intake` — 58%, `29 completed`, `2 ready`, `1 planning`; медиана `4 826 Б`, макс `UI-0032` — `28 797 Б` / ~11k tok) + сиротская папка `UI-0032-0005` без `task.json`; `75` `plan.md` (маркер тира лишь в `19/75`); `75` `verification.json` | **`77/77` на `draft-0.2`**, **`76/77` с `owner/priority = unset`**, **`23/29` закрыты с пустым `approvals: []`**, **`0/77` со `state.json`/`events.jsonl`/`intent_digest`**, `CASE` лишь в `10/77`, `snapshot_files` и непустой `checked_revision` — в `23/75` |
| **Тесты и локальный gate (`doc/tests/`, `8` файлов, `196.1 КБ`, `3 729` строк)** | [run.sh](<../../../doc/tests/run.sh>) (`--brief / --gate / --index-only / --in-copy / --only`) | Завязан на `bash/tar/mktemp/cmp` — **падает на нативном Windows владельца** без WSL |
| **База исследований (`data/`, `157` файлов, `1.13 МБ`, `16 927` строк)** | `5` тематических энциклопедий с MOC-навигацией и протоколом эпистемического статуса | [data/README.md](<../../../data/README.md>) (`ROOT-moc`) ссылается на несуществующий `data/simple/` (дрейф MOC) |

---

## 2. Девять фундаментальных сильных сторон («ров проекта», сохраняемый на 100%)

1. **Единый типизированный вход `task.json` и готовый модуль неизменяемого замысла ([task_record.py](<../../../doc/tools/arch/task_record.py>)):** функции `intent_digest`, `build_state`, `append_event`, `replay` и `migrate` уже написаны и оттестированы — требуется лишь подключить их в `schema.py` (`PROB-20`).
2. **Честная маркировка зрелости (`implemented: true/false` в `index.json`) и детерминизм пересборки (`PYTHONHASHSEED=0` и `12345`, `0/155` битых `related`).**
3. **Строгий белый список файловой структуры в [paths.yaml](<../../../doc/config/paths.yaml>) (`only_declared_paths: true`, `garbage_detector: true`)** и декларативные политики `close_policy / subtask_policy`.
4. **Криптографическая свежесть доказательств (`snapshot_files` SHA-256 + `checked_revision` в [acceptance.py](<../../../doc/tools/arch/acceptance.py>) и [evidence.py](<../../../doc/tools/arch/evidence.py>))** — уникальна среди SDD-аналогов.
5. **Атомарная запись с журналированием композитных операций ([fs_atomic.py](<../../../doc/tools/arch/fs_atomic.py>) + `.arch-write-journal.json`)** при декомпозиции подзадач `task decompose` *(после замены `fcntl` на кроссплатформенный лок заработает и на Windows)*.
6. **Разведение осей `phase` (этап процесса) и `status` + уровневая политика планов (`micro / standard / full` в `plan_policy.py`).**
7. **Модель устаревания как отношения входов (`suspect links` по типу DOORS/Jama и Bazel affected-targets в [taskcontrol.md](<../../../taskcontrol.md>)), а не календарного возраста.**
8. **Идемпотентный журнал событий с защитой от дублей и учёт источников трекера ([task_record.py](<../../../doc/tools/arch/task_record.py>) + [task_registry.py](<../../../doc/tools/arch/task_registry.py>)): ключ идемпотентности `event_id`, хеш-цепочка `prev_digest` и `replay_state`.**
9. **Единый машинный JSON-протокол `CliEnvelope` со стабильными кодами выхода (`0, 1, 2, 5, 10, 20`) и наличие встроенного форензик-аудитора сессий ([session_audit.py](<../../../doc/tools/arch/session_audit.py>)).**

---

## 3. Восемь жёстких форензик-улик реального поведения системы

1. **Улика №1 — Разрыв между написанным event-ядром и реальным корпусом (`PROB-20` / `D-01`):** `task_record.py` не вызывается в `schema.py` (`task new/init`) → во всём дереве `doc/tasks/` **`0` файлов `state.json`, `0` файлов `events.jsonl` и `0/77` карточек с `intent_digest`** (в 0-diff режиме лечится немедленным вызовом `arch task migrate <key>` после `task new`, в ядре — фиксом `schema.py`).
2. **Улика №2 — Реальная цена одного небольшого багфикса `UI-0011` ([seesionaudit.md](<../../../seesionaudit.md>), `PROB-01`):** дифф в 2 файлах потребовал **`97` сообщений, `95` вызовов инструментов (`75 bash`), `12 мин 07 с`, `253 845` новых входных токенов и `7 326 976` кумулятивных токенов кэша** (`$6.71` даже на модели со сверхдешёвым кэшем), причём `68%` ушло на кустарное воспроизведение в `/tmp/`, а на финише агент сломал `task.json` значением `phase: "verifying"`, не положил постоянный тест в `doc/tests/`, пропустил баг plain-text отказа при `--json` и отрапортовал *«Задача полностью выполнена!»*.
3. **Улика №3 — Бумажный гейт одобрения владельца и полу-прозаический `verification.json` (`PROB-21/23` / `D-02/D-04`):** **`23 из 29`** задач со `status: "completed"` имеют пустой массив `approvals: []` (включая `UI-0011`, чья `stage_history` явно ждёт апрува владельца!). Из `75` файлов `verification.json` ключ `checked_revision` есть в `66/75`, но **непустое значение записано ровно в `23/75`**, `snapshot_files` — в `23/75`, `schema_version` — в `41/75`, а поле `result` смешивает свободную прозу, `"passed"`, `"pass"` и `None`.
4. **Улика №4 — Синдром «перегруженной слабой модели» (`PROB-05/24` / `D-05/D-06`):** до чтения первой строчки кода продукта агент обязан проглотить `~65 КБ` (`~25 000` ток.) скиллов и контрактов, а монолиты `ARCH-contract` (`136 КБ` / ~52k tok), `MAN-software-factory` (`137 КБ`), `nextplan.md` (`126 КБ` / ~49k tok) и карточки вроде `UI-0032` (`28.8 КБ` / ~11k tok) вызывают *Context Rot*.
5. **Улика №5 — `evidence.py` фиксирует факт запуска команды, но слеп к качеству оракула (`PROB-02`):** пустой `assert True` или удалённый `assert` даёт `exit_code == 0` и проходит как валидное доказательство.
6. **Улика №6 — Поломка на Windows-машине владельца (`PROB-22` / `D-03`):** в `fs_atomic.py:38–48` `lock_directory()` вызывает POSIX-only `fcntl.flock` и `os.O_DIRECTORY` (блокируя все write-команды `arch` на нативном Windows без WSL), а `doc/tests/run.sh` требует `bash`, `tar`, `mktemp`, `cmp`.
7. **Улика №7 — Слепота к большим кодовым базам (`PROB-04/07`):** `doc/architecture/index.json` индексирует только `45` Markdown-документов (`12` реализованных и `33` нереализованных), не имея моста к AST/LSP/роутам реального кода.
8. **Улика №8 — Коллизии бэклога и сиротские артефакты (`PROB-08/09` / `D-08`):** `45/77` карточек лежат в `intake` без `Validity`-контроля (`UI-0030` нарушает `scope.out` `UI-0029`, `UI-0031` пересекается с `UI-0028`), а в корне задач лежит сиротская папка `doc/tasks/UI-0032-0005/research/taxonomy-decision.md` без `task.json`, которую пропускает `run.sh --gate` (ловится только ручным `arch scan`).

---

## 4. Аудит 10 декларированных принципов Манифеста и 7 «священных коров»

| № | Принцип Манифеста `sf` | Фактическое состояние в `f8cb406` | Вердикт |
|---:|---|---|---|
| **1** | Истина — в артефактах репо, не в памяти чата | Реестры и карточки в Git, но `state.json`/`events.jsonl = 0`, в `UI-0032` следы чата раздули карточку до `28.8 КБ` | **Частично** |
| **2** | Каждый тип истины живёт в своём месте (SSOT) | Чёткое деление папок, но два расходящихся манифеста (`23 КБ` разницы), дубль `plan-tier` в Python и YAML | **Сильная база с нарушениями** |
| **3** | Краткий вход + глубокое чтение по требованию | `AGENTS.md` краток (`18` и `61` строка), но обязательные скиллы и монолиты съедают `~25k` ток. на старте | **Не выдержано в скиллах** |
| **4** | Детерминизм и скрипты вместо LLM там, где нет суждения | `11.5k` LOC в `arch`, но `body_validation.py` — no-op, а проверка `AC` держится на отчёте самой модели | **Хорошо в CLI, слабо в приёмке** |
| **5** | Дешёвые модели на рельсах, сильные — на развилках | `CAP-role-model-routing` имеет `implemented: false`; стартовый налог `25k` ток. топит малые модели | **Только проект** |
| **6** | Доказательство вместо заявления о готовности | Есть SHA-256 и журнал записи, но `verification.json` полу-прозаичен, оракулов/мутаций нет, `23/29` без `approvals` | **Половина пути** |
| **7** | Строгие границы доступа и доверия | Описана защита от prompt-injection, но нет контейнерного sandbox, RO-защиты тестов и `egress allowlist` | **Декларация без техконтроля** |
| **8** | Вертикальные срезы без заморозки разработки | `77` задач подряд строят документацию фабрики при `0` продуктовых срезов | **Нарушен на практике** |
| **9** | Явная политика локальных гейтов и независимости от CI | `run.sh` не работает на нативном Windows; конфликт запрета Git-hosted правил в `README` с `worktree.md` §4.6 (`CONF-08`) | **Сломан на целевой ОС** |
| **10** | Владелец утверждает смысл, контракты и спорные границы | Поле `approvals` есть в схеме, но `23/29` закрыты с `approvals: []`, `76/77` имеют `owner: "unset"` | **Обходится без блокировки** |

**Семь архитектурных противоречий («священных коров»), устраняемых в `sf v3.0`:**
1. *Pull-by-LLM моночат* → заменяется на `Envelope-Driven Subagents` в среде (Трек А) и `Push-by-Harness` микро-вызовы (Трек Б).
2. *Python-only без внешних графов кода* → заменяется на готовые MIT-графы `colbymchenry/codegraph`, `codebase-memory-mcp`, `Graphify`, `Serena` (`0` самописных MCP).
3. *Один агент пишет и код, и тесты, и ревьюит себя* → заменяется на `Oracle-First` + `RO Trust Zone` + `Independent Verifier` на другой модели.
4. *Вера в `exit_code == 0` и прозу в `verification.json`* → заменяется на строгую JSON Schema (`pass|fail|not_run`) + `Red-before-Green` + `Diff-Mutation Gate`.
5. *Смешение POSIX-движка и документации целевого продукта* → заменяется на кроссплатформенный лок и подключаемый слой среды/манифеста `.sf/`.
6. *Гипертрофия `13` типов задач и `102` файлов промптов* → сжимается в `Ceremony Scaling` (`quick / standard / full`) и `4–5` базовых конвейеров.
7. *Регулярки по текстовому `plan.md` и закрытие без `approvals`* → заменяются на `workpack.json`, детерминированные `analyze/converge` и машинный блокер `approvals`.

---

## 5. Однострочные команды 100%-й воспроизводимости всех замеров на клоне `sf`

```bash
# 1. Подсчёт файлов, байтов и строк рабочего дерева (без .git)
python3 -c "import pathlib; r=pathlib.Path('.'); fs=[p for p in r.rglob('*') if p.is_file() and '.git' not in p.parts]; print('files:',len(fs),'bytes:',sum(p.stat().st_size for p in fs),'lines:',sum(p.read_bytes().count(b'\n') for p in fs))"

# 2. Проверка task.json, event-ядра, пустых approvals и ревизий verification.json
python3 -c "import json,pathlib,statistics; ts=sorted(pathlib.Path('doc/tasks').rglob('task.json')); sz=[p.stat().st_size for p in ts]; d=[json.loads(p.read_text()) for p in ts]; done=[x for x in d if x.get('status')=='completed']; vs=[json.loads(p.read_text()) for p in pathlib.Path('doc/tasks').rglob('verification.json')]; print('tasks:',len(ts),'median_B:',int(statistics.median(sz)),'max_B:',max(sz),'state:',len(list(pathlib.Path('doc/tasks').rglob('state.json'))),'events:',len(list(pathlib.Path('doc/tasks').rglob('events.jsonl'))),'digest:',sum(1 for x in d if x.get('intent_digest')),'done:',len(done),'no_approvals:',sum(1 for x in done if not x.get('approvals')),'verif:',len(vs),'rev_nonempty:',sum(1 for v in vs if v.get('checked_revision')),'snap:',sum(1 for v in vs if v.get('snapshot_files')))"
```

## Связи

- [[Главная]] · [[01-Аудит-текущей-системы/Аудит-архитектурной-документации-и-схем]] · [[01-Аудит-текущей-системы/Моделирование-сценариев-и-режимы-отказа-F1-F14]] · [[04-Реестр-проблем-и-требований/Мастер-реестр-проблем-PROB-01-PROB-38]] · [[05-Этапы-внедрения/F0-Разблокировка-ядра-CLI-и-Windows]] · [[06-Консилиум-и-конфликты/Обзор-Эксперта-01-Полный-аудит-и-SF2]]
