# Stage 1 — Дополнить task.json и реализовать механизм subtasks/

## Цель этапа
Добавить в task.json поля task_type, subtasks, depends_on, phase, rollback_plan. Реализовать CLI-команды для работы с subtasks/. Обновить навыки и тесты.

## Шаги

1. **Обновить task.json UI-0001 и UI-0004** — добавить task_type, subtasks, depends_on, phase, rollback_plan.
2. **Обновить arch.py task validate** — валидация task_type (enum), phase (enum), subtasks (массив объектов), depends_on (массив строк), rollback_plan (строка).
3. **Реализовать arch task subtask init** — создать subtasks/<id>/ с task.json + stage1/, parent_task_key в task.json сабтаска.
4. **Реализовать arch task subtask validate** — валидация task.json сабтаска.
5. **Реализовать arch task subtask status** — статус сабтаска.
6. **Обновить SKILL.md** — go-to-task и задокументируй: новые поля task.json, правила работы с сабтасками.
7. **Добавить unit-тесты** — для новых полей и subtask команд.
8. **Прогнать все тесты**.

## Критерии завершения
- task.json UI-0001 и UI-0004 содержат новые поля
- arch task subtask init/validate/status работают
- arch task validate проверяет новые поля
- SKILL.md обновлены
- Все тесты проходят

## Связанные IDs
- task: UI-0007
- previous: UI-0001, UI-0004, UI-0005, UI-0006
