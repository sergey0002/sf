---
id: RUNBOOK-arch-operations
type: runbook
title: Операционное руководство Arch CLI
summary: "Процедуры восстановления после сбоев, отката изменений, миграции task-conf, обслуживания и диагностики проблем."
status: draft
domain: system
related: [SPEC-cli-implementation, REG-cli-validation-rules, REG-cli-command-map, VIEW-open-constraints]
implemented: false
---

# Операционное руководство Arch CLI

Процедуры для обслуживания, восстановления после сбоев, отката изменений и миграции конфигурации task-conf. Все команды выполняются из корня проекта (`/home/user` по умолчанию).

## 1. Диагностика состояния системы

### 1.1 Проверить все пути doc/

```bash
python doc/tools/arch/__main__.py docs paths --check
```

**Ожидаемый результат:** `All doc/ paths are declared and valid`

**Если ошибки:** discover undeclared файлы, удалите их или добавьте в `doc/config/paths.yaml allowed_paths`.

### 1.2 Проверить валидность архитектурной документации

```bash
python doc/tools/arch/__main__.py validate
```

**Ожидаемый результат:** `Architecture documentation is valid`

**Если ошибки:** Исправьте frontmell, ссылки или ID согласно сообщениям об ошибках.

### 1.3 Проверить конкретную задачу

```bash
python doc/tools/arch/__main__.py task diagnose <task_key>
```

**Пример вывода:**
```
Diagnosis for task UI-0009:
  type: feature  flow: standard-implementation  complexity: medium
  phase: completed
  subtasks: 2/2 closed
  can_close: True
    [completed] UI-0009-0001 — Создать task-conf типы
    [completed] UI-0009-0002 — Создать task-conf потоки
```

### 1.4 Проверить все типы task-conf

```bash
python doc/tools/arch/__main__.py task types
```

**Ожидаемый результат:** 9 типов (audit, bugfix, docs, feature, jira-incoming, planning, refactor, research, scaffold)

### 1.5 Проверить flujo для типа

```bash
python doc/tools/arch/__main__.py task flows --type jira-incoming
```

## 2. Восстановление после сбоев

### 2.1 task.json повреждён (невалидный JSON)

**Симптомы:** `arch task validate <key>` → `ERROR: task.json invalid JSON: ...`

**Восстановление:**
1. Скопируйте повреждённый файл в резервную копию:
   ```bash
   cp doc/tasks/<task_key>/task.json doc/tasks/<task_key>/task.json.corrupt
   ```
2. Восстановите task.json из последней известной рабочей версии (из Git или бэкапа).
3. Повторно валидируйте:
   ```bash
   python doc/tools/arch/__main__.py task validate <task_key>
   ```

### 2.2 task.md существует рядом с task.json

**Симптомы:** `arch task validate <key>` → `ERROR: task.md exists; manifest requires task.json as the only canonical input`

**Восстановление:**
```bash
rm doc/tasks/<task_key>/task.md
python doc/tools/arch/__main__.py task validate <task_key>
```

### 2.3 Недекларированный файл в doc/

**Симптомы:** `arch docs paths --check` → `ERROR: Undeclared path in doc/: <path>`

**Восстановление:**
1. Удалите недопустимый файл:
   ```bash
   rm <path>
   ```
2. Или добавьте путь в `doc/config/paths.yaml allowed_paths` (если это оправдано).
3. Повторно проверьте:
   ```bash
   python doc/tools/arch/__main__.py docs paths --check
   ```

### 2.4 Объявленный путь отсутствует на диске

**Симптомы:** `arch docs paths --check` → `ERROR: Declared path missing on disk: <pattern>`

**Восстановление:**
1. Создайте отсутствующий файл согласно шаблону в paths.yaml.
2. Или удалите объявление из `doc/config/paths.yaml allowed_paths` (если путь больше не нужен).
3. Повторно проверьте.

### 2.5 Subtask не закрыт, задача не закрывается

**Симптомы:** `arch task close <key>` → `ERROR: cannot close task <key>: subtasks not all completed`

**Восстановление:**
1. Диагностика:
   ```bash
   python doc/tools/arch/__main__.py task diagnose <key>
   ```
2. Выполните работу по незакрытым subtask.
3. Обновите phase subtask на `completed` в его task.json.
4. Повторно закройте родительскую задачу:
   ```bash
   python doc/tools/arch/__main__.py task close <key>
   ```

### 2.6 task-conf тип не найден

**Симптомы:** `arch task flows --type <unknown>` → `ERROR: task type '<unknown>' not found in task-conf`

**Восстановление:**
1. Создайте директорию `doc/config/task-conf/types/<unknown>/` с `config.yaml` и `prompt.md`.
2. Добавьте `<unknown>` в `project.task_types` в `doc/config/paths.yaml`.
3. Добавьте шаблоны путей в `allowed_paths` (если отсутствуют).
4. Повторно проверьте.

### 2.7 flow не в allowed_flows для типа

**Симптомы:** `arch task validate <key>` → `ERROR: task.json: flow '<flow>' not allowed for task_type '<type>'`

**Восстановление:**
1. Измените `flow` в task.json на одно из `allowed_flows` для данного типа.
2. Или добавьте новый flujo в `doc/config/task-conf/types/<type>/flows/<flow>/` с `config.yaml` и `prompt.md`.
3. Добавьте flujo в `allowed_flows` в `config.yaml` типа.
4. Повторно валидируйте.

## 3. Откат изменений

### 3.1 Откат task.json

