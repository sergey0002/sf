# UI-0028: Глоссарий — JSON-канон, CLI-поиск и синонимы

## 1. Зачем эта задача

Сейчас глоссарий — один Markdown-файл `doc/architecture/glossary.md` с H3-записями. Из этого следуют конкретные дефекты, каждый из которых наблюдался:

| Дефект | Наблюдение | Следствие |
|---|---|---|
| Термин не адресуем | `arch list --id TERM-task-key --json` → `[]` | нельзя сослаться на термин из задачи/документа |
| Нет проверки уникальности | `validate` проходит при любых дублях | два `TERM-*` с разным смыслом не обнаруживаются |
| Схема тела мертва | `schemas/bodies/glossary.json` содержит только `has_terms`, поле `term_format` не читается | контракт обещает больше, чем проверяется |
| Поиск без синонимов | `docs search` ранжирует по id/title/summary/heading/body | «ключ задачи» не находит термин «Номер и ключ задачи» |
| Нет связей с задачами | обратных ссылок нет | агент не знает, какие термины относятся к задаче |
| Неофициальные имена попадают в отчёты | в Markdown нет различия «официальный/поисковый» | планы и отчёты используют разные формулировки |

Цель: глоссарий становится **данными** (`glossary.json`), а поиск, скан и запись — **детерминированными операциями CLI**. Markdown остаётся, но только как генерируемое представление.

## 2. Принятые решения и почему

### 2.1 JSON — канон, Markdown — производный

- `doc/architecture/system/data.md`, «Политика формата» прямо требует JSON для машинных записей и индекса и запрещает YAML как формат обмена. Поэтому YAML не используется, несмотря на удобство.
- `jsonschema>=4.20` уже в `doc/tools/requirements.txt` — схема не требует новых зависимостей.
- `index.json` уже генерируется и проверяется (`index build/check`); глоссарий повторяет этот же паттерн, а не изобретает новый.
- Markdown остаётся для людей и для индексации: `glossary.md` генерируется, помечен в `generated_files`, ручная правка отвергается `check`.

### 2.2 Граница CLI

Решение осознанно **не** делает CLI единственным способом авторства: `architecture-contract.md` §8.2 и `manifest.md:456` фиксируют, что типизированные операции — кандидат, а не требование. Задача сужает это правило только для глоссария и только там, где CLI даёт проверяемую гарантию.

| Операция | Владелец | Обоснование |
|---|---|---|
| чтение (`lookup/search/match/query/refs`) | **только CLI** | заменяет чтение всего файла, даёт ранжирование и `match_type` |
| производные (`build`) | **только CLI** | index/md/vocab должны быть детерминированы |
| проверка (`validate/check`, `lint`, `scan`) | **только CLI** | единственный способ гарантировать инварианты |
| точечные мутации (`synonym add/remove`, `deprecate`) | **CLI предпочтителен** | payload меньше патча, типичные ошибки ловятся сразу |
| `add/update` | CLI поддерживается, файл допустим | длинный текст всё равно передаётся целиком |
| семантика (какой термин нужен, что значит) | агент/человек | CLI не имеет права решать |

### 2.3 Связи хранятся на стороне ссылающегося

`task.json` объявляет `glossary_terms`, архитектурный документ — `terms` во frontmatter. Глоссарий **не** хранит обратные ссылки. Причины:

- нет дрейфа двусторонних ссылок (классическая проблема ручных backlinks);
- задача сама декларирует используемую терминологию — это проверяемо;
- обратный индекс (`referenced_by`) полностью пересобирается `build`, поэтому не может устареть.

Цена: глоссарий не знает о ссылках без `build`, поэтому `check` обязателен в CI.

### 2.4 Два вида синонимов

- `official_synonyms` — допустимые официальные имена: показываются в отчётах, попадают в `vocab/accept.txt`.
- `search_synonyms` — только для поиска: никогда не выводятся как имя термина.
- `avoid` — запрещённые формулировки: попадают в `vocab/reject.txt`, **не участвуют** в положительном поиске (иначе поиск начнёт подтверждать запрещённое).

