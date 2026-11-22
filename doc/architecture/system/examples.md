---
id: EXAMPLES-cli-usage
type: examples
title: Примеры использования CLI и task.json
summary: "Полные примеры task.json, сценарии команд CLI, обработка ошибок, E2E потоки для всех типов задач."
status: draft
domain: system
related: [SPEC-cli-implementation, REG-cli-validation-rules, REG-cli-command-map]
implemented: false
---

# Примеры использования CLI и task.json

Этот документ содержит рабочие примеры task.json, вызовы команд CLI, сценарии обработки ошибок и E2E потоки. Все примеры могут быть использованы как эталон при реализации или тестировании CLI.

## 1. task.json примеры

### 1.1 Эталонный валидный task.json (UI-0009, тип feature)

```json
{
  "schema_version": "draft-0.2",
  "task_id": null,
  "task_key": "UI-0009",
  "task_number": "0009",
  "source": {
    "type": "ui",
    "native_id": null,
    "provenance": "created by user request",
    "revision": null,
    "captured_at": null,
    "attachments": [],
    "comments": [],
    "history": []
  },
  "title": "Разработка строгой структуры документации",
  "kind": "feature",
  "intent": "Ввести жёсткое регулирование структуры doc/",
  "scope": {
    "in": ["YAML-конфиг путей doc/config/paths.yaml", "Строгий скилл architecture-docs"],
    "out": ["Изменение kanoničeskogo формата task.json", "Автоматическое удаление файлов без подтверждения"],
    "allowed_files_modules": ["doc/config/paths.yaml", "doc/tools/arch/validation.py"]
  },
  "current_behavior": null,
  "evidence": [],
  "contracts_and_invariants": ["task.json остаётся единственным каноническим входом задачи"],
  "acceptance_criteria": [
    {"id": "AC-1", "statement": "doc/config/paths.yaml декларирует все допустимые пути", "verification": "arch docs paths --check проходит"}
  ],
  "implementation_plan": "Создать task-conf иерархию, конфиг путей, CLI валидатор путей",
  "target_release": "unset",
  "project_context_refs": [],
  "constraints": ["Никакого автоматического выделения task_number", "Никакого task.md"],
  "assumptions": [],
  "open_questions": [],
  "risk": "medium",
  "authority": {"allowed": [], "forbidden": [], "approval_required": []},
  "approvals": [],
  "task_type": "feature",
  "flow": "standard-implementation",
  "complexity": "medium",
  "subtasks": [
    {"id": "0001", "title": "Создать task-conf типы", "status": "completed", "path": "subtasks/0001/task.json"},
    {"id": "0002", "title": "Создать task-conf потоки", "status": "completed", "path": "subtasks/0002/task.json"}
  ],
  "depends_on": [],
  "phase": "completed",
  "rollback_plan": "Откатить изменения в doc/config/paths.yaml",
  "related_docs": [],
  "related_tests": [],
  "research_docs": [
    {
      "id": "res-001",
      "title": "Исследование дизайна task-conf",
      "path": "doc/tasks/UI-0009/research/task-conf-design-notes.md",
      "source_type": "internal",
      "source_ref": "doc/tasks/UI-0009/research/task-conf-design-notes.md",
      "summary": "Иерархическая конфигурация типов и потоков задач",
      "status": "confirmed"
    }
  ],
  "changed_files": {
    "added": ["doc/config/paths.yaml"],
    "modified": ["doc/tools/arch/validation.py"],
    "deleted": []
  },
  "owner": "unset",
  "priority": "unset",
  "stage_history": [
    {
      "stage_id": "stage1",
      "status": "completed",
      "result": "Создан task.json, валидация проходит",
      "evidence_refs": ["doc/config/paths.yaml", "doc/tools/arch/validation.py"]
    }
  ]
}
```

### 1.2 task.json для типа jira-incoming (bare four-digit number)

