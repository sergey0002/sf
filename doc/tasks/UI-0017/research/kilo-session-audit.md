# Аудит сессии Kilo: реализация UI-0017

## 1. Срез аудита

| Параметр | Значение |
|---|---|
| Сессия | `ses_dfc11d655ffeBcQDPPcUtDCTkZ` |
| Заголовок | «Реализация задачи 17 из README» |
| Агент / модель | `code` / `plusvibeapi/deepseek-v4.1-flash-1017` |
| Kilo | 7.8.32 |
| Каталог | `/home/newuser/projects/sf` |
| Поручение | `msg_203ee2955001IoEgX576GInSSD` — «читай ридми задача 17 реализуй» |
| Запрос аудита | `msg_204287e78001KhCyakybhrxJqR` |
| Интервал реализации | 2026-11-22 15:44:29Z → 16:31:09Z (46 мин 40 с) |
| Дочерние сессии | нет |
| Вызовов инструментов | 153 (реализация), из них `bash` 139, `edit` 14, `skill` 2 |
| Токены (сообщения) | input 2 444 132, output 53 854, reasoning 31 242, cache_read 20 129 408 |
| Токены (сессия) | input 2 674 327, output 54 316, reasoning 31 621, cache_read 20 617 344, total 23 377 608 |

Граница: независимые проверки ниже выполнены на **текущем общем рабочем дереве**, которое во время аудита изменялось параллельным писателем (см. §5.1). Это ограничение, а не исторический снимок.

## 2. Задание и полномочия

Поручение разрешало реализацию UI-0017. `task.json` ограничивал scope: `doc/config/`, `doc/tools/`, `doc/tests/`, `doc/architecture/`. Запрещены push/merge/deploy и запись во внешние источники. Сессия осталась в scope, внешних действий не выполняла, индекс пересобирала явно. Замечание: запись `doc/tasks/UI-0017/...` — это артефакты задачи, они допустимы, хотя формально не входят в `scope.in`.

## 3. Критерии приёмки → действие → доказательство → вердикт

| AC | Ожидание | Наблюдаемое действие | Доказательство | Вердикт |
|---|---|---|---|---|
| UI-0017 AC-1 | `bugfix` проходит `verify → fix`; `docs-only` — короткий путь без детей | Добавлены `flow-1` переходы и `task advance` | `test_bugfix_flow_returns_from_verify_to_fix_and_rejects_stale_events`, `test_docs_only_flow_short_path_without_children`; ручной прогон `verify --checks.failed--> fix` | Подтверждён |
| UI-0017 AC-2 | Неизвестный вход, конфликт правил, циклы и битые ссылки дают явные причины; отказ не меняет состояние | `select-flow` коды `UNKNOWN-FACT`/`MISSING-FACT`/`CONFLICT`; `scan` проверяет недостижимость и неоднозначность; `decompose`/`advance` не пишут при отказе | `test_flow_selection_reports_unknown_missing_and_conflict`, `test_subtask_dependencies_compute_ready_blocked_and_cycles`, `test_scan_task_conf_reports_unreachable_and_ambiguous_flow`; побайтовое сравнение `state.json` в тестах | Подтверждён |
| UI-0017-0001 AC-1 | Ошибочные ссылки, неоднозначные правила, недостижимые состояния видны в диагностике | `flows.py` + `scan --scope task-conf` | `test_scan_task_conf_reports_unreachable_and_ambiguous_flow`; ручной `scan` | Подтверждён |
| UI-0017-0002 AC-1 | Fixtures покрывают повторный переход, блокировки и короткий путь | Тесты на повтор `--id`, `blocked_by`, `docs-only` | Три целевых теста | Подтверждён, но см. D1: fixtures не проверяют порядок шагов |

## 4. Дефекты реализации

### D1 (высокий). Переходы `bugfix` противоречат объявленным `steps` и prompt

В `doc/config/task-conf/types/bugfix/flows/standard-implementation/config.yaml` порядок шагов:

```
architecture-context → reproduce → plan → fix → review-implementation → architecture-sync → verify → close
```

а исполняемый happy path по `transitions`:

```
architecture-context → reproduce → plan → fix → architecture-sync → verify → review-implementation → close
```

`review-implementation` и `architecture-sync` переставлены. Проверка:

```text
forward path: [... 'fix', 'architecture-sync', 'verify']
steps match forward path: False
```

Следствия:

