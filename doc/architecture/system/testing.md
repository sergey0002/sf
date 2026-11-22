---
id: SPEC-cli-testing
type: testing-spec
title: Стратегия тестирования Arch CLI
summary: "Что тестировать, как запускать тесты, какие сценарии покрыты, критерии приёмки для CLI и task.json валидации."
status: draft
domain: system
related: [SPEC-cli-implementation, REG-cli-command-map, REG-cli-validation-rules]
implemented: false
---

# Стратегия тестирования Arch CLI

## 1. Цель и охват

Тестирование проверяет, что CLI детерминированно выполняет операции над task.json, task-conf, путями doc/ и архитектурными документами. Тесты не проверяют семантическую правильность задач (это обязанность агента/скиллов), только структурную валидность и детерминированное поведение.

## 2. Уровни тестирования

| Уровень | Что тестируется | Инструменты | Критерии прохождения |
|---------|----------------|-------------|---------------------|
| Unit | Отдельные функции (identity, schema, validation, subtask, store) | pytest / unittest | Все функции возвращают ожидаемые результаты для валидных и невалидных входов |
| Integration | Взаимодействие модулей (CLI → validation → task-conf → task.json) | pytest | Команды CLI выполняются end-to-end без ошибок на валидных данных |
| E2E | Полные сценарии (создать задачу → валидировать → декомпозировать → закрыть) | shell скрипты / pytest | Все команды в цепочке возвращают exit 0, промежуточные состояния корректны |
| Paths | `arch docs paths --check` обнаруживает мусор и отсутствующие пути | pytest | Недекларированные файлы обнаружены, объявленные но отсутствующие пути сообщены |
| Schema | JSON Schema валидация тел документов | pytest / jsonschema | Все типы документов проходят валидацию по своим схемам |

## 3. Unit-тесты

### 3.1 identity.py

| Тест | Вход | Ожидаемый результат |
|------|------|--------------------|
| parse_task_key Jira bare number | `"2045"` | task_number="2045", source_type="jira", source_prefix=None |
| parse_task_key UI | `"UI-2045"` | task_number="2045", source_type="ui", source_prefix=None |
| parse_task_key other | `"GH-2045"` | task_number="2045", source_type="other", source_prefix="GH" |
| parse_task_key invalid | `"abc"` | ValueError |
| normalize_task_identity jira | source="jira", number="2045" | task_key="2045" |
| normalize_task_identity ui | source="ui", number="2045" | task_key="UI-2045" |
| normalize_task_identity other | source="other", number="2045", prefix="GH" | task_key="GH-2045" |
| normalize_task_identity invalid number | number="abc" | ValueError |

### 3.2 constants.py

| Тест | Вход | Ожидаемый результат |
|------|------|--------------------|
| path_is_allowed шаблон с {name} | "doc/tasks/{task_key}/task.json", "doc/tasks/UI-0001/task.json" | True |
| path_is_allowed шаблон с ** | "doc/architecture/**/*.md", "doc/architecture/system/overview.md" | True |
| path_is_allowed несоответствие | "doc/tasks/{task_key}/task.json", "doc/other/file.md" | False |
| TASK_KEY_RE valid | "UI-0009", "2045", "GH-2045" | Match |
| TASK_KEY_RE invalid | "ui-0009", "204", "GH-2045-extra" | No match |
| FLOW_RE valid | "standard-implementation", "jira-process", "minimal-scaffold" | Match |
| FLOW_RE invalid | "Standard", "flow_underscore", "a" | No match |

### 3.3 validation.py

