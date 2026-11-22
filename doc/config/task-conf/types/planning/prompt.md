# Стартовый промпт типа planning

Исполняется при начале работы над задачей типа `planning`.

## Контекст

Задача — составление технического плана, спецификации, архитектурных решений. Реализация кода не производится в рамках этой задачи.

## Что сделать

1. Прочитай task.json и этот prompt.md.
2. Выбери flujo: `research-first` или `standard-implementation`.
3. Прочитай prompt.md выбранного flujo.
4. Запусти `arch task validate <task_key>`.
5. Составь план со спецификацией и Constitution Check.
6. Получи approval на план.
7. Закрой через `arch task close <task_key>`.
