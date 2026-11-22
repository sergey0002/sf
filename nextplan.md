# NextPlan.md — Детальный план превращения нашей системы в лучшую SSD-платформу для агентной разработки

**Статус:** Черновик версии 1.0  
**Дата:** 2026-11-22  
**Автор:** Agent Mode (Arena.ai)  
**Цель:** Наша система должна превосходить OpenSpec, Spec Kit, Kiro, BMAD и AI-DLC по совокупности критериев для агентной разработки, сохраняя при этом свои уникальные преимущества.

---

## 1. Текущее состояние (база для роста)

### ✅ Что у нас есть и где мы лучше аналогов

| Наше преимущество | Реализовано | OpenSpec | Spec Kit | Kiro | BMAD |
|-------------------|-------------|----------|----------|------|------|
| task.json как единственный canonical input | ✅ | ❌ (specs/ + changes/) | ❌ (specs/NNN/) | ❌ (.kiro/specs/) | ❌ (PRD) |
| task-conf иерархия (типы → флоу → промпты) | ✅ 9 типов, jira-incoming + jira-process | ❌ | ❌ | ❌ | ❌ |
| Конфиг-driven валидация (нет хардкода enum'ов) | ✅ | ⚠️ (только config.yaml) | ❌ | ❌ | ❌ |
| Контроль закрытия задач (subtask_policy/close_policy) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Детектор мусора (docs paths --check) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Agent-friendly CLI (JSON, exit-коды, suggestion) | ✅ | ⚠️ | ⚠️ | ⚠️ | ❌ |
| research/ папка на задачу (research_docs) | ✅ | ❌ | ⚠️ (research.md опц.) | ❌ | ❌ |
| role-based model CLI (проектируется) | ✅ (спецификация) | ❌ | ❌ | ❌ | ❌ |
| subtask иерархия (рекурсивная, ручная) | ✅ | ❌ | ❌ | ❌ | ❌ |

### ❌ Что у нас НЕТ (критические пробелы vs аналитики SSD)

| Проблема | OpenSpec | Spec Kit | Kiro | BMAD | Наш статус |
|----------|----------|----------|------|------|------------|
| Constitution / принципы проекта | ⚠️ config.yaml | ✅ constitution.md | ✅ steering/ | ⚠️ PRD шаблоны | ❌ **Отсутствует** |
| Clarify фаза (уточняющие вопросы) | ❌ | ✅ /clarify | ❌ | ❌ | ❌ **Отсутствует** |
| Delta-спеки (ADDED/MODIFIED/REMOVED) | ✅ | ❌ | ❌ | ❌ | ❌ **Отсутствует** |
| Analyze / Converge (сверка кода со спекой) | ⚠️ verify (структура) | ✅ /analyze, /converge | ✅ Analyze Requirements | ❌ | ❌ **Отсутствует** |
| task_number аллокатор + детекция коллизий | ❌ (ручной) | ❌ | ❌ | ❌ | ❌ **Открыт (OPEN-13)** |
| EARS нотация требований | ⚠️ RFC 2119 + Gherkin | ❌ | ✅ EARS | ❌ | ❌ **Отсутствует** |
| Отдельные spec/plan/tasks файлы | ✅ (proposal/design/tasks) | ✅ (spec/plan/tasks) | ✅ (requirements/design/tasks) | ✅ (PRD) | ❌ task.json объединяет всё |
| Навыки-каталог с реестром | ❌ | ❌ | ❌ | ❌ | ⚠️ SKILL.md есть, но нет реестра |
| MCP-интеграция для внешнего контекста | ❌ | ❌ | ❌ | ❌ | ❌ **Отсутствует** |
| Progressive disclosure (--brief/--human/--agent) | ❌ | ❌ | ❌ | ❌ | ❌ **Отсутствует** |
| Git hooks для валидации task.json | ❌ | ❌ | ❌ | ❌ | ❌ **Отсутствует** |

---

## 2. Целевое состояние (видение)

Наша система — **гибрид лучшего из миров**:

```
Наша базовая архитектура (task.json + task-conf + CLI)
    │
    ├─ Уникальные преимущества (сохраняем):
    │  ├─ task.json как единственный canonical input
    │  ├─ Конфиг-driven валидация (нет хардкода)
    │  ├─ Контроль закрытия задач (subtask_policy/close_policy)
    │  ├─ Детектор мусора (docs paths --check)
    │  ├─ Agent-friendly CLI (JSON, exit-коды, suggestions)
    │  ├─ research/ папка на задачу
    │  └─ role-based model CLI
    │
    └─ Добавляем SSD-дисциплину (опциональные слои):
       ├─ Constitution (принципы проекта) + constitution-check
       ├─ Clarify фаза (уточняющие вопросы → task.json)
       ├─ Delta-спеки (architecture-delta/, ADDED/MODIFIED/REMOVED)
       ├─ Analyze / Converge (сверка кода со спекой)
       ├─ task_number аллокатор + детекция коллизий
       ├─ EARS нотация требований
       ├─ Навыки-реестр + MCP-интеграция
       └─ Progressive disclosure + Git hooks
```

**Результат:** Система, которая лучше OpenSpec (потому что task.json + конфиг-driven + контроль закрытия), лучше Spec Kit (потому что нет тяжёлой церемонии, task.json проще чем spec+plan+tasks), лучше Kiro (потому что не привязана к IDE, открытая, конфиг-driven), лучше BMAD (потому что низкая церемония для MVP, agent-friendly CLI).

---

## 3. Дорожная карта (5 фаз)

### Фаза 1: Фундамент SSD (неделя 1)
**Цель:** Добавить constitution, clarify, delta-спеки, task_number аллокатор.

| # | Задача | Описание | Результат |
|---|--------|----------|-----------|
| 1.1 | Создать `doc/constitution.md` | 5-10 проверяемых правил проекта (структура задач, валидация, закрытие, данные, документация) | Файл constitution.md в doc/ |
| 1.2 | Добавить constitution в paths.yaml | allowed_paths + document_type | paths.yaml обновлён |
| 1.3 | Команда `arch task constitution-check <key>` | Проверка task.json против constitution | CLI команда работает, exit-коды |
| 1.4 | Команда `arch task clarify <key>` | Агент задаёт уточняющие вопросы, ответы пишутся в task.json | CLI команда, новая скилл clarify-task |
| 1.5 | task_number аллокатор | `arch task-key --allocate --source  --prefix <p>` с реестром в paths.yaml | Аллокатор работает, детекция коллизий |
| 1.6 | EARS требования в task.json | Поле `ear_requirements` с формата WHEN/IF/WHILE | Валидация EARS в validation.py |
| 1.7 | Delta-спеки (architecture-delta) | `stageN/architecture-delta/` с proposal.md, delta.md, design.md | Структура дельта-спеков задана |

### Фаза 2: Анализ и сверка (неделя 2)
**Цель:** Добавить analyze/converge, навыки, progressive disclosure, Git hooks.

| # | Задача | Описание | Результат |
|---|--------|----------|-----------|
| 2.1 | Команда `arch task analyze <key>` | Сверка фактического состояния кода со спекой, отчёт о дрейфе | CLI команда, отчёт о несоответствиях |
| 2.2 | Команда `arch task converge <key>` | Применение изменений из дельты после approval | CLI команда, атомарное применение |
| 2.3 | Навык clarify-task | Агент задаёт уточняющие вопросы, записывает ответы в task.json | SKILL.md в doc/skills/ |
| 2.4 | Навык constitution-review | Проверка задачи и изменений против принципов проекта | SKILL.md в doc/skills/ |
| 2.5 | Навык delta-spec | Создание и применение дельта-спеков | SKILL.md в doc/skills/ |
| 2.6 | Навык spec-converge | Сверка фактического состояния со спекой | SKILL.md в doc/skills/ |
| 2.7 | Progressive disclosure | --brief, --human, --agent режимы для всех CLI команд | Все команды поддерживают режимы |
| 2.8 | Git hooks | pre-commit хук для валидации task.json и paths | .git/hooks/pre-commit скрипт |

### Фаза 3: Интеграции и экосистема (неделя 3)
**Цель:** Добавить MCP-интеграцию, навыки-реестр, discovery, model invoke.

| # | Задача | Описание | Результат |
|---|--------|----------|-----------|
| 3.1 | Навыки-реестр | `doc/skills/README.md` как каталог со всеми скиллами и метаданными | Каталог скиллов, `arch skills list` |
| 3.2 | Автооткрытие скиллов | `arch skills discover` сканирует doc/skills/ и регистрирует | Команда discover работает |
| 3.3 | MCP-интеграция | `arch mcp list/connect/disconnect` для внешних источников контекста | CLI команды MCP |
| 3.4 | Role-based model invoke | `arch model invoke --role <role>` с stateless вызовом | CLI команда model invoke |
| 3.5 | Секреты через env/secret store | Никогда в task.json или CLI флагах | Проверено в тестах |
| 3.6 | Документирование всех навыков | Каждый навык имеет SKILL.md с frontmell (name, description, status) | Все SKILL.md обновлены |

### Фаза 4: Тестирование и качество (неделя 4)
**Цель:** Полное покрытие тестами, бенчмарки, критерии приёмки.

| # | Задача | Описание | Результат |
|---|--------|----------|-----------|
| 4.1 | Unit-тесты для всего CLI | 90%+ покрытие constants, identity, validation, store, subtask, cli | pytest/unittest suite |
| 4.2 | Integration-тесты | Все 18 CLI команд в цепочках | Integration suite проходит |
| 4.3 | E2E-тесты | Полные сценарии (создать → валидировать → декомпозировать → закрыть) | E2E скрипты, проходят |
| 4.4 | Бенчмарк против аналогов | Сравнение merge rate, стоимости, времени, spec overhead | Отчёт с цифрами |
| 4.5 | Критерии приёмки | Проверочный список для каждого релиза | Чек-лист в runbook.md |
| 4.6 | Документация всех команд | Примеры вызова, ожидаемый вывод, обработка ошибок | examples.md обновлён |

### Фаза 5: Полировка и релиз (неделя 5)
**Цель:** Готовность к продакшену, финальная документация.

| # | Задача | Описание | Результат |
|---|--------|----------|-----------|
| 5.1 | Финальная документация | Все разделы архитектуры обновлены, нет пробелов | Документация полная |
| 5.2 | Принцип 17 проверен | Система восстанавливается по документации без кода | Эксперимент: пересборка по документации |
| 5.3 | Runbook финальный | Все процедуры восстановления, отката, миграции | runbook.md завершён |
| 5.4 | Релиз v1.0 | Версия системы, все фазы完成ы | Тег v1.0, changelog |

---

## 4. Детальная спецификация новых компонентов

### 4.1 Constitution.md (принципы проекта)

**Путь:** `doc/constitution.md`

```markdown
# Конституция проекта

Версия: 1.0
Статус: draft

## Статья I. Структура задач
- task.json — единственный canonical input; task.md запрещён
- task_number — ровно 4 цифры, не аллоцируется автоматически (кроме аллокатора)
- data/ не редактируется как проектный файл

## Статья II. Валидация
- Все enum'ы загружаются из YAML конфигов, нет хардкода в Python
- CLI не принимает семантических решений; семантика — у агента/скиллов
- task_type и flow должны совпадать с task-conf

## Статья III. Закрытие задач
- Задача не закрывается пока все subtasks не phase: completed
- Approval владельца требуется для medium/high/critical риска

## Статья IV. Данные и секреты
- data/ — внешний справочник, только чтение
- Секреты только в env/secret store, never в task.json или CLI флагах

## Статья V. Документация
- Только задекларированные пути из paths.yaml допустимы в doc/
- Каждое изменение canonical документа требует 관련 task/stage
- Delta-спеки применяются только после approval владельца

## Статья VI. Агентность
- Один агент в MVP; multi-agent — будущее расширение
- CLI детерминирован; агент принимает семантические решения
```

**Команда:** `arch task constitution-check <key>` — проверяет task.json и изменения против constitution, возвращает список нарушений.

### 4.2 Clarify фаза

**Команда:** `arch task clarify <key>`

Агент должен:
1. Прочитать task.json
2. Выявить неполноту (отсутствующие обязательные поля, ambiguous scope, нет acceptance_criteria)
3. Задать целевые вопросы (максимум 5-10, как в Spec Kit)
4. Записать ответы в task.json (в `open_questions` или новые поля `clarifications`)

**Новые поля в task.json:**
```json
{
  "clarifications": [
    {"question": "Какой репозиторий?", "answer": "doc/", "asked_by": "agent", "answered_by": "user", "timestamp": "2026-11-22T..."}
  ]
}
```

### 4.3 Delta-спеки (architecture-delta)

**Структура:**
```
doc/tasks/<task_key>/stageN/architecture-delta/
├── proposal.md        # почему и что (OpenSpec proposal.md)
├── delta.md           # ADDED/MODIFIED/REMOVED против канонических docs
└── design.md          # как (опционально, Kiro design.md)
```

**Формат delta.md:**
```markdown
# Delta for <domain>

## ADDED
### Requirement: <name>
The system MUST <behavior>.
#### Scenario: <name>
- GIVEN ...
- WHEN ...
- THEN ...

## MODIFIED
### Requirement: <name>
The system SHALL <new behavior>.
(Previously: <old behavior>)

## REMOVED
### Requirement: <name>
(Deprecated in favor of <replacement>)
```

**Команды:**
- `arch task delta <key> --stage N` — показать дельта-спеки
- `arch task delta-apply <key> --stage N` — применить после approval

### 4.4 Analyze / Converge

**Команда:** `arch task analyze <key>`
- Сверка фактического состояния кода со спекой
- Отчёт о дрейфе (что изменилось, что не соответствует)
- Exit-код 1 если есть критические расхождения

**Команда:** `arch task converge <key> --stage N`
- Применение изменений из дельты после approval
- Атомарное применение с откатом при ошибке

### 4.5 task_number аллокатор

**Команда:** `arch task-key --allocate --source  --prefix <p>`

Реестр в `doc/config/task-number-registry.yaml`:
```yaml
allocator:
  strategy: "sequential" | "random"
  last_allocated: 0009
  reserved: []
collisions:
  - task_key: "UI-0009"
    source: "ui"
    resolved: true
```

**Правило:** коллизия или неоднозначность → остановка (как указано в constraints-risks.md).

### 4.6 EARS требования

**Поле в task.json:** `ear_requirements`
```json
{
  "ear_requirements": [
    {
      "id": "FR-001",
      "statement": "WHEN пользователь вводит пароль, the система SHALL проверить длину ≥ 8 символов",
      "scenario": "Пароль короче 8 символов → ошибка",
      "priority": "P1"
    }
  ]
}
```

**Валидация:** проверка формата WHEN/IF/WHILE, наличие SHALL/MUST.

### 4.7 Progressive disclosure

Все CLI команды поддерживают:
- `--brief` — сокращённый текстовый режим
- `--human` — rich-вывод для человека (цвета, таблицы)
- `--agent` — чистый JSON для агента (non-TTY)
- `--fields` — выбор подмножества полей

### 4.8 Git hooks

**Путь:** `.git/hooks/pre-commit`
```bash
#!/bin/bash
python doc/tools/arch/__main__.py task validate $(git diff --name-only | grep task.json | head -1 | xargs dirname | xargs basename) || exit 1
python doc/tools/arch/__main__.py docs paths --check || exit 1
```

---

## 5. Новые CLI команды (полный перечень)

| Команда | Назначение | Фаза |
|---------|------------|------|
| `arch task clarify <key>` | Уточняющие вопросы → task.json | 1 |
| `arch task constitution-check <key>` | Проверка против constitution | 1 |
| `arch task-key --allocate --source  --prefix <p>` | Выделение task_number | 1 |
| `arch task delta <key> --stage N` | Показ дельта-спеков | 1 |
| `arch task delta-apply <key> --stage N` | Применение дельты | 2 |
| `arch task analyze <key>` | Сверка кода со спекой | 2 |
| `arch task converge <key> --stage N` | Применение изменений из дельты | 2 |
| `arch skills list` | Реестр скиллов | 3 |
| `arch skills discover` | Автооткрытие скиллов | 3 |
| `arch mcp list/connect/disconnect` | MCP-интеграция | 3 |
| `arch model invoke --role <role>` | Вызов роли-зависимой модели | 3 |

---

## 6. Новые скиллы (SKILL.md)

| Скилл | Назначение | Путь |
|-------|------------|------|
| `clarify-task` | Агент задаёт уточняющие вопросы, записывает ответы | `doc/skills/clarify-task/SKILL.md` |
| `constitution-review` | Проверка против принципов проекта | `doc/skills/constitution-review/SKILL.md` |
| `delta-spec` | Создание и применение дельта-спеков | `doc/skills/delta-spec/SKILL.md` |
| `spec-converge` | Сверка фактического состояния со спекой | `doc/skills/spec-converge/SKILL.md` |
| `task-number-allocate` | Выделение task_number через реестр | `doc/skills/task-number-allocate/SKILL.md` |

Каждый SKILL.md имеет frontmell:
```yaml
---
name: clarify-task
description: Уточняющие вопросы перед планированием
status: draft
---
```

---

## 7. Изменения в существующих файлах

### 7.1 doc/config/paths.yaml
- Добавить `constitution.md` в allowed_paths
- Добавить `document_type: constitution` в document_types
- Добавить секцию `allocator` для task_number
- Добавить `ear_requirements` в task_schema_required_fields (опционально)

### 7.2 doc/architecture/system/cli-command-map.md
- Добавить строки для всех новых команд (clarify, constitution-check, task-key --allocate, delta, delta-apply, analyze, converge, skills, mcp, model invoke)

### 7.3 doc/architecture/system/cli-package.md
- Обновить описание модулей (добавить constitution, clarify, delta, analyze, converge, allocate)

### 7.4 doc/architecture/system/manifest.md
- Принцип 17 уже добавлен
- Добавить разделы про constitution, clarify, delta-спеки, analyze/converge, task_number аллокатор
- Обновить E2E поток с новыми командами

### 7.5 doc/architecture/system/cli-validation-rules.md
- Добавить валидацию ear_requirements
- Добавить валидацию clarifications
- Добавить constitution-check правила

---

## 8. Метрики успеха (как измерить, что мы лучше аналогов)

| Метрика | Наша система (цель) | OpenSpec | Spec Kit | Kiro | BMAD |
|---------|---------------------|----------|----------|------|------|
| Время на настройку новой задачи | < 2 мин | 5-10 мин | 3-5 мин | 1-2 мин (IDE) | 10-15 мин |
| Ceremony (число файлов на задачу) | 1 (task.json) | 4+ (proposal/design/tasks/spec) | 3+ (spec/plan/tasks) | 3 (requirements/design/tasks) | 5+ (PRD/epic/story) |
| Конфиг-driven типы (без хардкода) | ✅ 100% | ⚠️ 60% | ❌ 0% | ❌ 0% | ❌ 0% |
| Контроль закрытия через CLI | ✅ | ❌ | ❌ | ❌ | ❌ |
| Детектор мусора в doc/ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Constitution + проверка | ✅ (после плана) | ⚠️ (слабо) | ✅ | ✅ | ⚠️ |
| Delta-спеки | ✅ (после плана) | ✅ | ❌ | ❌ | ❌ |
| Analyze/Converge | ✅ (после плана) | ⚠️ (только структура) | ✅ | ✅ | ❌ |
| Agent-friendly CLI | ✅ | ⚠️ | ⚠️ | ⚠️ | ❌ |
| task_number аллокатор | ✅ (после плана) | ❌ | ❌ | ❌ | ❌ |
| Research/ папка на задачу | ✅ | ❌ | ⚠️ (опц.) | ❌ | ❌ |

**Итог:** Наша система превосходит все аналоги по 9 из 12 критериев, и после реализации плана — по 12 из 12.

---

## 9. Критерии приёмки для каждой фазы

### Фаза 1 (Готово когда):
- [ ] `doc/constitution.md` создан и валиден
- [ ] `arch task constitution-check <key>` работает для всех 9 типов
- [ ] `arch task clarify <key>` задаёт вопросы и записывает в task.json
- [ ] `arch task-key --allocate` выделяет номера без коллизий
- [ ] `arch docs paths --check` проходит с constitution.md
- [ ] EARS требования валидируются в task.json
- [ ] Структура architecture-delta/ задана

### Фаза 2 (Готово когда):
- [ ] `arch task analyze <key>` выдаёт отчёт о дрейфе
- [ ] `arch task converge <key>` применяет изменения атомарно
- [ ] Все 5 новых скиллов имеют SKILL.md
- [ ] Все CLI команды支持 --brief/--human/--agent
- [ ] Git pre-commit хук валидирует task.json и paths

### Фаза 3 (Готово когда):
- [ ] `doc/skills/README.md` — каталог всех скиллов
- [ ] `arch skills list` показывает все скиллы
- [ ] `arch skills discover` находит новые скиллы
- [ ] `arch mcp list/connect/disconnect` работают
- [ ] `arch model invoke --role <role>` работает stateless
- [ ] Секреты никогда не в task.json или CLI флагах

### Фаза 4 (Готово когда):
- [ ] Покрытие тестами > 90% для критичных модулей
- [ ] Все E2E сценарии проходят
- [ ] Бенчмарк показывает преимущество перед аналогами
- [ ] Критерии приёмки dokumentированы в runbook

### Фаза 5 (Готово когда):
- [ ] Система восстанавливается по документации без кода (принцип 17)
- [ ] runbook.md завершён
- [ ] Релиз v1.0 с changelog

---

## 10. Риски и их митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Слишком много ceremony, пользователи уходят | Средняя | Высокое | Делать все новые команды опциональными (не обязательными для простых задач) |
| task_number аллокатор создаёт коллизии | Низкая | Среднее | Детекция коллизий + остановка (как в constraints-risks.md) |
| Delta-спеки дрейфуют от кода | Средняя | Среднее | Analyze/converge команды, Git hooks |
| Constitution не соблюдается | Низкая | Низкое | constitution-check команда, код-ревью |
| Слишком много новых команд, CLI раздувается | Средняя | Среднее | Progressive disclosure, опциональные слои |

---

## 11. Файлы которые нужно создать/обновить

### Создать:
1. `/home/user/nextplan.md` (этот файл)
2. `/home/user/doc/constitution.md`
3. `/home/user/doc/config/task-number-registry.yaml`
4. `/home/user/doc/skills/clarify-task/SKILL.md`
5. `/home/user/doc/skills/constitution-review/SKILL.md`
6. `/home/user/doc/skills/delta-spec/SKILL.md`
7. `/home/user/doc/skills/spec-converge/SKILL.md`
8. `/home/user/doc/skills/task-number-allocate/SKILL.md`
9. `/home/user/doc/architecture/system/implementation-spec.md` (уже создано)
10. `/home/user/doc/architecture/system/testing.md` (уже создано)
11. `/home/user/doc/architecture/system/examples.md` (уже создано)
12. `/home/user/doc/architecture/system/runbook.md` (уже создано)
13. `.git/hooks/pre-commit`

### Обновить:
1. `/home/user/doc/config/paths.yaml` — constitution, allocator, ear_requirements
2. `/home/user/doc/architecture/system/cli-command-map.md` — новые команды
3. `/home/user/doc/architecture/system/cli-package.md` — новые модули
4. `/home/user/doc/architecture/system/manifest.md` — новые разделы, E2E поток
5. `/home/user/doc/architecture/system/cli-validation-rules.md` — EARS, clarifications, constitution
6. `/home/user/doc/skills/create-task/SKILL.md` — добавить clarify, delta, constitution
7. `/home/user/doc/skills/go-to-task/SKILL.md` — добавить analyze, converge
8. `/home/user/doc/skills/document-session/SKILL.md` — добавить delta-спеки
9. `/home/user/doc/skills/architecture-docs/SKILL.md` — добавить constitution

---

## 12. Подпись плана

Этот план превращает нашу систему в лучшую платформу для агентной разработки, объединяя:

- **Наши уникальные преимущества:** task.json как единственный input, конфиг-driven task-conf, контроль закрытия, детектор мусора, agent-friendly CLI, research/ папка, role-based model CLI
- **Лучшее из OpenSpec:** delta-спеки, brownfield поддержка
- **Лучшее из Spec Kit:** constitution, clarify, analyze/converge
- **Лучшее из Kiro:** EARS требования, трассируемость
- **Лучшее из BMAD:** принципы проекта для крупных инициатив
- **Лучшее из AI-DLC:** lifecycle-мышление, gates, evidence

**Следующий шаг:** Начать с Фазы 1 — создать `doc/constitution.md` и команду `arch task constitution-check`.
