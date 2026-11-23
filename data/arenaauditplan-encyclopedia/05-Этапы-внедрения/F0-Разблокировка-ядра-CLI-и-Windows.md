---
id: "AAP-STAGE-F0"
title: "Этап F0 (1 неделя): Разблокировка ядра arch CLI, нативный Windows, схемы и гигиена корпуса"
description: "Пошаговый план этапа F0 (Трек Б) с карточками задач TASK-F0-01..07: подключение task_record.py, замена fcntl, блокер approvals, схема verification.json, починка body_validation.py и чистка 15 доков."
status: "canonical"
track: "track-b-core"
stage: "F0"
paths: ["doc/tools/arch/schema.py", "doc/tools/arch/fs_atomic.py", "doc/tools/arch/body_validation.py", "doc/architecture/schemas/", "doc/config/paths.yaml", "doc/tests/run.sh"]
tags: [этап-f0, план-внедрения, arch-cli, windows, task-record, body-validation, approvals, verification-json]
aliases: ["F0 Разблокировка ядра CLI и Windows", "Этап F0"]
---

# Этап `F0` (`1 неделя`): Разблокировка ядра `arch` CLI, нативный Windows, схемы и гигиена корпуса

> [!abstract] Паспорт этапа `F0`
> - **Трек:** `track-b-core` (точечные исправления ядра `doc/tools/arch/` и схем `doc/architecture/schemas/`).
> - **Закрываемые проблемы:** `PROB-08, PROB-15, PROB-19, PROB-20, PROB-21, PROB-22, PROB-23, PROB-25, PROB-34, PROB-35, PROB-36, PROB-37, PROB-38` (см. [[04-Реестр-проблем-и-требований/Мастер-реестр-проблем-PROB-01-PROB-38]]).
> - **Реализуемые требования:** `R1, R2, R3, R4, R5` + решения `OQ-01..03, OQ-06` (см. [[04-Реестр-проблем-и-требований/Рекомендации-R1-R23-и-открытые-вопросы-владельцу]]).
> - **Зависимости:** независим от `F00` (может идти параллельно с `F00`); является базой для `F1–F4`.

---

## Задачи этапа (готовые шаблоны для `arch task new`)

### TASK-F0-01 — Автоподключение `task_record.py` в `schema.py` и пакетная миграция `77` задач
- **Тип / Профиль / Риск:** `bugfix` (`change`) · `standard` · `high`
- **Входы и ссылки:** [[01-Аудит-текущей-системы/Рентген-репозитория-и-ядра-CLI]], `PROB-20` (`D-01`), `R1`
- **Область работ (`scope.in`):**
  1. Подключить вызов `build_state`, `append_event` и расчёт `intent_digest` из `doc/tools/arch/task_record.py` прямо в `task new / init` (`schema.py`) и перевести версию создаваемых карточек с `draft-0.2` на `1.0`.
  2. Выполнить пакетную миграцию всех существующих карточек `doc/tasks/` с проверкой детерминизма `arch task replay`.
  3. Заблокировать в `validation.py` изменение полей `intent` без явной команды `task revise` с записью события.
- **Критерии приёмки (`AC`):**
  - `AC-1`: `100%` карточек в `doc/tasks/` имеют непустой `intent_digest`, валидный `state.json` и `events.jsonl`; ручная правка `goal` в `task.json` без `revise` роняет `arch validate` с кодом `!= 0`.