```json
{
  "schema_version": "draft-0.2",
  "task_id": null,
  "task_key": "2045",
  "task_number": "2045",
  "source": {
    "type": "jira",
    "native_id": "PROJ-2045",
    "provenance": "Jira adapter sync",
    "revision": null,
    "captured_at": null,
    "attachments": [],
    "comments": [],
    "history": []
  },
  "title": "Исправить баг в аутентификации",
  "kind": "bugfix",
  "intent": "Исправить ошибку проверки пароля в модуле аутентификации",
  "scope": {
    "in": ["Исправление кода аутентификации", "Добавление теста"],
    "out": ["Рефакторинг unrelated модулей", "Изменение API контрактов"],
    "allowed_files_modules": ["src/auth/login.py", "tests/test_auth.py"]
  },
  "current_behavior": "Пароль не проверяется на соответствие политике сложности",
  "evidence": [],
  "contracts_and_invariants": ["Аутентификация должна отклонять слабые пароли"],
  "acceptance_criteria": [
    {"id": "AC-1", "statement": "Пароли shorter 8 символов отклоняются", "verification": "Тест test_password_policy проходит"}
  ],
  "implementation_plan": "Добавить валидацию длины пароля, покрыть тестами",
  "target_release": "v2.1",
  "project_context_refs": [],
  "constraints": ["Без автоматического выделения task_number"],
  "assumptions": [],
  "open_questions": [],
  "risk": "high",
  "authority": {"allowed": [], "forbidden": [], "approval_required": ["merge"]},
  "approvals": [],
  "task_type": "bugfix",
  "flow": "standard-implementation",
  "complexity": "medium",
  "subtasks": [
    {"id": "0001", "title": "Исправить код", "status": "completed", "path": "subtasks/0001/task.json"},
    {"id": "0002", "title": "Добавить тесты", "status": "completed", "path": "subtasks/0002/task.json"}
  ],
  "depends_on": [],
  "phase": "completed",
  "rollback_plan": "Откатить через git revert коммит исправления",
  "related_docs": [],
  "related_tests": [{"test_id": "test_password_policy", "suite": "unit", "location": "tests/test_auth.py", "command": "pytest tests/test_auth.py"}],
  "research_docs": [],
  "changed_files": {
    "added": [],
    "modified": ["src/auth/login.py", "tests/test_auth.py"],
    "deleted": []
  },
  "owner": "unset",
  "priority": "unset",
  "stage_history": [
    {"stage_id": "stage1", "status": "completed", "result": "Баг исправлен, тесты проходят", "evidence_refs": ["tests/test_auth.py"]}
  ]
}
```

### 1.3 task.json для типа scaffold

```json
{
  "schema_version": "draft-0.2",
  "task_id": null,
  "task_key": "UI-0001",
  "task_number": "0001",
  "source": {
    "type": "ui",
    "native_id": null,
    "provenance": "user request in chat",
    "revision": null,
    "captured_at": null,
    "attachments": [],
    "comments": [],
    "history": []
  },
  "title": "Create the simple software-factory architecture scaffold",
  "kind": "scaffold",
  "intent": "Create a project folder with architecture documentation",
  "scope": {
    "in": ["Create doc/architecture", "Create doc/tools CLI", "Create this task.json"],
    "out": ["Do not copy the root manifest into simple/", "Do not implement a pilot"],
    "allowed_files_modules": []
  },
  "current_behavior": null,
  "evidence": [],
  "contracts_and_invariants": ["task.json is the only canonical task input"],
  "acceptance_criteria": [
    {"id": "AC-1", "statement": "CLI can list/show docs, build/check index", "verification": "Run arch validate/index check"}
  ],
  "implementation_plan": "Создать структуру doc/, task.conf, CLI валидатор",
  "target_release": "unset",
  "project_context_refs": [],
  "constraints": ["task.json is the only canonical task input", "task.md не создаётся"],
  "assumptions": [],
  "open_questions": [],
  "risk": "low",
  "authority": {"allowed": ["inspect", "edit_task_scope"], "forbidden": ["merge", "deploy"], "approval_required": ["merge"]},
  "approvals": [],
  "task_type": "scaffold",
  "flow": "minimal-scaffold",
  "complexity": "low",
  "subtasks": [],
  "depends_on": [],
  "phase": "completed",
  "rollback_plan": null,
  "related_docs": [],
  "related_tests": [],
  "research_docs": [],
  "changed_files": {"added": [], "modified": [], "deleted": []},
  "owner": "unset",
  "priority": "unset",
  "stage_history": []
}
```

