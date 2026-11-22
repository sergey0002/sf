---
id: REG-cli-command-map
type: rule-set
title: Отображение команд CLI на модули и функции
summary: "Сопоставляет каждую команду и подкоманду arch CLI с модулем и функцией, которые её реализуют, для архитектурной прослеживаемости."
status: draft
domain: system
related: [VIEW-cli-package, DOM-task-lifecycle, CAP-addressable-contracts]
implemented: true
---

# Карта команд CLI {#commands}

| Команда CLI | Модуль | Функция | Назначение |
|-------------|--------|---------|------------|
| `arch task-key --source X --number N [--prefix P]` | `cli` / `identity` | `main` → `normalize_task_identity` | Вывести task key из источника + номера + опционального префикса |
| `arch task-key --source ui --next` | `cli` / `task_registry` | `main` → `next_task_key` | Прочитать JSON-реестр и вывести следующий свободный UI-ключ; не сканирует задачи и не резервирует номер |
| `arch task new [--title T]` | `cli/commands/task` / `task_ops` / `task_registry` | `TaskCommand` → `next_task_key` + `init_task` + `register_entry` | Выделить следующий UI-ключ, создать карточку и записать её в реестр одной командой |
| `arch task registry [init|add|check|sync] [--json]` | `cli/commands/task` / `task_registry` | `TaskCommand` → `load_registry` / `register_entry` / `registry_drift` / `sync_registry` | Прочитать реестр, создать его, зарегистрировать карточку, сверить с каталогами или синхронизировать |
| `arch list [--id ID ...] [--type] [--domain] [--status] [--json]` | `cli` / `store` | `ListCommand` → `ArchitectureStore.load_documents` | Метаданные и путь относительно архитектуры без тела. Повторный `--id` запрашивает несколько точных ID. |
| `arch show <id> [--format markdown\|json]` | `cli` / `store` | `main` → `ArchitectureStore.load_documents` | Показать один документ по точному ID |
| `arch index build` | `cli` / `store` | `main` → `ArchitectureStore.build_index` + `write_index` | Атомарно построить `index.json` |
| `arch index check` | `cli` / `store` | `main` → `ArchitectureStore.validate` | Проверить актуальность индекса без записи |
| `arch validate [--json]` | `cli` / `store` | `main` → `ArchitectureStore.validate` | Валидировать все frontmatter, ссылки, ID, индекс |
| `arch task init <task_key>` | `cli/commands/task` / `task_ops` / `schema` | `TaskCommand` → `task_ops.init_task` | Создать директорию задачи и атомарно записать скффолд `task.json` |
| `arch task validate <task_key>` | `cli/commands/task` / `task_ops` / `validation` | `TaskCommand` → `task_ops.load_task` + `validation_errors` | Валидировать структуру и консистентность `task.json` |
| `arch task workspace <task_key> [--json]` | `cli/commands/task` / `task_ops` | `TaskCommand` → `task_ops.workspace_info` | Подготовить рабочую область задачи (подсказка ветки, релиз) и вернуть `preflight`: `clean`/`review`/`isolate`/`unknown`, пересечения незакоммиченных файлов с `changed_files` и разрешёнными модулями. Только чтение. |
| `arch task status <task_key>` | `cli/commands/task` / `task_ops` | `TaskCommand` → `task_ops.status_info` | Показать состояние задачи, этапы, файлы верификации и признак незавершённой записи |
| `arch task subtask init <parent> <id> [--task-type TYPE] [--flow FLOW] [--complexity LEVEL] [--estimate-hours N] [--json]` | `cli/commands/task` / `task_ops` / `subtask` | `TaskCommand` → `task_ops.subtask_init` | Создать директорию субтаски и атомарно записать скффолд `task.json` с выбранными агентом типом, flow, сложностью и оценкой |
| `arch task subtask validate <parent> <id> [--json]` | `cli/commands/task` / `task_ops` | `TaskCommand` → `task_ops.subtask_validate` | Валидировать `task.json` субтаски |
| `arch task subtask status <parent> <id> [--json]` | `cli/commands/task` / `task_ops` | `TaskCommand` → `task_ops.subtask_status` | Показать состояние субтаски, этапы, phase, task_type |
| `arch task types` | `cli/commands/task` / `validation` | `TaskCommand._types` → `load_task_conf_types` | Список всех типов задач из task-conf с allowed_flows, subtask_policy, close_policy |
| `arch task flows --type <type>` | `cli/commands/task` / `validation` | `TaskCommand._flows` → `load_task_conf_flows_for_type` | Список разрешённых flow для типа задачи |
| `arch task type-prompt --type <type>` | `cli/commands/task` / `validation` | `TaskCommand._type_prompt` → `load_task_conf_prompt` | Вывод стартового промпта типа (как скилл агента) |
| `arch task flow-steps --type <type> --flow <flow>` | `cli/commands/task` / `validation` | `TaskCommand._flow_prompt` → `flow_prompt_steps` | JSON с шагами в порядке YAML, `gate`, `output` и путём к источнику промпта. |
| `arch task flow-prompt --type <type> --flow <flow> [--step <id>]` | `cli/commands/task` / `validation` | `TaskCommand._flow_prompt` → загрузчик промпта | Общий Markdown потока или промпт выбранного шага. |
| `arch task select-flow --type <type> [--fact name=value ...]` | `cli/commands/task` / `task_ops` / `flows` | `TaskCommand._select_flow` → `task_ops.select_flow` | Применить версионированную таблицу выбора. Возвращает `rule_id`, `flow`, основание, недостающие факты или ID совпавших правил. |
| `arch task decompose <task_key> --subtask-id NNNN --subtask-title "..." [--subtask-depends-on ID=DEP[,DEP]] [--subtask-type ID=TYPE] [--subtask-flow ID=FLOW] [--subtask-complexity ID=LEVEL] [--subtask-estimate ID=HOURS] [--json]` | `cli/commands/task` / `task_ops` | `TaskCommand` → `task_ops.decompose` | Проверить весь пакет до записи, включая ссылки и циклы зависимостей детей и допустимость выбранного типа/flow/сложности, затем атомарно создать детей и обновить родителя; журнал позволяет возобновить прерванную запись |
| `arch task diagnose <task_key> [--json] [--brief]` | `cli/commands/task` / `task_ops` / `validation` / `acceptance` / `flows` | `TaskCommand` → `task_ops.diagnose` → `closure_state` | Машинные блокировки, `flow_state`, доступные переходы и готовность детей (`ready`/`blocked`/`blocked_by`), `acceptance_plan_ready` для задач с политикой кейсов, включая tier плана и обязательные разделы, и `evidence_freshness` (`current`/`stale`/`missing`/`unknown`) отдельно от исторического закрытия и `write_scope` при объявленном `scope.write_files`. Незавершённая составная запись видна как `incomplete_write` и блокирует закрытие. Краткий режим показывает счётчики и ссылки. |
| `arch task doctor <task_key> [--json] [--brief]` | `cli/commands/task` / `task_ops` | `TaskCommand` → `task_ops.doctor` | Одна read-only сводка: фаза, блокировки, `evidence_freshness`, незавершённая запись, зависимости, счётчики детей и `preflight`. |
| `arch task baseline <key> --file <path> --run <argv>` | `cli/commands/task` / `evidence` | `TaskCommand._baseline` → `task_baseline` | Записать `stageN/baseline.json` с командой, exit code и хешами входов. Отказ, если вход изменился во время запуска. Не заменяет evidence и не блокирует закрытие. |
| `arch task advance <task_key> --event <event> --expected-revision N [--id ID] [--dry-run]` | `cli/commands/task` / `task_ops` / `task_record` / `flows` | `TaskCommand` → `task_ops.advance` | Найти переход по текущему `flow_state` и событию, проверить ревизию и идемпотентность, записать `flow.transitioned` и вернуть обновлённую сводку. Неизвестное событие, конфликт и flow без `flow-1` (`UNSUPPORTED-FLOW`) не меняют состояние. |
| `arch task close <task_key> [--json] [--dry-run]` | `cli/commands/task` / `task_ops` | `TaskCommand` → `task_ops.close` | Предпросмотр без записи. При отказе exit 1 и структурированная ошибка в stderr в JSON-режиме. Успешная запись `phase=completed` атомарна; синхронизирует `subtasks[].status` и `stage_history`, для версионированной записи пишет событие `phase.changed`. Устаревший `snapshot_files` блокирует закрытие. |
| `arch task migrate <key> [--dry-run]` | `cli/commands/task` / `task_ops` / `task_record` | `TaskCommand._record` → `task_ops.migrate_record` | Добавляет `record_version`, `flow_version`, `intent_digest`, `state.json` и `events.jsonl`. Повторный запуск идемпотентен; intent-поля не меняются. |
| `arch task event <key> --id ID --type phase.changed\|result.recorded --expected-revision N [--phase P] [--summary S] [--dry-run]` | `cli/commands/task` / `task_ops` / `task_record` | `TaskCommand._record` → `task_ops.append_record_event` | Проверяет `expected_revision` и ключ идемпотентности. Повтор того же события возвращает исходный результат; другой payload или устаревшая ревизия — конфликт exit 5 без записи. |
| `arch task replay <key> [--dry-run]` | `cli/commands/task` / `task_ops` / `task_record` | `TaskCommand._record` → `task_ops.replay_record` | Пересобирает `state.json` из `events.jsonl`, проверяя цепочку `prev_digest`/`digest`. Повреждённый журнал не материализуется. |
| `arch task evidence <key> --check` / `--file <path> [--case CASE-N] --run <argv>` | `cli/commands/task` / `evidence` | `TaskCommand` → `task_evidence` | Проверка SHA-256 или запуск с фиксацией реального результата на стабильном снимке текущей стадии. `--check` возвращает `status` (`current`/`stale`/`missing`), `stale_files`, `missing_files` и `problems`; exit 1, если снимок не `current`. `<key>` принимает и ключ ребёнка (`UI-0014-0001`). |
| `arch session find --match <text> [--db] [--directory] [--all-projects] [--role] [--limit] [--json]` | `cli/commands/session` / `session_audit` | `SessionCommand` → `find_sessions` | Найти сессии по подстроке текста; вернуть совпадения, `message_id`, сниппет и `truncated`. |
| `arch session digest (<session_id> \| --match <text>) [--db] [--max-events] [--full-text] [--no-children]` | `cli/commands/session` / `session_audit` | `SessionCommand` → `digest_session` | JSON-дайджест: полный `tool_calls`, метки, статистика, фазы, аномалии, токены и `label_index`. Всегда JSON. |
| `arch session events <session_id> [--message] [--part] [--offset] [--limit] [--full]` | `cli/commands/session` / `session_audit` | `SessionCommand` → `session_events` | JSON-срез по `message_id` или `part_id`; неизвестная сессия возвращает пустой результат. |
| `arch docs paths --check` | `cli` / `validation` | `validate_paths` | Детектор мусора: файлы вне allowed_paths, frontmatter, типы, статусы |
| `arch docs paths --resolved` | `cli` / `project_config` | `ProjectConfig` | Выбранный YAML и разрешённые корни в JSON. Запрос без записи. |
| `arch docs tree` | `cli` / `store` | `DocsPathsCommand` → `ArchitectureStore.load_documents` | JSON-оглавление индексируемой архитектуры по каталогам без тел документов. |
| `arch docs read <DOC-ID#section-id> [--max-bytes N] [--json]` | `cli/commands/builtin` / `doc_ops` / `sections` | `DocsPathsCommand` → `read_section` | Один адресуемый раздел: путь, диапазон строк, SHA-256 файла и текст. Частичный текст при превышении бюджета не выдаётся. |
| `arch docs toc <id> [--json]` | `cli/commands/builtin` / `doc_ops` / `sections` | `DocsPathsCommand` → `table_of_contents` | Явные и slug-якоря разделов документа с диапазонами строк. |
| `arch docs search <query> [--scope product\|reference\|all] [--limit N] [--include-archived] [--json]` | `cli/commands/builtin` / `doc_ops` | `DocsPathsCommand` → `search` | Детерминированный локальный поиск по ID, alias, заголовку, summary, разделам и телу. Справочник подключается явно. |
| `arch docs check-links [--json]` | `cli/commands/builtin` / `doc_ops` | `DocsPathsCommand` → `check_links` | Битые локальные ссылки, отсутствующие якоря и выход за корень проекта. |
| `arch docs context --task <key> [--case CASE-N] [--max-bytes N] [--since-snapshot FILE] [--json]` | `cli/commands/builtin` / `doc_ops` | `DocsPathsCommand` → `context` | Ограниченный пакет объявленных ссылок задачи и кейса: причины, авторитет, evidence и дельта снимка. |
| `arch docs impact --since <rev> [--scope docs\|all] [--json]` | `cli/commands/builtin` / `doc_ops` | `DocsPathsCommand` → `impact` | Изменённые разделы и объявленные потребители; непокрытые изменения перечисляются отдельно. |

