<!-- plan-tier: standard -->
# UI-0033: стандартные статусы, релиз и ветки задачи

## Цель и границы

Добавить исполнительный `status` (включая `paused`) отдельно от `phase`, обязательные `target_release`, `branch`, `release_branch`, валидный скаффолд и миграцию корпуса. Git-операции подготовки и публикации ветки остаются в UI-0027.

## Правила проекта

- `ENT-task-input`: единственный канонический вход; скаффолд валиден сразу.
- `REG-cli-validation-rules`: конфиг-driven перечисления и обязательные поля.
- `doc/AGENTS.md`: запрет ручной карточки и смены типа ради обхода политики.
- taskcontrol.md: `status` и `phase` — разные оси.

## Решения

- `status` — новое поле, значения в `paths.yaml task_statuses`; `phase` не меняется.
- Дефолты релиза и веток — `project.release`; дети наследуют родителя (UI-0027 AC-5).
- Скаффолд `task_type`/`flow` остаются null: тип выбирает агент, иначе `subtask_policy` делает новую карточку невалидной.
- Обязательность включается флагом `release.enforce` после миграции корпуса.

## Артефакты и порядок

1. `schema.py`, `task_ops.py`, `validation.py`, `constants.py` — поля, дефолты, наследование, валидация.
2. `doc/tests/test_task_fields.py` — контракт `init → validate`.
3. Миграция корпуса: `status`, `target_release`, `branch`, `release_branch`.
4. `doc/architecture/` и скиллы — синхронизация контракта и запретов.

## Оценка и декомпозиция

16 ч: 0001 — 6 ч, 0002 — 6 ч, 0003 — 4 ч. Три независимо проверяемых результата.

## Риски и откат

- Риск: обязательные поля ломают корпус — снят миграцией и тестом `init → validate`.
- Риск: расхождение скаффолда и валидации — закрыт тестом.
- Откат: вернуть файлы к снимку и снять `enforce`; данные корпуса не откатывать.

## Приёмка

| CASE | AC | Дано | Действие | Ожидание |
|---|---|---|---|---|
| CASE-1 | AC-1, AC-2 | чистая fixture | task new --title | валидная карточка с status open и полями релиза |
| CASE-2 | AC-3, AC-5 | карточки и дети | task validate; task decompose | exit 0; ребёнок наследует ветку |
| CASE-3 | AC-4, AC-6 | корпус | run.sh --gate | 19 unit + 132 acceptance OK |
| CASE-4 | AC-7, AC-8 | документы и скиллы | index build; docs check-links; validate --brief | exit 0, правила описаны |

## Проверка

```bash
bash doc/tests/run.sh --gate
arch docs check-links
arch validate --brief
```
