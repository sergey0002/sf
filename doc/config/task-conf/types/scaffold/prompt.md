# Стартовый промпт типа scaffold

Исполняется при начале работы над задачей типа `scaffold`.

## Контекст

Задача — создание каркаса: директорий, task.json, этапов. Не содержит семантического содержимого задачи.

## Что сделать

1. Прочитай task.json и этот prompt.md.
2. Выбери flujo `minimal-scaffold`.
3. Прочитай prompt.md flujo.
4. Запусти `arch task init <task_key>`.
5. Создай stage1/ с plan.md и verification.json (заглушки).
6. Закрой через `arch task close <task_key>`.