| Тест | Вход | Ожидаемый результат |
|------|------|--------------------|
| validate_task_json валидный | Полный task.json со всеми обязательными полями | [] (пустой список ошибок) |
| validate_task_json missing required field | task.json без task_number | ["task.json: missing required field 'task_number'"] |
| validate_task_json invalid task_number | task_number="abc" | ["task.json: task_number must be exactly four decimal digits"] |
| validate_task_json task_key mismatch | task_key="UI-0001", directory="UI-0002" | ["task.json: task_key 'UI-0001' does not match directory 'UI-0002'"] |
| validate_task_json invalid flow | task_type="feature", flow="invalid-flow" | ["task.json: flow 'invalid-flow' not allowed for task_type 'feature'"] |
| validate_task_json invalid complexity | task_type="feature", complexity="invalid" | ["task.json: complexity must be one of low/medium/high/critical"] |
| validate_task_json subtask_policy required empty | subtask_policy="required", subtasks=[] | ["task.json: subtask_policy is 'required' but subtasks is empty or missing"] |
| validate_task_json subtask_policy forbidden non-empty | subtask_policy="forbidden", subtasks=[{...}] | ["task.json: subtask_policy is 'forbidden' but subtasks is not empty"] |
| validate_task_json research_docs invalid path | research_docs path не под doc/tasks/<key>/research/ | ["task.json: research_docs[0].path must be under ..."] |
| validate_task_json task.md exists | task.json + task.md в одной директории | ["task.md exists; manifest requires task.json as the only canonical input"] |

### 3.4 task-conf loaders

| Тест | Ожидаемый результат |
|------|--------------------|
| load_task_conf_types | 9 типов, каждый с config.yaml и prompt.md |
| load_task_conf_types jira-incoming | 1流: jira-process, subtask_policy=required |
| load_task_conf_types scaffold | 1流: minimal-scaffold, subtask_policy=forbidden |
| load_task_conf_flows_for_type feature | 2 flujo: standard-implementation, research-first |
| load_task_conf_prompt feature | Непустой текст из types/feature/prompt.md |
| load_task_conf_flow_prompt jira-incoming jira-process | Непустой текст из types/jira-incoming/flows/jira-process/prompt.md |

### 3.5 check_subtasks_closed

| Тест | Ожидаемый результат |
|------|--------------------|
| Все subtasks phase=completed | (True, []) |
| Один subtask phase=intake | (False, ["Subtask 0001: phase is 'intake', not completed"]) |
| Нет subtasks директории | (True, []) |

### 3.6 validate_paths

| Тест | Ожидаемый результат |
|------|--------------------|
| Все файлы doc/ декларированы | [] (пустой список) |
| Недекларированный файл в doc/ | ["Undeclared path in doc/: <path> — not listed in ..."] |
| Объявленный точный путь отсутствует | ["Declared path missing on disk: <pattern> — expected by ..."] |
| .md без frontmatter в doc/architecture/ | ["Missing or invalid YAML frontmatter: <path>"] |
| .md с недопустимым type в frontmatter | ["Unknown document type '<type>': <path>"] |

## 4. Integration-тесты

| Тест | Сценарий | Ожидаемый результат |
|------|----------|--------------------|
| CLI task types | `arch task types` | Выводит 9 типов с полями, exit 0 |
| CLI task flows | `arch task flows --type jira-incoming` | Выводит jira-process, exit 0 |
| CLI task type-prompt | `arch task type-prompt --type feature` | Выводит текст prompt.md, exit 0 |
| CLI task flow-prompt | `arch task flow-prompt --type jira-incoming --flow jira-process` | Выводит текст prompt.md, exit 0 |
| CLI task validate | `arch task validate UI-0009` | "task UI-0009 is valid", exit 0 |
| CLI docs paths --check | `arch docs paths --check` | "All doc/ paths are declared and valid", exit 0 |
| CLI task diagnose | `arch task diagnose UI-0009` | Показывает can_close, subtask count, exit 0 |
| CLI task close blocked | `arch task close UI-0009` (открытые subtasks) | Ошибка exit 1 со списком блокеров |
| CLI task close success | `arch task close UI-0009` (все subtasks закрыты) | "Task UI-0009 closed", exit 0 |
| CLI task decompose | `arch task decompose <key> --subtask-id 0001 --subtask-title "Test"` | Создаёт subtask, добавляет в task.json, exit 0 |
| CLI task subtask validate | `arch task subtask validate <parent> <id>` | "subtask ... is valid", exit 0 |

## 5. E2E-тесты

### 5.1 Сценарий: полный жизненный цикл задачи

```
1. arch task init UI-0100
2. arch task validate UI-0100 → "task UI-0100 is valid"
3. arch task decompose UI-0100 --subtask-id 0001 --subtask-title "Research"
4. arch task subtask validate UI-0100 0001 → "subtask UI-0100-0001 is valid"
5. arch task diagnose UI-0100 → can_close=False (1 open subtask)
6. arch task close UI-0100 → ошибка exit 1
7. Обновить subtask phase на completed
8. arch task close UI-0100 → "Task UI-0100 closed", exit 0
```