- агент, идущий по `task advance`, выполняет ревью **после** verify, что противоречит `prompt.md` (там ревью — шаг 5, verify — шаг 7);
- `scan --scope task-conf` даёт `0 incidents`: проверка не сверяет `states`/`transitions` с `steps`;
- тест `test_bugfix_flow_returns_from_verify_to_fix_and_rejects_stale_events` кодирует **неверный** порядок (`fix.applied → architecture-synced → checks.passed → review-implementation`), поэтому дефект не ловится.

Это единственный AC-блокирующий по смыслу дефект: формально AC-1 выполнен, но исполняемый контракт и документация расходятся.

### D2 (средний). `subtasks[].status` родителя не синхронизируется

После закрытия детей в `doc/tasks/UI-0017/task.json`:

```json
"subtasks": [
  {"id": "0001", "status": "open", ...},
  {"id": "0002", "status": "open", ...}
]
```

при `phase: completed` у детей и родителя. `task close` пишет только `phase` и не обновляет объявленные статусы. `diagnose` читает фазу ребёнка, поэтому функционально не блокирует, но запись противоречива и вводит в заблуждение при чтении карточки.

### D3 (средний). Типы с несколькими flow не требуют таблицы выбора

`feature`, `refactor`, `planning` имеют по два `allowed_flows`, но `flow-selection.yaml` есть только у `bugfix` и `docs`. `task select-flow --type feature` возвращает `CONFIG` (файл не найден), а `scan --scope task-conf` — `0 incidents`. Механизм выбора необязателен там, где решение реально нужно.

### D4 (низкий). Неинформативная ошибка `advance` для legacy-flow

Для flow без `schema_version` (например, `feature/standard-implementation`) `task advance` возвращает `NO-FLOW: the selected flow has no initial state` с подсказкой «declare initial_state». Причина другая — flow не исполняемый (`flow-1`). Подсказка уводит в неверную сторону.

### D5 (низкий). Evidence фиксирует фильтрованные селекторы, а план заявляет полный прогон

Итоговый `doc/tasks/UI-0017/stage1/verification.json` содержит только:

```
python3 -m unittest discover -s doc/tests -p test_task_identity.py -k flow -q
python3 -m unittest discover -s doc/tests -p test_task_identity.py -k subtask_dependencies -q
```

Полный `test_task_identity.py` и `run.sh --brief` действительно прогонялись (seq 100, 153), но в evidence не записаны. План утверждает «полный `test_task_identity.py` пройдены» — утверждение верно по факту прогона, но не подтверждается записанным evidence.

### D6 (низкий). `replay_state` не сверяет `event` у `flow.transitioned`

`replay_state` проверяет `from`, `to`, `transition_id` и цепочку `from`, но не сверяет поле `event` с таблицей переходов. Подмена `event` при том же `from/to` пройдёт replay. Риск низкий (журнал append-only и с дайджестами), но инвариант «событие соответствует переходу» не проверяется.

### D7 (процесс). Ручная правка записи после `task close`

После `task close` (seq 136) фазы и `stage_history.status` выставлялись inline-Python (seq 137), а не CLI. Для legacy-записи это допустимо, но обходит единый путь и не журналируется. Для версионированной записи такая правка была бы отклонена.

### D8 (среда). Параллельный писатель в том же checkout

Во время 115-секундного полного прогона изменился `doc/tools/arch/cli/commands/task.py`:

```text
changed during full suite: ['doc/tools/arch/cli/commands/task.py']
```

В дереве появились чужие изменения: `doc/tools/arch/task_registry.py` (23:41), команды `task new`/`task registry`, `--title` у `task init`. `task.py` изменялся в 23:55, уже после финального ответа. Это объясняет:

- ошибку evidence `changed during run` (seq 134);
- повторную неактуальность снимков;
- то, что финальное утверждение «evidence актуально» перестало быть верным после сессии.

## 5. Качество взаимодействия и процесса

### 5.1 Метрики

| Метрика | Значение | Оценка |
|---|---|---|
| Время до первой записи | 4 мин 42 с | Хорошо |
| Время до первой целевой проверки | 9 мин 14 с (`scan --scope task-conf`) | Приемлемо |
| Первый полный прогон | 9 мин 38 с | Рано, до появления новых тестов |
| `plan.md` записан | 16:04:13, через ~15 мин после первой правки | Плохо: план после реализации |
| `architecture-context` зафиксирован в плане | только в ретроспективном плане | Плохо |
| Shell-чтение (`sed`/`cat`/`grep`/`find`/`ls`/`wc`/`stat`) | 67 вызовов | Плохо |
| Выделенные `read`/`grep`/`glob` | 0 | Нарушение инструкций |
| Запись через shell heredoc | 22 | Плохо: обход `write`/`edit` |
| `edit` | 14 | Норма |
| Вызовы evidence | 16 (8 записей + проверки) | Плохо: churn |
| Полные прогоны | 12 `unittest` + 3 `run.sh` | Избыточно |
| `todowrite` | 0 | Упущено для 150+ шагов |
| Чтение `doc/AGENTS.md` | нет | Пробел |
| Скилл `arch-cli` | не загружен | Допустимо: задача меняет CLI |