## Запись и восстановление {#write-recovery}

- Одиночный `task.json` заменяется атомарно через временный файл в том же каталоге и `os.replace` (`fs_atomic.atomic_write_text`). Читатель не видит частично записанную запись.
- `task decompose` проверяет весь пакет до первой записи: формат и уникальность ID, непустые заголовки, уже объявленных детей и существующие каталоги. При любой ошибке не создаётся ни один каталог и родитель не меняется.
- Перед составной записью создаётся журнал `doc/tasks/<key>/.arch-write-journal.json` с типом операции и пакетом. После записи детей и родителя журнал удаляется последним.
- Если процесс прерван, `task diagnose`, `task status` и `scan --scope tasks` показывают журнал. Валидный журнал возобновляется тем же пакетом после проверки всех детей. Повреждённый журнал отображается как `incomplete_write.state: invalid` и требует сверки записей. Журнал блокирует закрытие и отдельное создание детей. Параллельный писатель и конфликт повтора дают exit 5 без записи. [Границы восстановления](implementation-spec.md#914-устойчивая-запись-и-восстановление)
- Версионированная запись разделяет неизменяемый intent (`task.json`), изменяемое состояние (`state.json`) и журнал (`events.jsonl`). `task migrate` идемпотентен, `task event` проверяет ожидаемую ревизию и ключ идемпотентности, `task replay` пересобирает состояние из журнала. `diagnose`/`status` показывают `record.state` (`ok`, `stale`, `missing`, `invalid`). [Запись задачи](../domains/task-lifecycle/entities/task-record.md)

## Коды выхода {#exit-codes}

| Код | Значение |
|-----|----------|
| 0 | Успех, включая пустую выдачу `search` и `context` с `complete: false` |
| 1 | Ошибка валидации, отсутствующий или неоднозначный документ/якорь, инциденты `check-links`, коллизия |
| 2 | Неверные аргументы, неизвестная ревизия Git или нечитаемый снимок |

## Документальные контракты {#doc-contracts}

`read`, `toc`, `search`, `check-links`, `context` и `impact` работают с текущим checkout, не пишут в репозиторий и не обращаются к сети. Явный якорь `{#anchor}` стабилен к переносу и переименованию; slug-якорь служит совместимым резервом. `context` включает только объявленные ссылки задачи и кейса, а `impact` — только объявленных потребителей; текстовое совпадение не считается доказанным влиянием. Полный контракт — [Адресуемые контракты документации](addressable-contracts.md).

## Формат вывода {#output-format}

Все структурированные команды выводят JSON в stdout (indent=2, `ensure_ascii=False`). `session digest` и `session events` всегда выводят JSON. Человекочитаемые команды (`list`, `show --format markdown`, `validate` без `--json`, `session find` без `--json`) выводят обычный текст.

## Глобальные параметры {#global-options}

`--root`, `--config` и `--version` доступны до имени команды. `--version` печатает `arch <version>` из `arch.__version__`; `pyproject.toml` получает ту же версию динамически. Свежесть индекса проверяется локальным gate `bash doc/tests/run.sh --gate`: `index check` до любой пересборки, затем две независимые пересборки с разными `PYTHONHASHSEED` во временных деревьях. CI/CD и Git-hosted workflow запрещены.
