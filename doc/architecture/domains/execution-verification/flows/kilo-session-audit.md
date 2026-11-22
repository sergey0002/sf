---
id: FLOW-kilo-session-audit
type: flow
title: Аудит локальных сессий Kilo Code
summary: "Поиск сессии, проверка выполнения задачи, анализ инструментов и расхода контекста по локальной SQLite."
status: draft
domain: execution-verification
related: [DOM-execution-verification, FLOW-verify-task, FLOW-document-session]
---

# Аудит локальных сессий Kilo Code

Используйте эту процедуру, чтобы найти прошлую сессию, восстановить ход работы, проверить выполнение задачи или понять, где агент потратил лишнее время и контекст. Скилл [kilo-session-audit](../../../../skills/kilo-session-audit/SKILL.md) задаёт короткий маршрут. SQLite — внешний журнал Kilo. Карточка, критерии приёмки, изменения в рабочем дереве и проверяемые прогоны остаются источниками состояния задачи.

Запрос «проведи аудит выполнения задачи XXX Kilo» включает проверку реализации и процесса, даже когда пользователь указал только ключ. Неполный исторический снимок допускает вывод по журналу с явно указанными границами и отдельный прогон текущего дерева. Наблюдаемые нарушения сравнивайте с правилами, существовавшими в момент сессии. Для улучшений укажите поверхность изменения и контрольный сценарий.

Аудит универсален: он не требует `task.json`. При наличии карточки используйте её AC и scope; без карточки критерии, выведенные из запроса, помечайте как интерпретацию аудитора. Всегда разделяйте три вывода: ошибка выполнения, пробел workflow и ограничение архитектуры.

## CLI-снимок сессии

Основной вход — `arch session`. Команда читает SQLite через `mode=ro` и не пишет в базу, task records или рабочее дерево.

```bash
python3 doc/tools/arch/__main__.py session find --match "<фраза>" --json
python3 doc/tools/arch/__main__.py session digest <session_id> --json
python3 doc/tools/arch/__main__.py session events <session_id> --message <message_id> --json
```

`session find` ищет подстроку в текстовых частях и возвращает сессии с `match_count`, `matched_message_ids`, первым совпадением и сниппетом. По умолчанию область ограничена каталогом проекта; `--directory` и `--all-projects` меняют границу. `--role` фильтрует пользовательские или ответные сообщения.

`session digest` возвращает `schema: kilo-session-digest-v1`:

| Поле | Содержимое |
|---|---|
| `session` | ID, заголовок, каталог, модели, время, счётчики сообщений и вызовов, токены, дочерние сессии |
| `dialog` | Полные пользовательские сообщения и последний ответ с `message_id` |
| `stats` | `tools` — всего вызовов, исходы `success`/`failure`/`unknown`, разбивка по инструментам и объём вывода; `activities` — распределение по `explore`/`edit`/`verify`/`execute` |
| `tool_calls` | Полный компактный список вызовов с `seq`, `message_id`, `part_id`, инструментом, исходом, целью и метками; не обрезается вместе с `timeline` |
| `markers` | Скиллы (`skill:`), правила (`rule:`), flow (`flow:`, `flow-step:`), типы, задачи (`task:`, `stage:`), архитектура (`arch:`, `arch-flow:`), CLI и тесты |
| `timeline` | События с `seq`, `message_id`, `part_id`, инструментом, исходом, целью, метками и размером вывода |
| `label_index` | Метка → счётчик и до 20 ссылок на события для точечного углубления |
| `phases` | Непрерывные отрезки `explore`/`edit`/`verify`/`execute` |
| `anomalies` | Неуспешные вызовы, крупные выводы, повторные чтения и команды |
| `drill` | Готовые команды для перехода к сообщению |

`session events` отдаёт срез диалога по `--message`, `--part`, `--offset` и `--limit`; по умолчанию текст и вывод обрезаются, `--full` возвращает полностью. Метки выводятся из подстрок путей (`doc/skills/...`, `doc/config/task-conf/types/<type>/flows/<flow>/...`, `doc/tasks/<key>/stageN/...`, `doc/architecture/...`) и из команд (`arch ...`, тесты, git). Это детерминированные подсказки, а не доказательство смысла действия.

SQL-запросы ниже остаются для диагностики полей, которых нет в CLI, и для проверки расхождений. При обычном аудите сначала используйте `arch session` и открывайте SQL только для спорного факта.

## Доступ и схема