### 5.2 Крупные источники контекста

| seq | Команда | Байт |
|---|---|---|
| 7 | `sed -n '540,640p' nextplan.md` | 35 027 |
| 46 | `grep ... nextplan.md \| sed -n '1,120p'` | 28 438 |
| 13 | `sed -n '650,740p' nextplan.md` | 24 632 |
| 36 | `sed -n '1,220p' task_record.py; sed -n '220,592p' ...` | 24 461 |

Чтение целых диапазонов и широких `grep` вместо адресных `arch docs read`/`search` и `Read` с offset/limit.

### 5.3 Токены по этапам

| Этап | Сообщений | input | output | reasoning | cache_read |
|---|---|---|---|---|---|
| explore 15:44–15:49 | 29 | 235 800 | 4 334 | 11 852 | 2 094 720 |
| implement 15:49–15:54 | 35 | 305 396 | 23 222 | 5 198 | 5 792 768 |
| test/fix 15:54–16:04 | 22 | 416 338 | 13 492 | 5 096 | 4 166 016 |
| docs/evidence 16:04–16:30 | 38 | 1 486 598 | 12 806 | 9 096 | 8 075 904 |
| аудит-ответ | 23 | 269 797 | 9 008 | 6 015 | 5 136 768 |

Этап документации и evidence съел ~60 % input и ~40 % cache_read — дороже реализации. Причина — повторные записи evidence, полные прогоны и повторные чтения документов.

## 6. Рекомендации

### P0 — исправить до признания контракта flow надёжным

**R1. Привести переходы `bugfix` в соответствие с `steps` и prompt.**
Точка правки: `doc/config/task-conf/types/bugfix/flows/standard-implementation/config.yaml`, `doc/tools/arch/flows.py`, `doc/tools/arch/cli/commands/builtin.py`, `doc/tests/test_task_identity.py`.
Изменение: порядок `fix → review-implementation → architecture-sync → verify → close`; добавить в `validate_flow_definition` проверку, что happy path `flow-1` совпадает с порядком `steps`, и что каждому шагу соответствует состояние. Тест: утверждение порядка, а не только наличия переходов. Проверка: `scan --scope task-conf` на сломанном порядке даёт инцидент; тест падает при перестановке.

**R2. Изолировать рабочее дерево и замораживать снимок.**
Точка правки: `go-to-task`/`review-implementation` skill, `task_ops.close`, `evidence`.
Изменение: требовать отдельный worktree на задачу; перед `task evidence` фиксировать «снимок заморожен»; `task close` отказывать при `evidence --check` != current; добавить предупреждение о параллельном писателе (mtime/лок). Проверка: два писателя в одном checkout не портят evidence; отказ без записи.

**R3. Синхронизировать запись при закрытии.**
Точка правки: `task_ops._close_task`, `task_record`.
Изменение: `close` обновляет `subtasks[].status` и `stage_history.status` атомарно; добавить команду фиксации результата стадии вместо ручного JSON. Проверка: после `close` карточка не содержит `status: open` у завершённых детей.

### P1 — процесс и валидация

**R4. Заменить shell-чтение на выделенные инструменты.**
Точка правки: `AGENTS.md`, `go-to-task`, `arch-cli` skill.
Изменение: явное правило «Read/Grep/Glob для файлов; `arch docs read/search/toc` для архитектуры; shell — только git/тесты». Проверка: в аудите доля shell-read падает; вывод меньше.

**R5. Требовать `flow-selection.yaml` при нескольких flow.**
Точка правки: `_scan_task_conf`, `flows.validate_flow_selection`.
Изменение: если `len(allowed_flows) > 1`, отсутствие таблицы — инцидент. Проверка: `scan --scope task-conf` ловит `feature`/`refactor`/`planning`.

**R6. Перестроить работу с evidence.**
Точка правки: `go-to-task`, `evidence`, flow `verify`.
Изменение: сначала финализировать код/доки/план, затем одна запись evidence; записывать полный `run.sh --brief` или полный набор; не использовать evidence как test runner; `--check` только на финале. Проверка: одна запись на снимок, ноль повторов из-за собственных правок.

**R7. Писать план до реализации.**
Точка правки: `go-to-task`, `flow-steps` gate.
Изменение: запретить `implement` до `plan` с заполненными AC→CASE→oracle; в `diagnose` показывать незавершённый шаг. Проверка: план существует и содержит правила проекта до первой правки.

