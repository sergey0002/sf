# Стартовый промпт типа bugfix

Исполняется при начале работы над задачей типа `bugfix`.

## Контекст

Задача — исправление дефекта. Нужно воспроизвести ошибку, внести фикс, добавить регресс-тест и проверить.

## Что сделать

1. Прочитай task.json и этот prompt.md.
2. Выбери flujo: `standard-implementation` или `minimal-scaffold`.
3. Прочитай prompt.md выбранного flujo.
4. Запусти `arch task validate <task_key>`.
5. Запусти `arch docs paths --check`.
6. Следуй шагам flujo.

## Закрытие

Через `arch task close <task_key>` только если все подзадачи закрыты и approval получен.