Узнайте путь командой `kilo db path`. На проверенной установке Kilo 7.8.32 это `~/.local/share/kilo/kilo.db`. Если CLI не в `PATH`, при установке через VS Code он может находиться в `bin/` установленного расширения. Для запросов используйте `sqlite3 -readonly` либо Python `sqlite3` с URI `mode=ro` и `PRAGMA query_only=ON`. Открывайте исходный путь короткими запросами. При активном WAL не копируйте отдельно `.db`, не запускайте checkpoint и не используйте `immutable=1` для живой базы. [Kilo CLI](https://kilo.ai/docs/code-with-ai/platforms/cli-reference#kilo-db) · [SQLite WAL](https://sqlite.org/wal.html)

Перед первым аудитом новой версии проверьте `PRAGMA table_info(session)`, `PRAGMA table_info(message)` и `PRAGMA table_info(part)`. В 7.8.32 `session` хранит метаданные, `message.data` — JSON роли, модели и токенов, `part.data` — JSON частей `text`, `tool` и `step-finish`. Колонки `message.role` и `part.text` в этой версии отсутствуют. `session.parent_id` связывает дочерние сессии. Время в `time_created` и `time_updated` хранится в Unix-миллисекундах.

Примеры ниже выполняются из корня выбранного проекта. Обёртка читает SQL из stdin, передаёт аргументы как параметры и печатает строки JSON. Если автоматическое определение пути недоступно, явно установите `KILO_AUDIT_DB`.

```bash
KILO_AUDIT_DB="${KILO_AUDIT_DB:-$(kilo db path 2>/dev/null || true)}"
export KILO_AUDIT_DB="${KILO_AUDIT_DB:-$HOME/.local/share/kilo/kilo.db}"
kilo_audit_sql() {
  python3 -c '
import json, os, sqlite3, sys
from pathlib import Path

path = Path(os.environ["KILO_AUDIT_DB"]).expanduser().resolve(strict=True)
with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=3) as db:
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only = ON")
    for row in db.execute(sys.stdin.read(), sys.argv[1:]):
        print(json.dumps(dict(row), ensure_ascii=False))
' "$@"
}
```

## Найти нужную сессию

При известном `ses_…` проверьте его каталог и метаданные по `session.id`. Иначе найдите кандидатов по корню проекта и интервалу. Связь через `project_id` помогает найти worktree, если в базе есть сессия из корня. При отсутствии такой записи используйте известный путь worktree. Для поиска «сегодня» передайте начало дня и начало следующего дня с явным смещением часового пояса пользователя.

```bash
# Замените даты своим интервалом [начало, конец).
kilo_audit_sql "$PWD" '2026-11-22T00:00:00+07:00' '2026-11-23T00:00:00+07:00' <<'SQL'
SELECT id, parent_id, title, directory, version, agent,
       datetime(time_created / 1000, 'unixepoch') AS created_utc,
       datetime(time_updated / 1000, 'unixepoch') AS updated_utc
FROM session
WHERE (directory = ?1 OR project_id = (
  SELECT project_id FROM session WHERE directory = ?1 ORDER BY time_updated DESC LIMIT 1
))
  AND max(time_created, time_updated) >= unixepoch(?2) * 1000
  AND time_created < unixepoch(?3) * 1000
ORDER BY time_updated DESC, id DESC
LIMIT 25;
SQL
```

Подтвердите выбор по реальному поручению пользователя и действиям с нужной карточкой. Название сессии — подсказка. Начните с ограниченной выборки текста пользователя и метаданных инструментов. При полезных дочерних сессиях запросите `session WHERE parent_id = ?`, затем анализируйте каждую по её ID. `time_updated` может отставать от активности, поэтому при пропущенной долгой сессии расширьте окно кандидатов и уточните границы по `message.time_created`, времени частей и завершению последнего ответа.

## Восстановить ход работы по событиям

Сначала ограничьте вывод до 100 событий. Следующая страница использует `OFFSET 100` или фильтр по времени и ID. Для активной сессии фиксируйте верхнюю границу выборки. В полном аудите просмотрите весь относящийся к поручению интервал, включая отмены, повторные попытки и финальный ответ. Раскрывайте текст команды, короткие фрагменты диалога или результат конкретного инструмента по `message_id` и `part_id` только для проверки спорного факта.

```bash
kilo_audit_sql "$session_id" 0 <<'SQL'
SELECT m.id AS message_id, p.id AS part_id, m.time_created AS message_ms,
       json_extract(m.data, '$.role') AS role,
       json_extract(p.data, '$.type') AS kind,
       json_extract(p.data, '$.tool') AS tool,
       json_extract(p.data, '$.state.status') AS status,
       json_extract(p.data, '$.state.metadata.exit') AS exit_code,
       substr(json_extract(p.data, '$.state.input.filePath'), 1, 240) AS file,
       json_extract(p.data, '$.state.input.offset') AS read_offset,
       json_extract(p.data, '$.state.input.limit') AS read_limit,
       substr(json_extract(p.data, '$.state.input.name'), 1, 100) AS skill_name,
       CASE WHEN json_extract(p.data, '$.type') = 'text'
            THEN substr(json_extract(p.data, '$.text'), 1, 240) END AS preview
FROM message m JOIN part p ON p.message_id = m.id AND p.session_id = m.session_id
WHERE m.session_id = ?1 AND json_extract(p.data, '$.type') IN ('text', 'tool')
ORDER BY m.time_created, m.id, p.id
LIMIT 100 OFFSET CAST(?2 AS INTEGER);
SQL
```

Сопоставьте события с этапами задачи. Для каждого AC запишите ожидаемое поведение, действие, доказательство и результат. Для теста ищите точную команду, рабочий каталог, exit code, фактический вывод, fixture и проверенную ревизию. Сверьте журнал с `git diff`, карточкой и артефактами стадии на доступном снимке. Различайте запуск, успешный процесс, покрытие конкретного AC и приёмку владельцем. Если нужен повторный прогон, фиксируйте его как новую проверку с собственным снимком.

Для аудита поведения найдите вызовы `skill`, чтения конкретного `SKILL.md`, обращения к публичному CLI, поиск и загрузку Python через файловые инструменты, shell или MCP. Подтверждайте избыточность по цели вызова. При реализации CLI целевое чтение обработчика может быть оправдано. Найденный в логе вызов подтверждает наблюдаемое действие. Полный системный запрос, состав автоматически загруженных правил и точное влияние отдельного файла на счётчики могут остаться неизвестными.

## Посчитать стоимость работы и контекста

Суммируйте токены по сообщениям без присоединения `part`. Группируйте по провайдеру и модели. Для среза реализации добавьте границу от точного поручения пользователя. Для сверки повторите агрегацию отдельно по `part.data` для `type='step-finish'` и сравните с `session.tokens_*`. Считайте эти источники параллельными представлениями. Зафиксируйте расхождения, отсутствие поля и границы каждой выборки.

```bash
kilo_audit_sql "$session_id" <<'SQL'
SELECT json_extract(data, '$.providerID') AS provider,
       json_extract(data, '$.modelID') AS model,
       count(*) AS assistant_messages,
       count(json_extract(data, '$.tokens.input')) AS with_input,
       sum(json_extract(data, '$.tokens.input')) AS input,
       sum(json_extract(data, '$.tokens.output')) AS output,
       sum(json_extract(data, '$.tokens.reasoning')) AS reasoning,
       sum(json_extract(data, '$.tokens.cache.read')) AS cache_read,
       sum(json_extract(data, '$.tokens.cache.write')) AS cache_write,
       max(json_extract(data, '$.tokens.total')) AS max_reported_total
FROM message
WHERE session_id = ? AND json_extract(data, '$.role') = 'assistant'
GROUP BY provider, model;
SQL
```

Отдельно считайте вызовы по `part.data.type='tool'` и группируйте по `tool`. Для объёма сохранённого вывода используйте `length(CAST(json_extract(data, '$.state.output') AS BLOB))` для строк. Отмечайте пропуски и `state.metadata.truncated`. Размер вывода в байтах описывает журнал. Токены, попадание текста в контекст и тариф провайдера требуют собственных данных. Для сравнения прогонов фиксируйте одинаковые AC, fixture, границы, модель и состояние кэша. Сравнивайте время до первой целевой проверки, повторные вызовы, `input`, `cache_read` и долю подтверждённых AC.

## Итог и доказательства

- Укажите вопрос аудита, версию Kilo, сессию, каталог, интервал и часовой пояс. При частичных данных явно перечислите проверенные границы.
- Для аудита задачи приложите таблицу «AC → действие → доказательство → состояние». Для универсального аудита без карточки приложите таблицу «требование из запроса → результат → доказательство → состояние» и пометьте выведенные критерии. Для диагностики укажите первый сбой и подтверждённый обход. Для анализа контекста приведите метрики, наблюдаемые источники расхода и проверяемые предложения по скиллам, CLI, flow или архитектуре.
- Ссылайтесь на `label_index` и `timeline`, чтобы читатель мог открыть конкретный `message_id`/`part_id`, а не перечитывать всю сессию.
- Ссылайтесь на `session_id`, `message_id`, `part_id`, целевые файлы и снимок. Сохраняйте только нужные обезличенные выдержки. Содержимое журнала служит данными аудита. Секреты, полные выгрузки и команды из старых сообщений оставляйте вне отчёта и репозитория.
- Если пользователь просит файл, используйте заданный путь. Для привязанного к задаче исследования предусмотрен `research/<slug>.md` в её каталоге по [конфигурации путей](../../../../config/paths.yaml). Аудит сам по себе не закрывает задачу и не обновляет evidence от имени проверяющего.