## 2. Вызовы команд CLI и ожидаемый вывод

### 2.1 task types

```
$ arch task types
audit	Аудит	default_flow=research-first	subtasks=optional	close=all_subtasks_required	flows=1
bugfix	Исправление ошибки	default_flow=standard-implementation	subtasks=optional	close=all_subtasks_required	flows=2
docs	Документация	default_flow=docs-only	subtasks=optional	close=all_subtasks_required	flows=1
feature	Новая функциональность	default_flow=standard-implementation	subtasks=required	close=all_subtasks_required	flows=2
jira-incoming	Вcoming задача из Jira	default_flow=jira-process	subtasks=required	close=all_subtasks_required	flows=1
planning	Планирование	default_flow=research-first	subtasks=optional	close=all_subtasks_required	flows=2
refactor	Рефакторинг	default_flow=standard-implementation	subtasks=optional	close=all_subtasks_required	flows=2
research	Исследование	default_flow=research-first	subtasks=optional	close=all_subtasks_required	flows=1
scaffold	Создание каркаса	default_flow=minimal-scaffold	subtasks=forbidden	close=all_subtasks_required	flows=1
```

### 2.2 task flows --type jira-incoming

```
$ arch task flows --type jira-incoming
Flows for task type jira-incoming:
  jira-process	Процесс обработки входящей задачи из Jira	(jira-incoming)
```

### 2.3 task type-prompt --type jira-incoming

```
$ arch task type-prompt --type jira-incoming
# Стартовый промпт типа jira-incoming

Это стартовый промпт (по принципу скилла), который исполняется при начале работы над задачей типа `jira-incoming`.

## Контекст

Задача поступила из внешнего трекера Jira. Её нужно нормализовать в canonical `task.json`, пройти через единственный flujo процесса `jira-process` и закрыть только после выполнения всех подзадач и получения approval.

...
```

### 2.4 task validate UI-0009

```
$ arch task validate UI-0009
task UI-0009 is valid
```

### 2.5 task validate с ошибкой

```
$ arch task validate UI-9999
ERROR: task.json: missing required field 'flow'
ERROR: task.json: flow must be one of standard-implementation/research-first for task_type feature
```

### 2.6 task diagnose UI-0009 (с открытыми subtasks)

```
Diagnosis for task UI-0009:
  type: feature  flow: standard-implementation  complexity: medium
  phase: completed
  subtasks: 0/2 closed
  can_close: False
  blockers:
    - Subtask 0001: phase is 'intake', not completed
    - Subtask 0002: phase is 'intake', not completed
    [intake ] UI-0009-0001 — Создать task-conf типы
    [intake ] UI-0009-0002 — Создать task-conf потоки
```

### 2.7 task diagnose UI-0009 (все subtasks закрыты)

```
Diagnosis for task UI-0009:
  type: feature  flow: standard-implementation  complexity: medium
  phase: completed
  subtasks: 2/2 closed
  can_close: True
    [completed] UI-0009-0001 — Создать task-conf типы
    [completed] UI-0009-0002 — Создать task-conf потоки
```

### 2.8 task close UI-0009 (закрыто)

```
Task UI-0009 closed (phase=completed). All subtasks verified completed.
```

### 2.9 task close UI-0009 (открытые subtasks — ошибка)

```
ERROR: cannot close task UI-0009: subtasks not all completed
  - Subtask 0001: phase is 'intake', not completed
```

### 2.10 docs paths --check

```
$ arch docs paths --check
All doc/ paths are declared and valid
```

### 2.11 docs paths --check с мусором

```
ERROR: Undeclared path in doc/: doc/architecture/random-file.md — not listed in doc/config/paths.yaml allowed_paths
```

### 2.12 task decompose

```
$ arch task decompose UI-0010 --subtask-id 0001 --subtask-title "Исследовать существующий код"
{
  "ok": true,
  "task_key": "UI-0010",
  "subtasks_created": [
    {
      "subtask_id": "0001",
      "title": "Исследовать существующий код",
      "directory": "doc/tasks/UI-0010/subtasks/0001",
      "task_json": "doc/tasks/UI-0010/subtasks/0001/task.json",
      "stage_dir": "doc/tasks/UI-0010/subtasks/0001/stage1"
    }
  ]
}
```