### TASK-F0-02 — Кроссплатформенный файловый лок в `fs_atomic.py` и замена `run.sh` на `python -m arch gate`
- **Тип / Профиль / Риск:** `bugfix` (`change`) · `standard` · `high`
- **Входы и ссылки:** [[01-Аудит-текущей-системы/Рентген-репозитория-и-ядра-CLI]], `PROB-08`, `PROB-22` (`D-03`), `R2`, `R5`
- **Область работ (`scope.in`):**
  1. Заменить POSIX-only `import fcntl` и `os.O_DIRECTORY` в `doc/tools/arch/fs_atomic.py:38–48` на кроссплатформенную обёртку (`msvcrt.locking` / атомарный lockfile на `nt`, `fcntl.flock` на `posix`).
  2. Реализовать команду `python -m arch gate` на чистом Python (`shutil / tempfile / zipfile / filecmp` вместо `bash / tar / mktemp / cmp`), **обязательно включив в неё `arch scan`** (чтобы сиротские папки вроде `UI-0032-0005` никогда не проходили гейт), и оставить `doc/tests/run.sh` тонким делегатом.
- **Критерии приёмки (`AC`):**
  - `AC-1`: все write-команды `arch` (`task new`, `decompose`, `close`) и `python -m arch gate` проходят с `exit 0` как на Linux, так и в нативном Windows PowerShell без WSL.

### TASK-F0-03 — Машинный блокер `approvals` владельца и запрет `owner == "unset"` при закрытии
- **Тип / Профиль / Риск:** `bugfix` (`change`) · `quick` · `medium`
- **Входы и ссылки:** [[01-Аудит-текущей-системы/Рентген-репозитория-и-ядра-CLI]], `PROB-21` (`D-02`), `R3`, `OQ-06`
- **Область работ (`scope.in`):**
  1. В `task_ops.py` и `acceptance.py` запретить перевод задачи в `status: "completed"`, если `owner == "unset"` или массив `approvals` пуст (для `risk ≥ medium` либо по политике типа задачи).
  2. По решению `OQ-06` оформить явный пакет ретроспективного подтверждения или версионную границу для исторических `23` закрытых задач.
- **Критерии приёмки (`AC`):**
  - `AC-1`: вызов `arch task close` на задаче с `approvals: []` завершается отказом `APPROVAL_REQUIRED` (`CliEnvelope`, `exit 1`) без модификации файлов на диске.

### TASK-F0-04 — Строгая JSON Schema `verification.json` (`v1.0`) и запрет прозаического `result`
- **Тип / Профиль / Риск:** `feature` (`change`) · `standard` · `high`
- **Входы и ссылки:** [[03-Архитектура-и-контракты/Конвейер-верификации-оракулы-и-песочница]], `PROB-23` (`D-04`), `R4`
- **Область работ (`scope.in`):**
  1. Ввести схему `verification.schema.json` (`v1.0`): обязательные `schema_version`, `checked_revision` (40-символьный Git SHA), `checks[]` с `result ∈ {"pass", "fail", "not_run"}` и `snapshot_sha256`.
  2. Заблокировать `task close`, если хотя бы один обязательный `check` имеет `result != "pass"` (включая `"not_run"`!).
- **Критерии приёмки (`AC`):**
  - `AC-1`: запись свободной прозы или `null` в `result`, а также пустой `checked_revision` отвергаются валидатором и `task close`.

### TASK-F0-05 — Починка тройного бага `body_validation.py` и синхронизация `document.schema.json` с `ARCH-contract` §6.2
- **Тип / Профиль / Риск:** `bugfix` (`change`) · `standard` · `high`
- **Входы и ссылки:** [[01-Аудит-текущей-системы/Аудит-архитектурной-документации-и-схем]], `PROB-34`, `PROB-35`, `PROB-37`, `R5`, `OQ-02`
- **Область работ (`scope.in`):**
  1. Исправить `validate_document_body()` в `doc/tools/arch/body_validation.py` (чтение из `schema["properties"]`, нормализация префикса `## `, очистка fenced code blocks и суффиксов `{#anchor}`) и добавить негативные unit-тесты на каждый тип документа.
  2. Устранить все 6 расхождений `document.schema.json` с `ARCH-contract` §6.2 (`additionalProperties: false`, объектный/нормализованный `source_refs`, единый паттерн `id`, `enum` типов, `allOf` для `decision_status`/`superseded_by`, поля `implemented/aliases/owner`).
  3. Внести `stage{stage}/architecture-delta/` и правило для `doc/architecture/README.md` в `doc/config/paths.yaml`.
