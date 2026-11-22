---
id: FLOW-cli-task-lifecycle
type: flow
title: Жизненный цикл задачи — init, validate, workspace, status
summary: "Документирует, как работают `arch task init/validate/workspace/status`, что они создают и какие инварианты соблюдают."
status: draft
domain: task-lifecycle
related: [DOM-task-lifecycle, ENT-task-input, REG-cli-validation-rules, REG-cli-command-map]
implemented: true
---

# Жизненный цикл задачи

Четыре команды управляют директорией задачи и `task.json` под `doc/tasks/<task_key>/`.

## Структура директории

```
doc/tasks/<task_key>/
├── task.json          (канонический вход задачи; task.md запрещён)
└── stage1/
    ├── plan.md
    └── verification.json
```

## `arch task init <task_key>`

- Разбирает `task_key` через `parse_task_key()` → извлекает `source_type`, `task_number`, `source_prefix`.
- Отклоняет, если `doc/tasks/<task_key>/` уже существует (коллизия).
- Создаёт `<task_key>/` и `<task_key>/stage1/`.
- Записывает скффолд `task.json` через `scaffold_task_json()` (draft-0.2, семантические поля не заполнены).
- Выводит JSON-результат с `ok`, `task_key`, `task_number`, `source_type`, `source_prefix`, путями.
- Код выхода 1 при коллизии или неверном ключе.

## `arch task validate <task_key>`

- Читает `task.json`, разбирает JSON.
- Запускает `validate_task_json(data, task_key)`.
- Отклоняет, если `task.md` существует (манифест требует `task.json` как единственный канонический вход).
- Выводит `task <task_key> is valid` при успехе; списки ошибок `ERROR:` при неудаче.
- Код выхода 1 при любой ошибке валидации или отсутствующем файле.

## `arch task workspace <task_key>`

- Сначала валидирует `task.json` (как в `validate`).
- Выводит детерминированную информацию о рабочей области: `directory`, `task_json`, `target_release`, `branch_hint`.
- `branch_hint` — `futures/<number>` для источников Jira, `bugfix/<key>` для остальных.
- Не выполняет git checkout; фактическая работа с репозиторием требует настроенного репозитория.
- Код выхода 1 при ошибке валидации.

## `arch task status <task_key>`

- Читает `task.json`.
- Перечисляет директории этапов (`stage1`, `stage2`, …) под директорией задачи.
- Перечисляет файлы `verification.json` по этапам.
- Сообщает `has_task_md` (должно быть `false`).
- Выводит JSON с `task_key`, `task_number`, `source_type`, `source_prefix`, этапами, файлами верификации.
- Код выхода 1, если `task.json` отсутствует.

## Инварианты {#invariants}

- `task_key` должен совпадать с именем директории.
- `task_number` должен быть ровно четырьмя десятичными цифрами.
- `task.md` не должен существовать.
- `source.type` должен быть `jira`, `ui` или `other`; ключи Jira — это bare number, ключи UI используют префикс `UI-`, остальные источники требуют явного префикса.