### 2.13 task-key

```
$ arch task-key --source jira --number 2045
{
  "task_key": "2045",
  "task_number": "2045",
  "source_type": "jira",
  "source_prefix": null
}

$ arch task-key --source ui --number 2045
{
  "task_key": "UI-2045",
  "task_number": "2045",
  "source_type": "ui",
  "source_prefix": null
}

$ arch task-key --source other --number 2045 --prefix GH
{
  "task_key": "GH-2045",
  "task_number": "2045",
  "source_type": "other",
  "source_prefix": "GH"
}
```

## 3. Сценарии обработки ошибок

### 3.1 Отсутствующее обязательное поле

```
$ arch task validate UI-9999
ERROR: task.json: missing required field 'flow'
```

**Исправление:** Добавить поле `flow` со значением из `allowed_flows` для данного `task_type`.

### 3.2 Несовпадение task_key с директорией

```
ERROR: task.json: task_key 'UI-0001' does not match directory 'UI-0002'
```

**Исправление:** Переименовать директорию в `UI-0001` или изменить `task_key` в task.json на `UI-0002`.

### 3.3 task_number не четыре цифры

```
ERROR: task.json: task_number must be exactly four decimal digits, got 'abc'
```

**Исправление:** Установить `task_number` в значение из 4 десятичных цифр (например, `0001`).

### 3.4 flow не в allowed_flows

```
ERROR: task.json: flow 'invalid-flow' not allowed for task_type 'feature'; allowed: standard-implementation, research-first
```

**Исправление:** Установить `flow` в одно из разрешённых значений для типа `feature`.

### 3.5 subtask_policy required но subtasks пуст

```
ERROR: task.json: subtask_policy is 'required' but subtasks is empty or missing
```

**Исправление:** Создать至少 один subtask через `arch task decompose <key> --subtask-id NNNN --subtask-title "..."`.

### 3.6 task.md существует рядом с task.json

```
ERROR: task.md exists; manifest requires task.json as the only canonical input
```

**Исправление:** Удалить файл `task.md` из директории задачи.

### 3.7 subtask директория уже существует

```
ERROR: subtask directory already exists: doc/tasks/UI-0009/subtasks/0001
```

**Исправление:** Использовать другой `subtask-id` или удалить существующую директорию.

### 3.8 task_task_key невалидный

```
ERROR: task_key 'ui-0009' does not match pattern: must be Jira bare number, UI-<number>, or PREFIX-<number>
```

**Исправление:** Использовать корректный формат: `UI-0009` для UI, `2045` для Jira, `GH-2045` для других источников.

## 4. E2E потоки

### 4.1 Полный жизненный цикл задачи типа feature

```bash
# 1. Создать задачу
python doc/tools/arch/__main__.py task init UI-0100

# 2. Заполнить task.json полями task_type, flow, complexity, subtasks
# (ручное редактирование task.json)

# 3. Валидировать
python doc/tools/arch/__main__.py task validate UI-0100
# → "task UI-0100 is valid"

# 4. Проверить пути doc/
python doc/tools/arch/__main__.py docs paths --check
# → "All doc/ paths are declared and valid"

# 5. Декомпозировать на subtasks (если subtask_policy: required)
python doc/tools/arch/__main__.py task decompose UI-0100 \
  --subtask-id 0001 --subtask-title "Исследовать существующий код" \
  --subtask-id 0002 --subtask-title "Реализовать изменение"

# 6. Проверить диагноз
python doc/tools/arch/__main__.py task diagnose UI-0100
# → subtasks: 0/2 closed, can_close: False

# 7. Выполнить работу, обновить phase subtask на completed
# (ручное редактирование subtask task.json)

# 8. Проверить диагноз снова
python doc/tools/arch/__main__.py task diagnose UI-0100
# → subtasks: 2/2 closed, can_close: True

# 9. Закрыть задачу
python doc/tools/arch/__main__.py task close UI-0100
# → "Task UI-0100 closed (phase=completed). All subtasks verified completed."
```

### 4.2 Поток типа jira-incoming

