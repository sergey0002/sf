---
id: ENT-task-record
type: entity
title: Версионированная запись задачи
summary: "Неизменяемый intent в task.json, изменяемое состояние в state.json и append-only журнал переходов events.jsonl с ревизиями и ключами идемпотентности."
status: draft
domain: task-lifecycle
related: [ENT-task-input, ENT-stage-artifact, ENT-verification-evidence, FLOW-task-lifecycle, REG-cli-command-map]
implemented: true
---

# Версионированная запись задачи

## Назначение и граница

Разделить неизменяемое намерение задачи, изменяемое состояние жизненного цикла и
журнал переходов. Legacy-запись без `record_version` остаётся валидной и читается
как раньше: её `phase` хранится в `task.json`.

## Хранение

| Артефакт | Роль |
|---|---|
| `task.json` | Канонический ввод. У версионированной записи дополнительно хранит `record_version`, `flow_version`, `intent_digest`. |
| `state.json` | Изменяемое состояние: `revision`, `phase`, `event_count`, `last_event_id`, `state_digest`. |
| `events.jsonl` | Append-only журнал переходов: `event_id`, `type`, `expected_revision`, `revision`, `payload`, `prev_digest`, `digest`. |

`flow_version` — SHA-256 содержимого `flows/<flow>/config.yaml` на момент миграции,
поэтому последующая правка шаблона не меняет уже запущенную запись.
`intent_digest` — SHA-256 канонического подмножества intent-полей. Поля `phase`,
`subtasks`, `stage_history` и `changed_files` изменяемы и в дайджест не входят.

## Инварианты

- Intent неизменяем после миграции: изменение intent-поля даёт ошибку
  `intent fields changed since migration`.
- Ревизия монотонна: событие применяется только к `expected_revision`, равной
  текущей ревизии; иначе — конфликт без записи.
- `event_id` — ключ идемпотентности. Повтор того же ключа с тем же типом,
  ревизией и payload возвращает исходный результат и не создаёт вторую запись.
  Тот же ключ с другим содержимым — конфликт.
- Журнал образует цепочку `prev_digest` → `digest`. Повреждённая или частичная
  строка не материализуется как успешное состояние.
- `state.json` — производное от журнала значение. `task replay` пересобирает его
  и тем самым восстанавливает состояние после прерванной записи.

## Команды

| Команда | Результат |
|---|---|
| `arch task migrate <key> [--dry-run]` | Добавляет версионированные поля и файлы; повторный запуск идемпотентен. |
| `arch task event <key> --id ID --type phase.changed --expected-revision N --phase P` | Проверяет ревизию и идемпотентность, затем пишет событие и состояние. |
| `arch task replay <key> [--dry-run]` | Пересобирает `state.json` из журнала, проверяя цепочку дайджестов. |

`diagnose`, `status`, `close` и проверка зависимостей читают действующую фазу из
`state.json`, если запись версионирована. `scan --scope tasks` сообщает о
несоответствии состояния журналу.

## Evidence

Реализация: `doc/tools/arch/task_record.py`, `doc/tools/arch/task_ops.py`,
`doc/tools/arch/cli/commands/task.py`. Проверки:
`doc/tests/test_task_identity.py` (миграция, идемпотентность, конфликт ревизии,
replay и повреждённый журнал).
