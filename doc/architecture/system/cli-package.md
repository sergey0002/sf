---
id: VIEW-cli-package
type: component-view
title: Структура пакета Arch CLI и ответственность модулей
summary: "Модульный Python-пакет под doc/tools/arch/; ответственность каждого модуля и граф зависимостей между ними."
status: draft
domain: system
related: [REG-cli-command-map, SYS-simple-factory, DOM-task-lifecycle]
implemented: true
---

# Arch CLI: структура пакета

CLI был рефакторен из одного файла `arch.py` (~900 строк) в модульный Python-пакет под `doc/tools/arch/`. Каждый модуль имеет единственную, чётко определённую ответственность. Поверхность CLI расширена: `list`, `show`, `index`, `validate`, `task-key`, `task`, `task subtask`, `task types`, `task flows`, `task type-prompt`, `task flow-prompt`, `task decompose`, `task diagnose`, `task close`, `docs paths --check`.

## Карта модулей

| Модуль | Ответственность | Зависит от |
|--------|-----------------|------------|
| `constants.py` | Регексы, имена ключей для загрузки из YAML-конфигов (task_types, phases, risk_levels, source_types, task_schema_required_fields, task-conf ключи), `TASK_KEY_RE`, `FLOW_RE`, `path_is_allowed()` | — |
| `identity.py` | Вывод task-key (`normalize_task_identity`, `parse_task_key`, `task_dir`). Никогда не аллоцирует номера. | `constants` |
| `schema.py` | Шаблон `task.json` (`draft-0.2`) и `scaffold_task_json()` | — |
| `validation.py` | `validate_task_json()` — валидация конфиг-driven (все правила из YAML), `load_task_conf_types()`, `load_task_conf_flows_for_type()`, `load_task_conf_prompt()`, `load_task_conf_flow_prompt()`, `check_subtasks_closed()`, `validate_paths()`, `load_paths_config()` | `constants`, `store` (для check_subtasks_closed) |
| `store.py` | `ArchitectureStore` — загрузка документов с frontmatter, валидация ссылок/ID, сборка/проверка `index.json` | (внутри пакета arch — нет) |
| `subtask.py` | Пути субтасок, скффолд JSON, перечисление этапов и вложенных субтасок | `identity`, `schema` |
| `cli/app.py` | Парсер `argparse`, `run()`, диспетчеризация зарегистрированных команд | `cli.commands`, `store` |
| `cli/output.py` | JSON-envelope, human/brief/quiet/verbose режимы, scan-сводка | `cli.errors` |
| `cli/errors.py` | `CliError`, `CliEnvelope`, семантические exit-коды, `ok_envelope`/`error_envelope` | — |
| `cli/commands/` | `Command`-интерфейс, реестр и команды: `list`, `show`, `index`, `validate`, `scan`, `docs`, `task`, `task-key` | `identity`, `validation`, `store`, `subtask` |
| `__init__.py` | Публичный API, версия пакета (`0.2.0`) | все (реэкспорт) |
| `__main__.py` | Точка входа для `python -m arch` и прямого запуска файла | `cli.app` |

## Граф зависимостей

```
constants.py
   ▲
   │
identity.py  schema.py  validation.py  store.py
   ▲          ▲          ▲
   │          │          │
subtask.py (identity, schema)
   ▲
   │
   └──── cli/commands/ ────────┘
         (identity, schema, validation, store, subtask, constants)
         ▲
         │
    cli/app.py
         ▲
         │
    __main__.py
         ▲
         │
     python -m arch / прямой запуск файла
```

## Принципы проектирования

- **Детерминизм:** никакого автоматического выделения ID или номеров; каждый ключ и номер выводятся из явного ввода.
- **Конфиг-driven валидация:** все enum'ы, обязательные поля, allowed_flows, complexity_levels читаются из YAML-конфигов (`doc/config/paths.yaml`, `doc/config/task-conf/types/*/config.yaml`). Нет хардкода в Python.
- **Семантические решения принадлежат агенту/скиллам:** CLI валидирует структуру и перечисления; он никогда не угадывает релевантность и не заполняет семантические поля.
- **`task.json` — единственный канонический вход задачи:** `task.md` отвергается, если присутствует.
- **Субтаски всегда ручные:** нет привязки к внешним источникам (Jira, трекеры и т.д.).
- **Контроль закрытия задач:** `arch task close` отказывает если есть подзадачи с `phase != completed` (close_policy).
- **Детектор мусора:** `arch docs paths --check` выявляет файлы в `doc/` вне `allowed_paths`.
- **Обработка ошибок:** все доменные модули возвращают списки ошибок или выбрасывают `ValueError`/`OSError`; `cli.app.run()` конвертирует их в семантический exit-код и единый JSON-envelope. Структурированные команды в human-режиме печатают свой envelope, а не scan-сводку.

## Точки входа

- `python3 -m arch` (из `doc/tools/`)
- `python3 doc/tools/arch/__main__.py` (прямой запуск, работает из любого cwd)