Инварианты (проверяются `validate`):

```
official_synonyms ∩ search_synonyms = ∅
avoid ∩ (term ∪ official_synonyms ∪ search_synonyms) = ∅
search_synonyms не содержат term и official_synonyms
```

## 3. Инвентарь файлов

### Создаются

| Путь | Роль |
|---|---|
| `doc/architecture/decisions/ADR-0002-glossary-json-store.md` | решение о JSON-источнике и границе CLI |
| `doc/architecture/glossary.json` | канон |
| `doc/architecture/schemas/glossary.schema.json` | схема канона |
| `doc/architecture/glossary.index.json` | generated: поисковый индекс + `referenced_by` |
| `doc/architecture/glossary.md` | generated view (заменяет текущий ручной файл) |
| `doc/config/vocab/accept.txt` | generated, Vale-совместимый |
| `doc/config/vocab/reject.txt` | generated |
| `doc/tools/arch/glossary.py` | загрузка, нормализация, инварианты, поиск, скан |
| `doc/tools/arch/cli/commands/glossary.py` | CLI-обёртка |
| `doc/tools/tests/test_glossary.py` | unit-тесты |

### Изменяются

| Путь | Что именно |
|---|---|
| `doc/config/paths.yaml` | `allowed_paths`, `generated_files`, `cli.allowed_commands` |
| `doc/tools/arch/cli/commands/registry.py` | регистрация группы `glossary` |
| `doc/tools/arch/body_validation.py` | убрать мёртвую `has_terms`/`term_format` логику или привести в соответствие |
| `doc/tools/arch/doc_ops.py` | expansion в `search`, блок `glossary` в `context` |
| `doc/tools/arch/store.py` | валидация `terms` во frontmatter |
| `doc/tools/arch/validation.py` | валидация `glossary_terms` в `task.json` |
| `doc/architecture/system/cli-command-map.md` | новые команды |
| `doc/architecture/system/cli-validation-rules.md` | новые коды и сообщения |
| `doc/architecture/glossary.md` | становится generated (содержимое из JSON) |
| `doc/tools/arch/task_record.py` | добавить `glossary_terms` в список известных полей, если он там перечисляется |
| `doc/skills/arch-cli/SKILL.md` | короткий раздел «glossary» |
| `doc/skills/architecture-read/SKILL.md` | «известен термин → `glossary lookup`» |
| `doc/tests/test_task_identity.py` | тест на фразу в `glossary.md` переписать |

### Почему vocab в `doc/config/`

`structure_rules.architecture_doc_extensions` содержит только `.md` и `.json`. Размещение `.txt` в `doc/architecture/` потребовало бы расширить правило для архитектурных документов. `doc/config/vocab/` уже конфигурационный каталог, и добавление `.txt` там не ослабляет правило для архитектуры. Альтернатива (расширить `architecture_doc_extensions` до `.txt`) допустима, но шире по последствиям.

## 4. Контракты данных

### 4.1 `glossary.json`

```json
{
  "schema_version": 1,
  "id": "GLO-system",
  "domain": "system",
  "title": "Словарь программной фабрики",
  "summary": "Значения терминов, квалифицированные доменом.",
  "status": "current",
  "terms": [
    {
      "id": "TERM-system-task-key",
      "term": "Номер и ключ задачи",
      "definition": "Детерминированный ключ из task_number и source.",
      "official_synonyms": ["task_key"],
      "search_synonyms": ["task key", "ключ задачи", "номер задачи"],
      "avoid": ["task.md как эквивалент ввода"],
      "abbreviation": null,
      "examples": [],
      "technical_mapping": ["task.json#task_key"],
      "related_terms": ["TERM-system-task-json"],
      "status": "approved",
      "owner": "task-intake",
      "since": "2026-01-01",
      "superseded_by": null
    }
  ]
}
```

Обязательные поля термина: `id`, `term`, `definition`, `status`. Остальные — с дефолтами (`[]`, `null`).

### 4.2 `glossary.index.json`

