# Стартовый промпт типа docs

Исполняется при начале работы над задачей типа `docs`.

## Контекст

Задача меняет только архитектурную документацию, скиллы или конфиги путей. Требует структурной валидации путей и frontmatter.

## Что сделать

1. Прочитай task.json и этот prompt.md.
2. Выбери flujo `docs-only`.
3. Прочитай prompt.md flujo.
4. Запусти `arch task validate <task_key>`.
5. Запусти `arch docs paths --check`.
6. Внеси минимальный diff в затронутые .md файлы под doc/architecture/.
7. Запусти `arch validate` и `arch docs paths --check` повторно.
8. Закрой через `arch task close <task_key>`.
