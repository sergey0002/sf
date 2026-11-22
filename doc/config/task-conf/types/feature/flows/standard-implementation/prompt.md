# Стартовый промпт flujo standard-implementation (тип feature)

## Шаги

1. **Уточнение намерения** — прочитай task.json, уточни блокирующие вопросы у пользователя.
2. **Планирование** — создай stage1/plan.md с файлами, подзадачами и критериями приёмки.
3. **Реализация** — изменения только в рамках `allowed_files_modules` из task.json.
4. **Проверка** — `arch validate`, `arch docs paths --check`, тесты, stage1/verification.json.
5. **Закрытие** — `arch task close <task_key>` только если все подзадачи закрыты.