```json
{
  "index_schema_version": 1,
  "generated_from": "doc/architecture/glossary.json",
  "terms": [
    {
      "id": "TERM-system-task-key",
      "term": "Номер и ключ задачи",
      "norm": "номер и ключ задачи",
      "official_synonyms": ["task_key"],
      "norm_official": ["task key"],
      "search_synonyms": ["task key", "ключ задачи"],
      "norm_search": ["task key", "ключ задачи"],
      "abbreviation": null,
      "domain": "system",
      "status": "approved",
      "summary": "…",
      "definition": "…",
      "anchor": "term-system-task-key"
    }
  ],
  "referenced_by": {
    "TERM-system-task-key": [
      {"kind": "task", "ref": "UI-0016", "path": "doc/tasks/UI-0016/task.json", "field": "glossary_terms"},
      {"kind": "document", "ref": "ENT-task-input", "path": "doc/architecture/domains/task-lifecycle/entities/task-input.md", "field": "terms"}
    ]
  }
}
```

`norm_*` — нормализованные формы, чтобы поиск не нормализовал всё на каждый запрос. Индекс детерминирован: сортировка по `id`, ключи отсортированы, `\n` в конце.

### 4.3 `glossary.md` (generated)

Сохраняет frontmatter `type: glossary`, `id: GLO-system`, чтобы остаться в `index.json` и не ломать навигацию. Тело — H3-записи в текущем формате `### <term> — \`TERM-...\`` плюс блоки полей. Именно это делает переход обратимым: читатель видит тот же документ.

### 4.4 Новые поля

```yaml
# frontmatter архитектурного документа
terms: [TERM-system-task-key]
```

```json
// task.json
"glossary_terms": ["TERM-system-glossary-json"]
```

`document.schema.json` имеет `additionalProperties: true` — `terms` проходит без правки схемы. `index.schema.json` имеет `additionalProperties: false` — поэтому `terms` **не** попадает в `index.json`, чтобы не менять схему индекса. Это осознанное ограничение: связи живут в `glossary.index.json`.

## 5. Алгоритмы

### 5.1 Нормализация

```
normalize(s):
  s = unicodedata.normalize("NFC", s)
  s = s.casefold()
  s = s.replace("ё", "е")
  s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
  s = re.sub(r"\s+", " ", s).strip()
```

Порядок обязателен: NFC до casefold (иначе турецкая `İ` и составные формы дадут разные результаты), пунктуация после casefold.

### 5.2 Уровни поиска (`glossary search`)

| Уровень | Условие | score |
|---|---|---|
| 1 | `id` == запрос (регистр игнорируется) | 1000 |
| 2 | `norm(term)` == `norm(query)` | 900 |
| 3 | `norm_official` содержит `norm(query)` | 800 |
| 4 | `norm_search` содержит `norm(query)` | 700 |
| 5 | `norm(term)` начинается с `norm(query)` | 500 |
| 6 | Левенштейн ≤ `min(2, len//4)` и `len ≥ 4` | 300 − distance |
| 7 | вхождение токенов запроса в `definition` | 100 |

Сортировка: score убыв., затем `id` возрастает (детерминизм). `match_type` — имя уровня, `matched_on` — конкретная поверхность (например, введённый синоним), `display_term` — всегда `term`.

`avoid` не входит ни в один уровень. `search_synonyms` никогда не становится `display_term`.

### 5.3 Поиск в тексте (`match`)

1. Построить `surfaces = {(norm(surface), term_id, kind)}` из `term`, `official_synonyms`, `search_synonyms`.
2. `max_span` — максимум слов в поверхности.
3. Токенизировать текст с сохранением позиций.
4. Для каждой позиции пробовать окна от `max_span` до 1; побеждает **первое** (longest match).
5. Поглощённые токены не участвуют в следующих совпадениях (без дублей вложенных терминов).
6. `avoid` в поверхности не входит и как вхождение не отдаётся.
7. Ответ: `{term_id, kind, start, end, text}`.

### 5.4 Расширение `docs search`

До ранжирования:

