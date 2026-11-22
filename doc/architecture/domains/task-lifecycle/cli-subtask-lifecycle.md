---
id: FLOW-cli-subtask-lifecycle
type: flow
title: Жизненный цикл субтаски — init, validate, status
summary: "Документирует, как работают `arch task subtask init/validate/status`, контракт директории субтаски и правила рекурсии."
status: draft
domain: task-lifecycle
related: [DOM-task-lifecycle, FLOW-cli-task-lifecycle, REG-cli-validation-rules, REG-cli-command-map]
implemented: true
---

# Жизненный цикл субтаски

Субтаски декомпозируют задачу на более мелкие единицы. Они **всегда ручные** — нет привязки к внешним источникам (Jira, трекеры и т.д.).

## Структура директории

```
doc/tasks/<parent_task_key>/
├── task.json            (имеет subtasks: [{id, title, status, path}])
└── subtasks/
    ├── 0001/
    │   ├── task.json    (parent_task_key ссылается на родителя)
    │   └── stage1/
    │       ├── plan.md
    │       └── verification.json
    │   └── subtasks/    (рекурсия: у субтаски могут быть свои субтаски)
    │       └── 0001/
    └── 0002/
        ...
```

## `arch task subtask init <parent_task_key> <subtask_id> [--task-type TYPE] [--flow FLOW] [--complexity LEVEL] [--estimate-hours N]`

- Требует наличия `doc/tasks/<parent_task_key>/`.
- `subtask_id` должен быть ровно четырьмя десятичными цифрами.
- Отклоняет, если `doc/tasks/<parent_task_key>/subtasks/<subtask_id>/` уже существует (коллизия).
- Создаёт `subtasks/<subtask_id>/` и `subtasks/<subtask_id>/stage1/`.
- Записывает скффолд `task.json` через `scaffold_subtask_json()` — `task_key` равно `<parent_task_key>-<subtask_id>`, `task_number` равно `<subtask_id>`, `source.type` равно `ui`.
- `--task-type` по умолчанию `subtask` (лист работы, дальнейшая декомпозиция запрещена). `--complexity` наследует сложность родителя. `--flow` и `--estimate-hours` необязательны. CLI проверяет тип, flow и сложность по task-conf.
- Выводит JSON-результат с `ok`, `parent_task_key`, `subtask_id`, `subtask_key`, путями.
- Примечание в выводе: "subtasks are always manual; no external source binding".
- Код выхода 1 при коллизии, неверном ID или отсутствующем родителе.

## `arch task subtask validate <parent_task_key> <subtask_id>`

- Читает `subtasks/<subtask_id>/task.json`.
- Запускает `validate_task_json(data, "<parent_task_key>-<subtask_id>")`.
- Отклоняет, если `task.md` существует в директории субтаски.
- Выводит `subtask <parent_task_key>-<subtask_id> is valid` при успехе.
- Код выхода 1 при ошибке валидации или отсутствующем файле.

## `arch task subtask status <parent_task_key> <subtask_id>`

- Читает `subtasks/<subtask_id>/task.json`.
- Перечисляет директории этапов и вложенные субтаски.
- Выводит JSON с `parent_task_key`, `subtask_id`, `subtask_key`, `directory`, `task_json`, `stages`, `sub_subtasks`, `phase`, `task_type`.
- Код выхода 1, если `task.json` отсутствует.

## Правила

| Правило | Описание |
|---------|----------|
| Только ручно | Нет автоматического создания субтасок или привязки к внешним источникам. |
| Уникальность внутри родителя | `subtask_id` должен быть уникален только среди兄弟-субтасок одного родителя. |
| Рекурсия разрешена | Директория субтаски может содержать свою директорию `subtasks/`. |
| `parent_task_key` | Скффолд `task.json` использует `<parent_task_key>-<subtask_id>` как свой `task_key`. |
| Форма выбирается агентом | `task_type`, `flow`, `complexity` и `estimate_hours` ребёнка выбирает агент по содержанию работы и передаёт в `init` или `decompose`. Жёстко зашитый `scaffold` не используется. |
| Нет `task.md` | `task.json` — единственный канонический вход; `task.md` вызывает ошибку валидации. |