### 5.2 Сценарий: обнаружение мусора

```
1. Создать файл doc/architecture/random-file.md (не в allowed_paths)
2. arch docs paths --check → ошибка "Undeclared path in doc/..."
3. Удалить файл
4. arch docs paths --check → "All doc/ paths are declared and valid"
```

### 5.3 Сценарий: невалидный task.json

```
1. Создать task.json с отсутствующим обязательным полем
2. arch task validate <key> → список ошибок, exit 1
3. Исправить task.json
4. arch task validate <key> → "task <key> is valid", exit 0
```

## 6. Тестовые фикстуры

### 6.1 Валидный task.json

Хранится в `doc/tasks/UI-0009/task.json` — эталонный валидный task.json со всеми полями, flow, complexity, subtasks, research_docs.

### 6.2 task-conf фикстуры

Все 9 типов в `doc/config/task-conf/types/*/` — эталонные конфиги для тестирования loaders и валидации.

### 6.3 paths.yaml фикстура

`doc/config/paths.yaml` — эталонный конфиг путей для тестирования validate_paths.

## 7. Как запускать тесты

### 7.1 Unit-тесты (прямой запуск)

```bash
cd /home/user/doc/tools
python -m pytest tests/ -v
python -m unittest discover tests/ -v
```

### 7.2 Integration через CLI

```bash
cd /home/user
python doc/tools/arch/__main__.py task types
python doc/tools/arch/__main__.py task flows --type feature
python doc/tools/arch/__main__.py task validate UI-0009
python doc/tools/arch/__main__.py docs paths --check
```

### 7.3 E2E скрипт

```bash
# Запускать из корня проекта
cd /home/user
bash -e << 'EOF'
python doc/tools/arch/__main__.py task init UI-9999
python doc/tools/arch/__main__.py task validate UI-9999
python doc/tools/arch/__main__.py task decompose UI-9999 --subtask-id 0001 --subtask-title "Test subtask"
python doc/tools/arch/__main__.py task diagnose UI-9999
python doc/tools/arch/__main__.py task close UI-9999  # должен失败ть
# ... обновить subtask phase на completed
python doc/tools/arch/__main__.py task close UI-9999  # должен пройти
EOF
```

## 8. Критерии приёмки для CLI

| Критерий | Как проверять |
|----------|---------------|
| Все 9 типов task-conf загружаются | `arch task types` возвращает 9 строк |
| jira-incoming имеет ровно 1 flujo | `arch task flows --type jira-incoming` возвращает jira-process |
| task.json валидируется конфиг-driven | `arch task validate <key>` возвращает ошибки только из конфигов, без хардкода |
| close отказывает при открытых subtasks | `arch task close <key>` с открытыми subtasks → exit 1 |
| close проходит при всех закрытых subtasks | `arch task close <key>` с закрытыми subtasks → exit 0 |
| paths --check проходит на чистом doc/ | `arch docs paths --check` → "All doc/ paths are declared and valid" |
| paths --check обнаруживает мусор | Добавление файла вне allowed_paths → ошибка |
| Детерминизм | Повторный запуск той же команды даёт идентичный результат |
| Нет хардкода enum'ов | Поиск строк "jira-incoming", "feature", "standard-implementation" в *.py должен возвращать только комментарии/строки из YAML загрузки, а не жёсткие проверки |

## 9. Coverage цели

| Модуль | Минимальный coverage |
|--------|---------------------|
| constants.py | 100% |
| identity.py | 100% |
| schema.py | 90% |
| validation.py | 95% |
| store.py | 80% |
| subtask.py | 90% |
| cli.py | 85% |
| body_validation.py | 80% |

## 10. Запуск в CI

```yaml
# Пример конфигурации CI (псевдоформат)
steps:
  - run: pip install -r doc/tools/requirements.txt
  - run: python -m pytest doc/tools/tests/ -v
  - run: python doc/tools/arch/__main__.py task types
  - run: python doc/tools/arch/__main__.py task validate UI-0009
  - run: python doc/tools/arch/__main__.py docs paths --check
  - run: python doc/tools/arch/__main__.py task close UI-0009  # только если все subtasks закрыты
```
