# Stage 1: Доработка архитектурной документации и CLI

## Цель
Закрыть пробелы в архитектурной документации и CLI:
1. JSON Schema валидация тел документов по типам
2. Команда `arch docs related <id>` для обхода графа связанных документов
3. Поле `implemented` в frontmatter и index.json
4. Тесты для новой функциональности

## Что сделано
- [x] Созданы JSON Schema для тел документов по 15 типам в `doc/architecture/schemas/bodies/`
- [x] Добавлен модуль `doc/tools/arch/body_validation.py` с валидацией тел документов
- [x] Обновлён `doc/tools/arch/store.py` — валидация тел в `validate()`, поле `implemented` в `make_index()`
- [x] Обновлён `doc/tools/arch/cli.py` — команда `docs related <id> [--depth N]`
- [x] Обновлён `doc/tools/arch/__init__.py` — экспорт body_validation
- [x] Обновлён `doc/architecture/schemas/index.schema.json` — поле `implemented`
- [x] Добавлено поле `implemented` ко всем 34 документам `doc/architecture/`
- [x] Добавлены 4 теста в `doc/tests/test_task_identity.py`
- [x] `arch validate` — проходит
- [x] `arch index check` — проходит
- [x] Полный тестовый цикл — 35 passed, 10 subtests passed

## Принятие
- AC-1: JSON Schema для тел документов по типам — ✓
- AC-2: `arch validate` проверяет тела документов — ✓
- AC-3: `arch docs related <id>` — ✓
- AC-4: Поле `implemented` в frontmatter и index.json — ✓
- AC-5: Все документы имеют поле `implemented` — ✓
- AC-6: Тесты покрывают новую функциональность — ✓
- AC-7: `arch validate` и `arch index check` проходят — ✓
