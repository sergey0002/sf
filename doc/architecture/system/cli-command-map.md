---
id: REG-cli-command-map
type: rule-set
title: Отображение команд CLI на модули и функции
summary: "Сопоставляет каждую команду и подкоманду arch CLI с модулем и функцией, которые её реализуют, для архитектурной прослеживаемости."
status: draft
domain: system
related: [VIEW-cli-package, DOM-task-lifecycle]
implemented: true
---

# Карта команд CLI {#commands}

| Команда CLI | Модуль | Функция | Назначение |
|-------------|--------|---------|------------|
| `arch task-key --source X --number N [--prefix P]` | `cli` / `identity` | `main` → `normalize_task_identity` | Вывести task key из источника + номера + опционального префикса |
| `arch list [--id ID ...] [--type] [--domain] [--status] [--json]` | `cli` / `store` | `ListCommand` → `ArchitectureStore.load_documents` | Метаданные и путь относительно архитектуры без тела. Повторный `--id` запрашивает несколько точных ID. |
| `arch show <id> [--format markdown\|json]` | `cli` / `store` | `main` → `ArchitectureStore.load_documents` | Показать один документ по точному ID |
| `arch index build` | `cli` / `store` | `main` → `ArchitectureStore.build_index` + `write_index` | Атомарно построить `index.json` |
| `arch index check` | `cli` / `store` | `main` → `ArchitectureStore.validate` | Проверить актуальность индекса без записи |
| `arch validate [--json]` | `cli` / `store` | `main` → `ArchitectureStore.validate` | Валидировать все frontmatter, ссылки, ID, индекс |
| `arch task init <task_key>` | `cli/commands/task` / `task_ops` / `schema` | `TaskCommand` → `task_ops.init_task` | Создать директорию задачи и атомарно записать скффолд `task.json` |
| `arch task validate <task_key>` | `cli/commands/task` / `task_ops` / `validation` | `TaskCommand` → `task_ops.load_task` + `validation_errors` | Валидировать структуру и консистентность `task.json` |
| `arch task workspace <task_key>` | `cli/commands/task` / `task_ops` | `TaskCommand` → `task_ops.workspace_info` | Подготовить рабочую область задачи (подсказка ветки, релиз) |
| `arch task status <task_key>` | `cli/commands/task` / `task_ops` | `TaskCommand` → `task_ops.status_info` | Показать состояние задачи, этапы, файлы верификации и признак незавершённой записи |
| `arch task subtask init <parent> <id>` | `cli/commands/task` / `task_ops` / `subtask` | `TaskCommand` → `task_ops.subtask_init` | Создать директорию субтаски и атомарно записать скффолд `task.json` |
| `arch task subtask validate <parent> <id>` | `cli/commands/task` / `task_ops` | `TaskCommand` → `task_ops.subtask_validate` | Валидировать `task.json` субтаски |
| `arch task subtask status <parent> <id>` | `cli/commands/task` / `task_ops` | `TaskCommand` → `task_ops.subtask_status` | Показать состояние субтаски, этапы, phase, task_type |
| `arch task types` | `cli/commands/task` / `validation` | `TaskCommand._types` → `load_task_conf_types` | Список всех типов задач из task-conf с allowed_flows, subtask_policy, close_policy |
| `arch task flows --type <type>` | `cli/commands/task` / `validation` | `TaskCommand._flows` → `load_task_conf_flows_for_type` | Список разрешённых flow для типа задачи |
| `arch task type-prompt --type <type>` | `cli/commands/task` / `validation` | `TaskCommand._type_prompt` → `load_task_conf_prompt` | Вывод стартового промпта типа (как скилл агента) |
| `arch task flow-steps --type <type> --flow <flow>` | `cli/commands/task` / `validation` | `TaskCommand._flow_prompt` → `flow_prompt_steps` | JSON с шагами в порядке YAML, `gate`, `output` и путём к источнику промпта. |
| `arch task flow-prompt --type <type> --flow <flow> [--step <id>]` | `cli/commands/task` / `validation` | `TaskCommand._flow_prompt` → загрузчик промпта | Общий Markdown потока или промпт выбранного шага. |
| `arch task decompose <task_key> --subtask-id NNNN --subtask-title "..."` | `cli/commands/task` / `task_ops` | `TaskCommand` → `task_ops.decompose` | Проверить весь пакет до записи, затем атомарно создать детей и обновить родителя; журнал позволяет возобновить прерванную запись |
| `arch task diagnose <task_key> [--json] [--brief]` | `cli/commands/task` / `task_ops` / `validation` / `acceptance` | `TaskCommand` → `task_ops.diagnose` → `closure_state` | Машинные блокировки и состояние детей, `acceptance_plan_ready` для задач с политикой кейсов. Незавершённая составная запись видна как `incomplete_write` и блокирует закрытие. Краткий режим показывает счётчики и ссылки. |
| `arch task close <task_key> [--json] [--dry-run]` | `cli/commands/task` / `task_ops` | `TaskCommand` → `task_ops.close` | Предпросмотр без записи. При отказе exit 1 и структурированная ошибка в stderr в JSON-режиме. Успешная запись `phase=completed` атомарна. |
| `arch task evidence <key> --check` / `--file <path> [--case CASE-N] --run <argv>` | `cli/commands/task` / `evidence` | `TaskCommand` → `task_evidence` | Проверка SHA-256 или запуск с фиксацией реального результата на стабильном снимке текущей стадии. `<key>` принимает и ключ ребёнка (`UI-0014-0001`). |
| `arch session find --match <text> [--db] [--directory] [--all-projects] [--role] [--limit] [--json]` | `cli/commands/session` / `session_audit` | `SessionCommand` → `find_sessions` | Найти сессии по подстроке диалога; вернуть совпадения, `message_id` и сниппет. |
| `arch session digest <session_id> [--db] [--max-events] [--full-text] [--no-children]` | `cli/commands/session` / `session_audit` | `SessionCommand` → `digest_session` | Компактный JSON-дайджест: метки flow, скиллов, правил и задач, статистика инструментов, фазы, аномалии, токены и `label_index`. |
| `arch session events <session_id> [--message] [--part] [--offset] [--limit] [--full]` | `cli/commands/session` / `session_audit` | `SessionCommand` → `session_events` | Точечный срез диалога по `message_id` или `part_id` без перечитывания всей сессии. |
| `arch docs paths --check` | `cli` / `validation` | `validate_paths` | Детектор мусора: файлы вне allowed_paths, frontmatter, типы, статусы |
| `arch docs paths --resolved` | `cli` / `project_config` | `ProjectConfig` | Выбранный YAML и разрешённые корни в JSON. Запрос без записи. |
| `arch docs tree` | `cli` / `store` | `DocsPathsCommand` → `ArchitectureStore.load_documents` | JSON-оглавление индексируемой архитектуры по каталогам без тел документов. |

