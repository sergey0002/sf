# Stage 1 — Реализовать CLI-команды task init/validate/workspace/status

## Цель этапа
Добавить в `doc/tools/arch.py` группу команд `task` для детерминированной работы с задачами завода.

## Шаги

1. **Изучить структуру arch.py** — парсер argparse, существующие команды (list/show/index/validate/task-key), ArchitectureStore класс.
2. **Добавить парсер для группы `task`** — подкоманды: init, validate, workspace, status.
3. **Реализовать `task init <task_key>`**:
   - Валидация формата task_key (соответствие источникам/префиксам)
   - Проверка коллизии (каталог doc/tasks/<task_key> уже существует)
   - Создание каталога doc/tasks/<task_key>/
   - Создание scaffold task.json с минимальными полями (task_key, task_number, source, title, intent, scope, exclusions, acceptance_criteria, target_release, project_context_refs, constraints, assumptions, open_questions, approvals) — семантическое содержимое заполняется агентом
   - Создание каталога doc/tasks/<task_key>/stage1/
4. **Реализовать `task validate <task_key>`**:
   - Чтение task.json из doc/tasks/<task_key>/task.json
   - Валидация JSON структуры
   - Валидация task_number (ровно 4 десятичные цифры)
   - Проверка task_key совпадения с именем каталога и содержимым task.json
   - Проверка источника и префикса (Jira bare, UI-, иные — явный префикс)
   - Проверка отсутствия task.md
5. **Реализовать `task workspace <task_key>`**:
   - Проверка существования и валидности task.json
   - Подготовка workspace: базовый коммит, имя ветки по правилам task_key
6. **Реализовать `task status <task_key>`**:
   - Показать состояние задачи, стадию, каталоги stageN/, файлы верификации
7. **Добавить unit-тесты** в doc/tools/tests/test_arch.py для новых команд.
8. **Прогнать все тесты** — doc/tests/run.sh (13/13) + unittest discover (5+ Новые/5).

## Критерии завершения
- arch task init создаёт каталог + task.json + stage1/
- arch task validate проходит для UI-0001
- arch task init на существующий ключ → ошибка коллизии
- Некорректные ключи → ошибка
- 13/13 тестов проходят

## Связанные IDs
- task: UI-0004
- архитектура: REG-task-number-registry, GLO-system, ENT-task-input
- навыки: create-task, go-to-task