```bash
# Найти последний коммит с task.json
git log --oneline -- doc/tasks/<task_key>/task.json

# Откатить к предыдущей версии
git checkout <commit> -- doc/tasks/<task_key>/task.json

# Повторно валидировать
python doc/tools/arch/__main__.py task validate <task_key>
```

### 3.2 Откат изменений в doc/tools/arch/

```bash
git log --oneline -- doc/tools/arch/
git checkout <commit> -- doc/tools/arch/

# Проверить, что CLI всё ещё работает
python doc/tools/arch/__main__.py task types
python doc/tools/arch/__main__.py docs paths --check
```

### 3.3 Откат task-conf

```bash
git log --oneline -- doc/config/task-conf/
git checkout <commit> -- doc/config/task-conf/

# Проверить валидацию типов
python doc/tools/arch/__main__.py task types
```

### 3.4 Откат paths.yaml

```bash
git checkout <commit> -- doc/config/paths.yaml

# Проверить пути
python doc/tools/arch/__main__.py docs paths --check
```

## 4. Миграция task-conf

### 4.1 Добавление нового типа задачи

1. Создайте директорию:
   ```bash
   mkdir -p doc/config/task-conf/types/<new-type>/
   ```

2. Создайте `config.yaml`:
   ```yaml
   id: <new-type>
   title: "<Название>"
   description: |
     <Описание типа>
   complexity_default: medium
   complexity_allowed:
     - low
     - medium
     - high
     - critical
   allowed_flows:
     - standard-implementation
   default_flow: standard-implementation
   subtask_policy: optional
   close_policy: all_subtasks_required
   required_fields: []
   forbidden_in_scope: []
   ```

3. Создайте `prompt.md` — стартовый промпт типа.

4. Добавьте `<new-type>` в `project.task_types` в `doc/config/paths.yaml`.

5. Добавьте шаблоны путей в `allowed_paths` (если отсутствуют):
   ```yaml
   - "doc/config/task-conf/types/{type}/config.yaml"
   - "doc/config/task-conf/types/{type}/prompt.md"
   ```

6. Проверьте:
   ```bash
   python doc/tools/arch/__main__.py task types
   python doc/tools/arch/__main__.py docs paths --check
   ```

### 4.2 Добавление нового flujo для типа

1. Создайте директорию:
   ```bash
   mkdir -p doc/config/task-conf/types/<type>/flows/<new-flow>/
   ```

2. Создайте `config.yaml`:
   ```yaml
   id: <new-flow>
   title: "<Название>"
   type: <type>
   description: |
     <Описание flujo>
   subtask_policy: optional
   close_policy: all_subtasks_required
   steps:
     - id: intake
       name: Приём
       action: validate_task_json
       output: task.json прошёл валидацию
       gate: task_validated
   ```

3. Создайте `prompt.md` — стартовый промпт flujo.

4. Добавьте `<new-flow>` в `allowed_flows` в `config.yaml` типа.

5. Добавьте шаблон пути в `allowed_paths`:
   ```yaml
   - "doc/config/task-conf/types/{type}/flows/{flow}/config.yaml"
   - "doc/config/task-conf/types/{type}/flows/{flow}/prompt.md"
   ```

6. Проверьте:
   ```bash
   python doc/tools/arch/__main__.py task flows --type <type>
   python doc/tools/arch/__main__.py docs paths --check
   ```

## 5. Обслуживание

### 5.1 Перестроить index.json

```bash
python doc/tools/arch/__main__.py index build
```

### 5.2 Проверить актуальность index.json

```bash
python doc/tools/arch/__main__.py index check
```

### 5.3 Проверить все frontmell и ссылки

```bash
python doc/tools/arch/__main__.py validate
```

### 5.4 Проверить все задачи

```bash
for key in $(ls doc/tasks/); do
  python doc/tools/arch/__main__.py task validate "$key" || echo "FAILED: $key"
done
```

### 5.5 Проверить все subtasks

```bash
for task_dir in doc/tasks/*/subtasks/*/; do
  task_key=$(echo "$task_dir" | sed 's|doc/tasks/\(.*\)/subtasks/.*|\1|')
  subtask_id=$(basename "$task_dir")
  python doc/tools/arch/__main__.py task subtask validate "$task_key" "$subtask_id" || echo "FAILED: $task_key/$subtask_id"
done
```

## 6. Чек-лист перед релизом

| Проверка | Команда | Ожидаемый результат |
|----------|---------|--------------------|
| Все пути doc/ декларированы | `arch docs paths --check` | `All doc/ paths are declared and valid` |
| Архитектурная документация валидна | `arch validate` | `Architecture documentation is valid` |
| Все 9 типов task-conf | `arch task types` | 9 строк, включая jira-incoming |
| jira-incoming имеет 1 flujo | `arch task flows --type jira-incoming` | `jira-process` |
| Все task.json валидны | Цикл `task validate` для всех задач | Все `task <key> is valid` |
| Все закрытые задачи имеют закрытые subtasks | `task diagnose <key>` для каждой закрытой | `can_close: True` |
| task.md отсутствует рядом с task.json | `find doc/tasks/ -name "task.md"` | Пустой результат |

## 7. Эскалация

Если проблема не решается данными процедурами:

1. Создайте задачу типа `audit` или `planning` с описанием проблемы.
2. Обратитесь к владельцу домена для принятия решения.
3. Не вводите обходных решений, которые нарушают инварианты манифеста (task.json единственный canonical input, task.md не создаётся, task_number не аллоцируется автоматически).
