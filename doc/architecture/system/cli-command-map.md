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

# Карта команд CLI

| Команда CLI | Модуль | Функция | Назначение |
|-------------|--------|---------|------------|
| `arch task-key --source X --number N [--prefix P]` | `cli` / `identity` | `main` → `normalize_task_identity` | Вывести task key из источника + номера + опционального префикса |
| `arch list [--type] [--domain] [--status] [--json]` | `cli` / `store` | `main` → `ArchitectureStore.load_documents` | Список документов архитектуры по точным фильтрам метаданных |
| `arch show <id> [--format markdown\|json]` | `cli` / `store` | `main` → `ArchitectureStore.load_documents` | Показать один документ по точному ID |
| `arch index build` | `cli` / `store` | `main` → `ArchitectureStore.build_index` + `write_index` | Атомарно построить `index.json` |
| `arch index check` | `cli` / `store` | `main` → `ArchitectureStore.validate` | Проверить актуальность индекса без записи |
| `arch validate [--json]` | `cli` / `store` | `main` → `ArchitectureStore.validate` | Валидировать все frontmatter, ссылки, ID, индекс |
| `arch task init <task_key>` | `cli` / `schema` / `identity` | `_handle_task` → `scaffold_task_json` + `task_dir` | Создать директорию задачи + скффолд `task.json` |
| `arch task validate <task_key>` | `cli` / `validation` | `_handle_task` → `validate_task_json` | Валидировать структуру и консистентность `task.json` |
| `arch task workspace <task_key>` | `cli` / `validation` | `_handle_task` → `validate_task_json` + детерминированный вывод | Подготовить рабочую область задачи (подсказка ветки, релиз) |
| `arch task status <task_key>` | `cli` | `_handle_task` → прочитать `task.json`, перечислить этапы | Показать состояние задачи, этапы, файлы верификации |
| `arch task subtask init <parent> <id>` | `cli` / `subtask` / `schema` | `_handle_subtask` → `scaffold_subtask_json` + `subtask_dir` | Создать директорию субтаски + скффолд `task.json` |
| `arch task subtask validate <parent> <id>` | `cli` / `validation` | `_handle_subtask` → `validate_task_json` | Валидировать `task.json` субтаски |
| `arch task subtask status <parent> <id>` | `cli` / `subtask` | `_handle_subtask` → `list_stages` + `list_sub_subtasks` | Показать состояние субтаски, этапы, phase, task_type |
| `arch task types` | `cli` / `validation` | `_handle_task` → `load_task_conf_types` | Список всех типов задач из task-conf с allowed_flows, subtask_policy, close_policy |
| `arch task flows --type <type>` | `cli` / `validation` | `_handle_task` → `load_task_conf_flows_for_type` | Список разрешённых flujo для типа задачи |
| `arch task type-prompt --type <type>` | `cli` / `validation` | `_handle_task` → `load_task_conf_prompt` | Вывод стартового промпта типа (как скилл агента) |
| `arch task flow-prompt --type <type> --flow <flow>` | `cli` / `validation` | `_handle_task` → `load_task_conf_flow_prompt` | Вывод стартового промпта flujo |
| `arch task decompose <task_key> --subtask-id NNNN --subtask-title "..."` | `cli` / `subtask` | `_handle_task` → `scaffold_subtask_json` + `subtask_dir` | Создание подзадач через CLI |
| `arch task diagnose <task_key>` | `cli` / `validation` | `_handle_task` → `check_subtasks_closed` | Гант-подобная диагностика: тип, флоу, сложность, подзадачи, блокеры закрытия |
| `arch task close <task_key>` | `cli` / `validation` | `_handle_task` → `check_subtasks_closed` + запись phase=completed | Закрытие задачи — отказ если есть незакрытые подзадачи |
| `arch docs paths --check` | `cli` / `validation` | `validate_paths` | Детектор мусора: файлы вне allowed_paths, frontmatter, типы, статусы |

## Коды выхода

| Код | Значение |
|-----|----------|
| 0 | Успех |
| 1 | Ошибка валидации, отсутствующий файл или коллизия (выводится как `ERROR:` на stderr) |
| 2 | Необработанная команда / внутренняя ошибка |

## Формат вывода

Все структурированные команды выводят JSON в stdout (indent=2, `ensure_ascii=False`). Человекочитаемые команды (`list`, `show --format markdown`, `validate` без `--json`) выводят обычный текст.