## Запись и восстановление {#write-recovery}

- Одиночный `task.json` заменяется атомарно через временный файл в том же каталоге и `os.replace` (`fs_atomic.atomic_write_text`). Читатель не видит частично записанную запись.
- `task decompose` проверяет весь пакет до первой записи: формат и уникальность ID, непустые заголовки, уже объявленных детей и существующие каталоги. При любой ошибке не создаётся ни один каталог и родитель не меняется.
- Перед составной записью создаётся журнал `doc/tasks/<key>/.arch-write-journal.json` с типом операции и пакетом. После записи детей и родителя журнал удаляется последним.
- Если процесс прерван, `task diagnose`, `task status` и `scan --scope tasks` показывают журнал. Валидный журнал возобновляется тем же пакетом после проверки всех детей. Повреждённый журнал отображается как `incomplete_write.state: invalid` и требует сверки записей. Журнал блокирует закрытие и отдельное создание детей. Параллельный писатель и конфликт повтора дают exit 5 без записи. [Границы восстановления](implementation-spec.md#914-устойчивая-запись-и-восстановление)

## Коды выхода {#exit-codes}

| Код | Значение |
|-----|----------|
| 0 | Успех |
| 1 | Ошибка валидации, отсутствующий файл или коллизия (выводится как `ERROR:` на stderr) |
| 2 | Необработанная команда / внутренняя ошибка |

## Формат вывода {#output-format}

Все структурированные команды выводят JSON в stdout (indent=2, `ensure_ascii=False`). `session digest` и `session events` всегда выводят JSON. Человекочитаемые команды (`list`, `show --format markdown`, `validate` без `--json`, `session find` без `--json`) выводят обычный текст.

## Глобальные параметры {#global-options}

`--root`, `--config` и `--version` доступны до имени команды. `--version` печатает `arch <version>` из `arch.__version__`; `pyproject.toml` получает ту же версию динамически. CI вызывает `index check` до любой пересборки и проверяет воспроизводимость двумя независимыми пересборками с разными `PYTHONHASHSEED` во временных деревьях.