- **Критерии приёмки (`AC`):**
  - `AC-1`: намеренная порча обязательного заголовка `## ` или опечатка в ключе YAML frontmatter гарантированно роняют `arch validate` (подтверждено unit-тестами).
  - `AC-2`: создание файла в `doc/tasks/<key>/stage1/architecture-delta/` проходит `arch docs paths --check` с `exit 0`.

### TASK-F0-06 — Приведение в порядок `15` нарушающих документов `doc/architecture/`, дубля манифеста и `SPEC-cli-implementation`
- **Тип / Профиль / Риск:** `refactor` (`specify`) · `standard` · `medium`
- **Входы и ссылки:** [[01-Аудит-текущей-системы/Аудит-архитектурной-документации-и-схем]], `PROB-15`, `PROB-34`, `PROB-36`, `PROB-38`, `R5`, `OQ-01`, `OQ-02`
- **Область работ (`scope.in`):**
  1. Выровнять все `15` документов из таблицы `PROB-34` (переклассифицировать `FLOW-cli-task-lifecycle`, `FLOW-cli-subtask-lifecycle`, `FLOW-kilo-session-audit`, `REG-cli-*` в их истинные типы; выровнять заголовки `ENT-*`, `DOM-task-lifecycle`, `VIEW-security`; перевести англ. шаблоны `ARCH-contract` §5.5 на русский).
  2. Устранить дублирование двух манифестов (`23 041 Б` дельты) и `33` непроверяемых `[[wikilink]]` в `system/manifest.md` по решению `OQ-01`, оставив ровно один документ `type: system`.
  3. Актуализировать `SPEC-cli-implementation` (описать 8 новых модулей CLI, убрать петлю в `related`, разбить секции `>32 КБ` против `SECTION-TOO-LARGE`, проставить честный `implemented: true` реально работающим спекам CLI).
- **Критерии приёмки (`AC`):**
  - `AC-1`: `arch validate` (с починенным `body_validation.py`), `arch docs check-links` и чтение всех секций `arch docs read` по `45` документам проходят с `0` ошибок и `0` `SECTION-TOO-LARGE`.

### TASK-F0-07 — Санитарная зачистка репозитория (`UI-0032-0005`, 8 локальных путей, `seesionaudit.md`, `data/README.md`)
- **Тип / Профиль / Риск:** `chore` (`change`) · `quick` · `low`
- **Входы и ссылки:** [[01-Аудит-текущей-системы/Аудит-архитектурной-документации-и-схем]], `PROB-08`, `PROB-19`, `PROB-25`, `PROB-38`, `R5`, `OQ-03`
- **Область работ (`scope.in`):**
  1. Оформить или перенести сиротскую папку `doc/tasks/UI-0032-0005/`, убрать 8 локальных путей рабочей станции из 5 файлов `doc/architecture/`, переименовать `seesionaudit.md` → `sessionaudit.md`, починить ссылку `data/simple/` в `data/README.md`, убрать корневой дубль обзорной статьи и урегулировать `37` ссылок `../../../` в `UI-0001..0007` (`OQ-03`).
- **Критерии приёмки (`AC`):**
  - `AC-1`: `python -m arch gate` (включая `scan`) завершается с `exit 0`, а поиск локальных абсолютных путей по `doc/` возвращает `0` вхождений.

## Связи

- [[Главная]] · [[01-Аудит-текущей-системы/Рентген-репозитория-и-ядра-CLI]] · [[01-Аудит-текущей-системы/Аудит-архитектурной-документации-и-схем]] · [[04-Реестр-проблем-и-требований/Мастер-реестр-проблем-PROB-01-PROB-38]] · [[05-Этапы-внедрения/F00-Среда-и-субагенты-без-правки-CLI]] · [[05-Этапы-внедрения/F1-Контекст-оракулы-и-первый-продуктовый-срез]]
