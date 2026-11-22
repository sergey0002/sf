# Stage 1 — Развернуть CLI-среду завода и корневой README

## Цель этапа
Подготовить рабочую среду agentic software factory в песочнице: CLI доступен и валиден, тесты зеленые, корневой README содержит инструкцию по `data/`.

## Шаги

1. **CLI исполняемым.** `chmod +x doc/tools/arch.py`; проверить вызов `./doc/tools/arch.py validate` и `python3 doc/tools/arch.py validate`.
2. **Валидация и индекс.** Запустить `arch.py validate`, `arch.py index check`, `arch.py index build`. Зафиксировать вывод.
3. **Тесты.** Запустить `doc/tests/run.sh` и `python3 -m unittest discover` в `doc/tools/tests/`. Ожидается 13/13.
4. **Корневой README.** Создать `/home/user/README.md`:
   - структура песочника (doc/ = завод, корень = сервисные правила, data/ = внешний справочник);
   - границы: что править, а что только читать;
   - CLI quickstart (команды arch.py);
   - порядок создания задачи (task.json, 4 цифры, префиксы);
   - раздел «Как работать с data/»: только чтение, навигация через MOC/Оглавления, не править как проектные файлы, ссылки на корневой манифест.
5. **Доработка при необходимости.** Если валидация или тесты падают — исправить файлы завода, повторить шаги 2–3.
6. **Фиксация.** Обновить `stage1/verification.json` фактическими результатами.

## Критерии завершения этапа
- `arch.py validate` → 0 ошибок
- `arch.py index check` → current
- `doc/tests/run.sh` → 13/13 pass
- `/home/user/README.md` существует и содержит раздел по `data/`

## Связанные IDs
- task: UI-0002
- предыдущая задача: UI-0001 (scaffold завода)
- архитектура: ADR-0001, SYS-simple-factory, GLO-system
