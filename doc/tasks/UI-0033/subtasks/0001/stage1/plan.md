<!-- plan-tier: micro -->
# UI-0033-0001: дефолты релиза и веток

## Изменение

- `_release_defaults` читает `project.release`: `default_branch`, `default_release`, `branch_patterns`.
- `_apply_release_defaults` заполняет только пустые/`unset` поля; ребёнок наследует значения родителя.
- Подключено в `init_task`, `decompose`, `_subtask_init`.

## Эквивалентность

| CASE | AC | Дано | Действие | Ожидание |
|---|---|---|---|---|
| CASE-1 | AC-1 | чистая fixture | task new --title | status open, bugfix/UI-0001, main, 0.1.0; validate exit 0 |
| CASE-2 | AC-2 | родитель с веткой bugfix/UI-0001 | task decompose | child.branch = bugfix/UI-0001 |

## Приёмка

| CASE | AC | Дано | Действие | Ожидание |
|---|---|---|---|---|
| CASE-1 | AC-1 | чистая fixture | task new --title | validate exit 0 и поля из project.release |
| CASE-2 | AC-2 | родитель с полями | task decompose | ребёнок наследует поля |

## Проверка

```bash
arch validate --brief
python3 -m unittest doc.tests.test_task_fields -q
```