1. Если `glossary.index.json` отсутствует — работать как раньше, добавить `notes: ["glossary index not found"]`.
2. Найти термины по запросу (уровни 1–6). Взять `canonical = term`, `official = official_synonyms`, `search = search_synonyms` найденных терминов. `avoid` — никогда.
3. `expanded_tokens = original ∪ tokens(canonical) ∪ tokens(official)`. Поисковые синонимы добавляют только исходный запрос (он уже в original), но не расширяют текст документа.
4. Новые уровни для документа:
   - документ объявляет `terms`, и один из них найден → `term_declared`, 900;
   - термин встречается в теле документа → `term_body`, 260;
   - совпадение только через поисковый синоним → `term_alias`, 250.
5. `term_declared` выше `title` (300) и ниже прямого `id` (1000).
6. В ответ добавить блок `glossary` (определения найденных терминов) и `matched_terms` в хит.
7. `--no-expand-terms` возвращает ровно прежнее поведение.

Инвариант: для запроса, не совпавшего ни с одним термином, результат побайтово совпадает с текущим.

### 5.5 Скан и lint

Классификация:

| Класс | Severity | Условие |
|---|---|---|
| `avoid` | error | встретилась формулировка из `avoid` |
| `unofficial_synonym` | warning | встретился `search_synonym`, но не официальная форма |
| `unknown_term` | info | слово/фраза похожа на термин, но отсутствует в глоссарии (эвристика: совпадение с `technical_mapping`-подобным паттерном не используется; только если включён `--detect-unknown`, иначе класс не выдаётся) |
| `undeclared_term` | info | термин встречается, но документ не объявляет его в `terms` |

