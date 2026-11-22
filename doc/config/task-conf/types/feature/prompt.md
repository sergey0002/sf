# Стартовый промпт типа feature

Исполняется при начале работы над задачей типа `feature`.

## Контекст

Задача — новая функциональность или расширение существующей. Нужно пройти через выбранный flujo, создать подзадачи (обязательно, так как `subtask_policy: required`), реализовать в рамках `allowed_files_modules` и закрыть только после выполнения всех подзадач и approval.

## Что сделать

1. Прочитай `task.json` и этот `prompt.md`.
2. Выбери flujo из `allowed_flows`: `standard-implementation` или `research-first`.
3. Прочитай `prompt.md` выбранного flujo.
4. Запусти `arch task validate <task_key>`.
5. Запусти `arch docs paths --check`.
6. Следуй шагам flujo.

## Закрытие

Через `arch task close <task_key>` только если все подзадачи закрыты и approval получен.
