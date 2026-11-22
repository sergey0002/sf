# Stage 1 — Расширить формат task.json для полной traceability

## Цель этапа
Оценить текущий task.json, определить недостающие поля, обновить примеры task.json, добавить валидацию в arch.py task validate, обновить навыки, добавить тесты.

## Шаги

1. **Анализ текущего task.json** — прочитать UI-0001/task.json и UI-0004/task.json, сопоставить с требованиями манифеста (source.comments/attachments/history, acceptance refs, execution snapshot) и data/machinedocs-encyclopedia (Контракт задачи для агента).
2. **Определить недостающие поля** — source.comments, source.attachments, source.history, related_docs (ENTITY/FLOW/ADR IDs), related_tests (test IDs, suite, location), changed_files (added/modified/deleted), owner, priority, stage_history (стадии со статусами, результатами, evidence refs).
3. **Обновить task.json UI-0001 и UI-0004** — добавить новые поля с примерными значениями (где применимо), оставить существующие поля нетронутыми.
4. **Обновить arch.py task validate** — добавить проверку новых полей: related_docs (существующие ID в индекте), related_tests (формат), changed_files (существующие пути), stage_history (структура), owner, priority.
5. **Обновить SKILL.md** — go-to-task и задокументируй: добавить разделы «task.json fields» со ссылками на related_docs, related_tests, changed_files, stage_history.
6. **Добавить unit-тесты** в test_task_identity.py для расширенной валидации.
7. **Прогнать все тесты** — doc/tests/run.sh + unittest discover + arch.py validate/index check.

## Критерии завершения
- task.json UI-0001 и UI-0004 содержат новые поля traceability
- arch task validate проходит для обоих
- SKILL.md содержат ссылки на новые поля
- Все тесты проходят

## Связанные IDs
- task: UI-0005
- предыдущие задачи: UI-0001 (scaffold), UI-0004 (task CLI)
- навыки: go-to-task, задокументируй, create-task