Исключения скана: frontmatter, fenced-блоки (```` ``` ````/`~~~`), inline-code, цели Markdown-ссылок, HTML-комментарии. Это предотвращает ложные срабатывания в примерах кода.

`--suggest` добавляет `terms_add` — кандидатов для frontmatter. Файлы не изменяются никогда.

## 6. Порядок работ и зависимости

```
0001  JSON-канон, схема, миграция, validate/build/check, ADR
  ├── 0002  lookup/search/match/query/refs, docs search, docs context, lint
  └── 0003  synonym/add/update/deprecate, scan, --suggest
```

`0002` и `0003` независимы между собой, но оба требуют `0001`: без схемы и индекса нечего читать и нечем валидировать.

Порядок внутри `0001` строгий:

1. ADR (фиксирует решение до кода).
2. Схема.
3. `glossary.json` + миграция.
4. `validate`.
5. `build` + производные.
6. `check`.
7. `paths.yaml` и регистрация команд.

Причина: `paths.yaml` с `generated_files` до появления генератора сломает `docs paths --check`; поэтому объявления путей идут последними.

## 7. Приёмка

Фикстуры: временное дерево с копией `doc/architecture` и `doc/config`, минимальный `task.json` с `glossary_terms`, документ с `terms`. Сеть не используется. Оракулы: exit code, JSON-ответ, **байтовое** сравнение `glossary.json` до/после, содержимое `glossary.index.json`, `referenced_by`.

| CASE | AC | Дано | Действие | Ожидание и проверка | Ребёнок |
|---|---|---|---|---|---|
| CASE-1 | AC-1 | Чистое дерево с мигрированным `glossary.json`, производные отсутствуют | `arch glossary validate`, затем `build`, затем `check` | `validate` и `check` — exit 0; `build` создаёт ровно `glossary.index.json`, `glossary.md`, `vocab/accept.txt`, `vocab/reject.txt`; повторный `build` идемпотентен побайтно. | 0001 |
| CASE-2 | AC-1 | Валидное дерево; изменён `glossary.md` вручную и удалён `glossary.index.json` | `arch glossary check` | Exit 1, сообщение о drift с указанием файла; `glossary.json` не изменён. | 0001 |
| CASE-3 | AC-2 | `glossary.json` с дублирующимся `TERM-*` | `arch glossary validate` | Exit 1, назван дубль; файл не изменён. | 0001 |
| CASE-4 | AC-2 | `official_synonyms` пересекается с `search_synonyms`; отдельно `avoid` пересекается с `term` | `arch glossary validate` | Оба случая exit 1 с указанием термина и поля. | 0001 |
| CASE-5 | AC-2 | ID `TERM-task-json` без домена | `arch glossary validate` | Exit 1 с ожидаемым форматом `TERM-<domain>-<slug>`, если владелец не утвердил исключение. | 0001 |
| CASE-6 | AC-3 | Известный `TERM-system-task-key` | `arch glossary lookup TERM-system-task-key --json` | Ровно одна запись, `term` официальный, поля синонимов разделены. | 0002 |
| CASE-7 | AC-3 | Неизвестный `TERM-missing` | `arch glossary lookup TERM-missing --json` | Exit 1, пустой `data`, без чтения всего файла в ответ. | 0002 |
| CASE-8 | AC-3 | Термин с `search_synonyms: ["ключ задачи"]` | `arch glossary search "ключ задачи" --json` | `match_type: search_synonym`, `matched_on` — введённый синоним, `display_term` — официальный термин. | 0002 |
| CASE-9 | AC-3 | Два термина: точное совпадение и префиксное | `arch glossary search <query> --json` | Точное совпадение выше префиксного; `score` убывает; порядок детерминирован. | 0002 |
| CASE-10 | AC-4 | Текст с термином, официальным синонимом и `avoid`-формулировкой | `arch glossary match --text "..." --json` | Позиции для термина и синонима; `avoid` не отдан как вхождение термина. | 0002 |
| CASE-11 | AC-4 | Текст содержит `ключ задачи` при наличии обоих терминов | `arch glossary match --file <path> --json` | Побеждает longest match; вложенный короткий термин не дублируется. | 0002 |
| CASE-12 | AC-5 | `task.json` с `glossary_terms`, текст с другим термином | `arch glossary query --task <key> --json` | `declared` из задачи, `inferred: true` у найденного по тексту; оба списка раздельны. | 0002 |
| CASE-13 | AC-5 | Объявленный термин также находится по тексту | `arch glossary query --task <key> --text "..." --json` | Объявленный не дублируется и не заменяется inferred-копией. | 0002 |
| CASE-14 | AC-7 | `task.json` с `glossary_terms` и документ с `terms` | `arch glossary build`, затем `refs TERM-*` | `referenced_by` содержит задачу и документ с путями; `build` воспроизводим. | 0002 |
| CASE-15 | AC-7 | `task.json` ссылается на несуществующий `TERM-*` | `arch glossary validate` | Exit 1, назван файл, поле и неизвестный ID. | 0002 |
| CASE-16 | AC-7 | Термин без ссылок из задач и документов | `arch glossary check` | Не ошибка; термин перечислен в отчёте как неиспользуемый. | 0002 |
| CASE-17 | AC-6 | Валидный термин | `arch glossary synonym add TERM-* --search "..." --dry-run` | Exit 0, предпросмотр; байты `glossary.json` не изменены. | 0003 |
| CASE-18 | AC-6 | Валидный термин | `arch glossary synonym add TERM-* --official "..."` без dry-run, затем `check` | Синоним записан, `check` — exit 0; повторное добавление того же синонима — exit 5 без второй записи. | 0003 |
| CASE-19 | AC-6 | Синоним пересекается с `avoid` или с другим видом синонима | `arch glossary synonym add ...` | Exit 1; сравнить байты файла до/после — без изменений. | 0003 |
| CASE-20 | AC-6 | Термин `approved`, указан `--superseded-by` | `arch glossary deprecate TERM-old --superseded-by TERM-new` | `status: deprecated` и `superseded_by` записаны; `validate` и `check` — exit 0. | 0003 |
| CASE-21 | AC-6 | Неизвестный `TERM-*` либо пустое определение | `arch glossary add`, `arch glossary update` | Exit 1, машинный отчёт; файл не изменён. | 0003 |
| CASE-22 | AC-8 | Реализованная задача | Проверить `decisions/ADR-*.md` и `index.json` | ADR существует, содержит контекст, решение, границу CLI и последствия; `validate` и `index check` — exit 0. | 0001 |
| CASE-23 | AC-9 | Запрос «ключ задачи»; документ объявляет `terms: [TERM-system-task-key]` | `arch docs search "ключ задачи" --json` | Хит документа с `match: term_declared` и `score: 900`; блок `glossary` содержит определение; `matched_terms[0].match_type: search_synonym`; `display_term` официальный. | 0002 |
| CASE-24 | AC-9 | Тот же запрос с `--no-expand-terms` | `arch docs search "ключ задачи" --no-expand-terms --json` | Документ не найден по синониму; `glossary` пуст; результат совпадает с поведением до изменения. | 0002 |
| CASE-25 | AC-9 | Запрос содержит формулировку из `avoid` | `arch docs search "<avoid>" --json` | `avoid` не расширяет запрос и не даёт `glossary`-хит; документ не поднимается. | 0002 |
| CASE-26 | AC-10 | Документ содержит `avoid`-формулировку | `arch glossary scan --scope product --json` | Классификация `error` с путём и позицией; ни один файл не изменён (сравнить байты). | 0003 |
| CASE-27 | AC-10 | Документ использует неофициальный синоним; другой — необъявленный термин | `arch glossary scan --scope product --json` и `--suggest` | `warning` и `info` соответственно; `--suggest` возвращает `terms_add` без записи в файл. | 0003 |
| CASE-28 | AC-10 | Документ с код-блоком и ссылкой, где встречается синоним | `arch glossary scan --file <path> --json` | Код-блоки, frontmatter и ссылки исключены; позиции только в прозе. | 0003 |
| CASE-29 | AC-11 | План с неофициальным синонимом и с `avoid` | `arch glossary lint --file doc/tasks/UI-0028/stage1/plan.md --json` | `warning` для синонима, `error` для `avoid`, у обоих путь и позиция; exit 1 при `error`. | 0002 |
| CASE-30 | AC-11 | `task.json` с `glossary_terms` | `arch docs context --task UI-0028 --json` | Блок `glossary` содержит определения объявленных терминов с официальным `term`. | 0002 |

## 8. Процедура проверки (для исполнителя)

1. До изменений: `bash doc/tests/run.sh --brief` и записать исходный результат в план стадии.
2. После каждого шага: целевая команда + `arch validate --brief` + `arch index check` + `arch docs paths --check`.
3. Для отказных CASE сравнивать **байты** файла: `sha256sum` до и после.
4. Для `build` — запустить дважды и сравнить `glossary.index.json` и `glossary.md` побайтно (идемпотентность).
5. Итог: `bash doc/tests/run.sh --brief`; записать в `verification.json` команды, коды выхода и снимок.

## 9. Чего делать нельзя

- Менять `index.schema.json`, чтобы протащить `terms` в `index.json`. Связи живут в `glossary.index.json`.
- Добавлять YAML-канон «потому что удобнее»: это прямо запрещено `VIEW-data`.
- Автоматически заменять прозу (`scan --fix --apply`) — вне scope, высокий риск.
- Включать `avoid` в expansion или в положительные уровни поиска.
- Выводить `search_synonym` как `display_term`.
- Генерировать `terms` во frontmatter из текста: это семантика, CLI только предлагает.
- Переименовывать legacy `TERM-task-json`/`TERM-task-key` без подтверждения владельца.
- Добавлять `snowballstemmer` или иную морфологию: отложено.
- Ослаблять `docs paths --check`, добавляя `.txt` в `architecture_doc_extensions`, если выбран вариант с `doc/config/vocab/`.

## 10. Готово, когда

- `arch glossary validate/build/check` зелёные, `check` ловит drift.
- `lookup/search/match/query/refs` работают и возвращают `match_type`/`display_term`.
- `docs search` расширяет запрос и не меняет поведение без терминов.
- `scan` и `lint` классифицируют вхождения и не пишут файлы.
- `task.json` и frontmatter валидируют `TERM-*`.
- ADR фиксирует решение; `index check`, `validate`, `docs paths --check`, `run.sh --brief` проходят.
