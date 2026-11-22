# Stage 1 plan — починка тестов и CLI-контракта

**Task:** `UI-0010`  
**Input:** `../task.json`  
**Basis:** `doc/architecture/system/implementation-spec.md`, `cli-command-map.md`, `cli-validation-rules.md`, `testing.md`.  
**Outcome:** factory-контур снова зелёный; поведение CLI соответствует заявленному контракту.

## Actions

- [x] Воспроизвести падения: `python3 -m unittest discover -s doc/tests -p 'test_*.py'` → 35 тестов, 17 failures + 3 errors.
- [x] Исправить `doc/tests/run.sh`: заменить удалённый `doc/tools/arch.py` на `doc/tools/arch/__main__.py`, добавить `docs paths --check`.
- [x] Зарегистрировать top-level команду `task-key` (`@register` в `cli/commands/task_key.py`).
- [x] Исправить `cli/output.py`: структурированные команды в human-режиме печатают свой JSON envelope, а не scan-сводку; scan/validate сохраняют прежний summary.
- [x] Дополнить `validation.py`: проверки `subtasks`, `related_docs`, `related_tests`, `stage_history`; структурные проверки выполняются даже при отсутствии/поломке project-конфига.
- [x] Сделать `implemented` обязательным полем каждой записи `index.json` (default `false`).
- [x] Обновить приёмочные тесты под единый envelope-контракт и изолированный temp-root с реальными YAML-конфигами.
- [x] Исправить fixture `UI-0001`: `project_context_refs` указывал на отсутствующий `doc.architecture.md`.
- [x] Синхронизировать документацию с фактическим путём CLI (`README.md`, `doc/AGENTS.md`, `doc/tools/README.md`, `doc/architecture/README.md`, `examples.md`, `SCENARIOS.md`).
- [x] Обновить реестр номеров задач (`task-number-registry.md`) для UI-0001…UI-0010.
- [x] Прогнать полный контур: `bash doc/tests/run.sh`, `validate`, `index check`, `docs paths --check`.

## Boundaries

Не реализуются Фазы 1–3 `nextplan.md` (constitution, clarify, delta-спеки, allocator, MCP, skills registry). `data/` не редактируется. Push/merge/deploy не выполняются.
