# Исследование: дизайн task-conf (типы и флоу задач)

## Гипотеза

Иерархическая конфигурация типов и потоков задач (`doc/config/task-conf/types/<type>/` с `config.yaml` и `prompt.md`, внутри `flows/<flow>/`) позволяет строго регламентировать workflow задачи на уровне CLI: какие flujo доступны для типа, нужны ли подзадачи, может ли задача закрыться при незакрытых подзадачах, какие поля обязательны.

## Источники

- `doc/config/task-conf/types/jira-incoming/flows/jira-process/prompt.md` — стартовый промпт для Jira-задач
- `doc/config/task-conf/types/feature/flows/standard-implementation/prompt.md` — стандартная реализация фичи
- `/home/user/data/machinedocs-encyclopedia/Практики/Сквозной цикл разработки.md` — Intent → Plan → Build → Verify → Secure → Deploy → Observe → Improve
- `/home/user/data/machinedocs-encyclopedia/Практики/Контракт задачи для агента.md` — issue-first подход

## Что подтверждено

- 9 типов задач зарегистрированы в task-conf
- 11 flujo с собственными конфигами и промптами
- CLI команды `task types`, `task flows --type`, `task type-prompt`, `task flow-prompt` работают
- `arch task validate` проверяет совместимость flow и task_type

## Открытые вопросы (гипотезы)

- Нужно ли добавить поле `research_docs` в task.json для связи с research/ файлами? — Да, добавлено.
- Следует ли валидировать, что research-файл реально существует на диске? — Пока нет, только путь и шаблон.
- Может ли один research-файл быть связан с несколькими задачами? — Пока нет, каждый research_docs принадлежит одной задаче.

## Статус

Всё вышеперечисленное реализовано и проходит валидацию CLI.