**R8. Понятная ошибка для legacy-flow.**
Точка правки: `flows.find_transition`, `task_ops.advance`.
Изменение: при отсутствии `schema_version` возвращать `UNSUPPORTED-FLOW` с подсказкой «flow не в формате flow-1». Проверка: `advance` на `feature/standard-implementation` даёт новый код.

### P2 — экономия контекста и наблюдаемость

**R9. `todowrite` для многошаговых задач.** 150+ вызовов без списка шагов; список снижает повторы и помогает возобновлению.

**R10. Читать `doc/AGENTS.md` первым.** Сейчас правило не загружалось; добавить обязательный шаг в `go-to-task`.

**R11. Адресное чтение.** Для `nextplan.md` использовать `arch docs read`/`search` по якорям вместо `sed` диапазонов; для исходников — `Read` с offset/limit; для вывода CLI — `--brief`.

**R12. Метрики аудита.** Добавить в `session digest`/отчёт долю shell-read против выделенных инструментов, число повторных записей evidence и число полных прогонов — как проверяемые сигналы процесса.

## 7. Вердикт

| Область | Оценка | Основание |
|---|---|---|
| Реализация | 7/10 | AC выполнены, отказы не меняют состояние, тесты и схемы на месте; минусы: D1 (порядок шагов), D2, D3, D6 |
| Процесс и взаимодействие | 5/10 | Верный scope и честный финальный отчёт; минусы: 67 shell-read при 0 выделенных, план после реализации, evidence churn, отсутствие изоляции от параллельного писателя, нет todo |

Блокеры для следующего выпуска: D1 (контракт flow противоречит документации), D8 (общий checkout с параллельным писателем делает evidence нестабильным), D2 (несогласованная запись).

## 8. Ссылки

- Финальный ответ: `msg_20418e246001A6ymUzUgTH7eNp`
- Первая запись: seq 52, `msg_203f27793001r2SuDhG5RvxfHS`
- План (ретроспективный): seq 116, `msg_2040038ae001w6gQBl3PVQR6PM`
- Evidence `changed during run`: seq 134, `msg_2040ed916001yBrnP7sfyuXTM1`
- Ручная правка записи: seq 137, `msg_2040f8763001vPMOHYUMWD3j4W`
- Изменение `advance` после полного прогона: seq 147, `msg_204152e470015AEVEkbDsKyeVa`
- Крупные выводы: seq 7 (`msg_203ee4a8a001SouV65xLpsAEe8`), seq 46 (`msg_203f0f991001lbcUdZvRPMaGJV`)
- Файлы: `doc/config/task-conf/types/bugfix/flows/standard-implementation/config.yaml`, `doc/tools/arch/flows.py`, `doc/tools/arch/validation.py`, `doc/tools/arch/task_ops.py`, `doc/tests/test_task_identity.py`, `doc/tasks/UI-0017/task.json`

## 9. Ограничения аудита

- Текущее дерево изменялось параллельным писателем во время аудита; независимые прогоны описывают текущее состояние, а не замороженный снимок сессии.
- Содержимое журнала Kilo использовано как данные; системный prompt и автоматически загруженные правила не восстановимы полностью.
- Байты вывода и токены — разные представления; стоимость провайдера не рассчитывалась (`cost: 0.0`).

## 10. Статус правок после аудита

| Дефект / рекомендация | Статус | Где |
|---|---|---|
| D1 порядок переходов `bugfix` | исправлен | `bugfix/.../config.yaml`, `flows.py` (сверка `steps`) |
| D2 `subtasks[].status` при закрытии | исправлен | `task_ops._sync_closed_records` |
| D3 таблица выбора для нескольких flow | исправлен | `feature`/`refactor`/`planning` + `scan` |
| D4 ошибка legacy-flow | исправлен | `advance` → `UNSUPPORTED-FLOW` |
| D5 evidence только с фильтрами | закрыт в stage2 | полный `test_task_identity.py` в `stage2/verification.json` |
| D6 replay не сверяет `event` | исправлен | `task_record.replay_state` |
| D7 ручная правка записи | не повторялась; закрытие синхронизирует запись | `task close` |
| D8 параллельный писатель | смягчён: stale `snapshot_files` блокирует закрытие | `closure_state` |
| R4/R6/R7 инструменты, evidence, план | внесено | `doc/AGENTS.md`, `go-to-task` |

Проверки stage2: полный `test_task_identity.py`, `scan --scope all`, `docs paths --check`, `index check`, `bash doc/tests/run.sh --brief`.
