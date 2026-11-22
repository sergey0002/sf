<!-- plan-tier: micro -->
# UI-0033-0002: миграция и тесты

## Изменение

- Бэкфилл: `status` из `phase` (completed→done, verification→review, иначе open), `target_release` 0.1.0, `branch` по шаблону источника, `release_branch` main.
- Новый тест `doc/tests/test_task_fields.py`; фикстуры `_make_minimal_task` дополнены полями.

## Эквивалентность

| CASE | AC | Дано | Действие | Ожидание |
|---|---|---|---|---|
| CASE-1 | AC-1 | мигрированный корпус | task validate (выборка + дети) | exit 0 |
| CASE-2 | AC-2 | чистая fixture | unittest test_task_fields | 7 тестов OK |

## Приёмка

| CASE | AC | Дано | Действие | Ожидание |
|---|---|---|---|---|
| CASE-1 | AC-1 | корпус | task validate | exit 0 |
| CASE-2 | AC-2 | fixture | unittest | OK |

## Проверка

```bash
arch validate --brief
bash doc/tests/run.sh --gate
```
