# Stage 1 — Изучить best practices форматов задач из data/, дополнить task.json и правила отражения в архитектуре

## Цель этапа
Изучить best practices из data/ (Контракт задачи для агента, Исследование формата, Тесты, Сущности SDD), определить дополнительные поля task.json, сформулировать правила отражения завершённой задачи в архитектурной документации, обновить примеры task.json, arch.py validate, навыки и тесты.

## Шаги

1. **Изучить data best practices** — прочитаны: Контракт задачи для агента, Исследование формата документации проекта и входящей задачи, Документация тестов, Сущности SDD (entity map, конвейер КСПЗР, ADR).
2. **Определить дополнительные поля task.json** — task_id, source.revision, source.captured_at, kind, scope.in/out, allowed_files_modules, current_behavior, evidence, contracts_and_invariants, risk, authority, execution_state.
3. **Сформулировать правила отражения завершённой задачи в архитектуре** — ADR при архитектурно значимом изменении, related_docs → affected docs, changed_files → accurate paths, stage_history → completion record, обновление ENT/FLOW docs если изменилось поведение, related_tests → verification evidence.
4. **Обновить task.json UI-0001 и UI-0004** — добавить новые поля.
5. **Обновить arch.py task validate** — валидация новых полей.
6. **Обновить SKILL.md** — go-to-task и задокументируй: новые поля task.json, правила отражения в архитектуре.
7. **Добавить unit-тесты** — для новых полей и правил.
8. **Прогнать все тесты**.

## Критерии завершения
- task.json UI-0001 и UI-0004 содержат новые поля
- arch task validate проходит для обоих
- Правила отражения в архитектуре сформулированы (в cli.skill.plan.md или отдельном документе)
- SKILL.md обновлены
- Все тесты проходят

## Связанные IDs
- task: UI-0006
- previous: UI-0001 (scaffold), UI-0004 (task CLI), UI-0005 (traceability fields)