```bash
# Jira задача — bare four-digit number, без префикса UI-
python doc/tools/arch/__main__.py task init 2045

# task_type: jira-incoming, flow: jira-process (единственный доступный)
# subtask_policy: required — должны быть созданы subtasks

python doc/tools/arch/__main__.py task decompose 2045 \
  --subtask-id 0001 --subtask-title "Приём и валидация" \
  --subtask-id 0002 --subtask-title "Реализация" \
  --subtask-id 0003 --subtask-title "Верификация"

python doc/tools/arch/__main__.py task validate 2045
python doc/tools/arch/__main__.py task diagnose 2045
# → can_close: False (пока subtasks не завершены)

# После завершения всех subtasks:
python doc/tools/arch/__main__.py task close 2045
# → "Task 2045 closed (phase=completed)."
```

### 4.3 Поток типа scaffold (subtask_policy: forbidden)

```bash
python doc/tools/arch/__main__.py task init UI-0200
# task_type: scaffold, flow: minimal-scaffold
# subtask_policy: forbidden — subtasks не должны быть созданы

# Попытка создать subtask — ошибка валидации
# subtask_policy: forbidden но subtasks не пуст → ошибка

python doc/tools/arch/__main__.py task validate UI-0200
# → "task UI-0200 is valid" (subtasks пуст, как требуется)

python doc/tools/arch/__main__.py task close UI-0200
# → "Task UI-0200 closed (phase=completed)." (нет subtasks, close_policy выполнен)
```

## 4.4 Пример subtask task.json

```json
{
  "schema_version": "draft-0.2",
  "task_id": null,
  "task_key": "UI-0009-0001",
  "task_number": "0001",
  "source": {
    "type": "ui",
    "native_id": null,
    "provenance": "created by arch task decompose",
    "revision": null,
    "captured_at": null,
    "attachments": [],
    "comments": [],
    "history": []
  },
  "title": "Создать task-conf типы",
  "kind": "feature",
  "intent": "",
  "scope": {"in": [], "out": [], "allowed_files_modules": []},
  "current_behavior": null,
  "evidence": [],
  "contracts_and_invariants": [],
  "acceptance_criteria": [],
  "implementation_plan": "Создать config.yaml и prompt.md для каждого типа в task-conf/types/",
  "target_release": "unset",
  "project_context_refs": [],
  "constraints": [],
  "assumptions": [],
  "open_questions": [],
  "risk": "low",
  "authority": {"allowed": [], "forbidden": [], "approval_required": []},
  "approvals": [],
  "task_type": "feature",
  "flow": "standard-implementation",
  "complexity": "low",
  "subtasks": [],
  "depends_on": [],
  "phase": "completed",
  "rollback_plan": null,
  "related_docs": [],
  "related_tests": [],
  "research_docs": [],
  "changed_files": {"added": [], "modified": [], "deleted": []},
  "owner": "unset",
  "priority": "unset",
  "stage_history": []
}
```

## 4.5 Пример research_docs

```json
{
  "id": "res-001",
  "title": "Исследование дизайна task-conf",
  "path": "doc/tasks/UI-0009/research/task-conf-design-notes.md",
  "source_type": "internal",
  "source_ref": "doc/tasks/UI-0009/research/task-conf-design-notes.md",
  "summary": "Иерархическая конфигурация типов и потоков задач: config.yaml + prompt.md для каждого типа, внутри flows/ — конфиг и промпт для каждого flujo.",
  "status": "confirmed"
}
```

## 5. Frontmell примеры

### 5.1 Architecture document frontmell

```yaml
---
id: ARCH-contract
type: architecture-view
title: "Целевая модель .doc/architecture: хранение, форматы, обновление и CLI"
summary: "Версия 1.3 — добавлена иерархическая task-conf..."
status: current
domain: system
related: [MAN-software-factory, ARCH-audit, SYS-simple-factory]
implemented: true
---
```

### 5.2 Rule-set frontmell

```yaml
---
id: REG-cli-validation-rules
type: rule-set
title: Правила валидации task.json и ограничения перечислений
summary: "Перечисляет все валидируемые поля task.json..."
status: draft
domain: system
related: [ENT-task-input, REG-cli-command-map, DOM-task-lifecycle]
implemented: true
---
```
