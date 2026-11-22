# 0002: Поиск, интеграция в docs search и обратные ссылки

Родитель: [UI-0028](../../../task.json) · [план родителя](../../stage1/plan.md) · Зависит от `0001`

## 1. Зачем

`0001` создаёт данные и индекс, но агент всё ещё не может ими пользоваться: нет адресуемого чтения, нет ранжирования, нет связей. Кроме того, у проекта уже есть `arch docs search` (`doc_ops.py`), и если глоссарий останется отдельным поиском, появятся два несогласованных ранжирования. Задача шага — **встроить глоссарий в существующий поиск**, а не построить второй.

## 2. Что должно появиться

| Возможность | Команда | Зачем |
|---|---|---|
| точное чтение термина | `glossary lookup TERM-*` | 1 запись вместо чтения всего файла |
| ранжированный поиск | `glossary search <q>` | синонимы, `match_type`, `display_term` |
| поиск в тексте | `glossary match --text/--file` | позиции терминов, longest match |
| термины задачи | `glossary query --task/--text` | `declared` + `inferred` |
| обратные связи | `glossary refs TERM-*` | кто ссылается на термин |
| расширение docs search | `docs search <q>` | синонимы работают во всём поиске |
| термины в контексте | `docs context --task` | определения до написания плана |
| проверка плана | `glossary lint --file` | официальная терминология в отчётах |

## 3. Контракты ответов

### 3.1 `lookup`

```json
{"ok":true,"code":0,"data":{
  "id":"TERM-system-task-key",
  "term":"Номер и ключ задачи",
  "definition":"…",
  "official_synonyms":["task_key"],
  "search_synonyms":["task key","ключ задачи"],
  "avoid":["…"],
  "domain":"system","status":"approved",
  "related_terms":["TERM-system-task-json"]
}}
```

Неизвестный ID → `{"ok":false,"code":1,"error":{"code":"NOT_FOUND","message":"unknown term 'TERM-missing'","field":"id"}}`, exit 1. Не возвращать список «похожих»: это работа `search`.

### 3.2 `search`

```json
{"ok":true,"code":0,"data":{"query":"ключ задачи","hits":[
  {"id":"TERM-system-task-key","display_term":"Номер и ключ задачи",
   "match_type":"search_synonym","matched_on":"ключ задачи","score":700,
   "domain":"system","status":"approved","summary":"…"}
]}}
```

`match_type` ∈ `{id, term, official_synonym, search_synonym, prefix, fuzzy, definition}`.

### 3.3 `match`

```json
{"ok":true,"code":0,"data":{"matches":[
  {"term_id":"TERM-system-task-key","kind":"term","start":12,"end":30,
   "text":"Номер и ключ задачи","line":3}
]}}
```

`kind` ∈ `{term, official_synonym, search_synonym}`. `avoid` не выдаётся никогда.

### 3.4 `query`

```json
{"ok":true,"code":0,"data":{
  "declared":[{"id":"TERM-…","term":"…","source":"task.json:glossary_terms"}],
  "inferred":[{"id":"TERM-…","term":"…","match_type":"search_synonym","inferred":true}],
  "text":"…"
}}
```

Правило: если ID есть в `declared`, он **не** дублируется в `inferred`; `inferred` содержит только новые.

### 3.5 `refs`

```json
{"ok":true,"code":0,"data":{
  "id":"TERM-system-task-key",
  "referenced_by":[
    {"kind":"task","ref":"UI-0016","path":"doc/tasks/UI-0016/task.json","field":"glossary_terms"},
    {"kind":"document","ref":"ENT-task-input","path":"…/task-input.md","field":"terms"}
  ]
}}
```

## 4. Реализация поиска (`glossary.py`)

### 4.1 Нормализация — единственная функция

```python
def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.casefold()
    text = text.replace("ё", "е")
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()
```

Не создавать вторую нормализацию в `doc_ops.py` — импортировать эту. Иначе `docs search` и `glossary search` разойдутся на `ё`/пунктуации.

### 4.2 Уровни

| Уровень | Условие | score |
|---|---|---|
| `id` | `normalize(query) == normalize(id)` | 1000 |
| `term` | `normalize(query) == norm(term)` | 900 |
| `official_synonym` | совпадение с `norm_official` | 800 |
| `search_synonym` | совпадение с `norm_search` | 700 |
| `prefix` | `norm(term).startswith(norm(query))` и `len(query) >= 3` | 500 |
| `fuzzy` | Левенштейн ≤ `min(2, len(query)//4)`, `len(query) >= 4` | 300 − distance |
| `definition` | все токены запроса есть в `norm(definition)` | 100 |

Порядок уровней фиксирован: вернуть первый подходящий, а не сумму. Суммирование даёт нестабильные результаты при добавлении синонимов.

Сортировка: `(-score, id)`. Никаких зависимостей от порядка в JSON.

### 4.3 `match` (longest match)

```python
def match_text(text, terms, *, line_offset=1):
    surfaces = []  # (norm_surface, term_id, kind, word_count)
    max_span = max(word_count)
    # токенизация с позициями: re.finditer(r"\w+", text)
    # для каждой позиции i пробовать span от max_span до 1
    # собрать окно, normalize, сравнить с множеством surfaces
    # при совпадении: записать, i += span (поглощение)
```

Требования:

- Сравнение по `normalize`, не по сырому тексту.
- Побеждает наибольший span; при равенстве — `term` выше `official_synonym`, `official_synonym` выше `search_synonym`.
- `line` считать по `text.count("\n", 0, start) + line_offset`.
- `avoid` в `surfaces` не добавляется.
- Пустой результат — `matches: []`, exit 0 (не ошибка).

### 4.4 `query`

1. Прочитать `task.json` по ключу (через существующий резолвер путей, не собирать путь вручную).
2. `declared` — из `glossary_terms`; каждый ID проверить на существование.
3. Если передан `--text`, прогнать `search` и `match`; добавить в `inferred` те ID, которых нет в `declared`.
4. Если у задачи есть план/отчёт, `--text` может не передаваться — тогда `inferred` пуст.

### 4.5 `refs` и `referenced_by`

Источники:

- все `doc/tasks/**/task.json` (включая subtasks) с полем `glossary_terms`;
- все `.md` в `doc/architecture/**` с `terms` во frontmatter.

Сборка в `build` (расширить `0001`), чтение — `refs` из `glossary.index.json`. `refs` **не** сканирует дерево на каждом вызове: это дорого и дублирует `build`.

Правило `check`: если `glossary.index.json` устарел относительно текущих `task.json`/frontmatter, `check` сообщает drift. То есть `referenced_by` входит в проверку drift наравне с `glossary.md`.

## 5. Интеграция в `arch docs search`

Точка входа: `doc_ops.search(store, query, *, scope="product", limit=5, include_archived=False)`.

### 5.1 Изменение сигнатуры

```python
def search(..., expand_terms: bool = True) -> dict
```

CLI (`builtin.py`, парсер `docs search`) добавляет `--no-expand-terms` с `action="store_false", dest="expand_terms"`.

### 5.2 Загрузка индекса

```python
index = _load_glossary_index(config)   # None, если файла нет
```

- Файла нет → `notes.append("glossary index not found; term expansion disabled")`, работать как раньше.
- Файл битый → `notes.append(...)`, не падать: поиск не должен ломаться из-за глоссария. `glossary check` сообщит об этом отдельно.

### 5.3 Расширение

```python
matched_terms = glossary_search(query, index)      # уровни 1–6
canonical_tokens = tokens(term)
official_tokens = tokens(official_synonyms)
expanded = original_tokens | canonical_tokens | official_tokens
```

`search_synonyms` **не** добавляются в `expanded`: они уже покрыты исходным запросом, а добавление превратило бы поиск в «расширение по всем синонимам», что размывает ранжирование.

`avoid` не участвует нигде.

### 5.4 Новые уровни в `_rank_product`

Добавить **до** проверки `_has_all(all_text, tokens)`, чтобы документ, объявивший термин, находился даже без буквального вхождения:

```python
declared = metadata.get("terms") or []
declared_hit = [t for t in declared if t in matched_ids]
if declared_hit:
    return _hit(..., match="term_declared", score=900,
                matched_terms=[...], glossary=[...])
```

Затем существующая цепочка (id 1000 → alias 1000 → title 300 → summary 200 → heading 150 → body 100), с добавлением:

- `term_body` 260 — термин найден `match_text` в теле документа;
- `term_alias` 250 — совпадение только через `search_synonym`.

Почему 900, а не 1000: прямое совпадение `id` должно оставаться сильнее. Почему выше `title` (300): «этот документ про этот термин» — более сильный сигнал, чем случайное слово в заголовке.

### 5.5 Ответ

```json
{
  "query": "…",
  "scope": "product",
  "limit": 5,
  "total_matched": 3,
  "hits": [
    {"id":"ENT-task-input","match":"term_declared","score":900,
     "matched_terms":[{"term_id":"TERM-system-task-key","display_term":"…",
                       "match_type":"search_synonym","matched_on":"ключ задачи"}],
     "glossary":[…]}
  ],
  "glossary": [
    {"id":"TERM-system-task-key","term":"…","definition":"…","match_type":"search_synonym"}
  ],
  "notes": []
}
```

Блок `glossary` на верхнем уровне — «definition first»: агент получает смысл, не открывая документ. Дублирование в хите допустимо: хит привязан к документу, верхний блок — к запросу.

### 5.6 Инвариант совместимости

Для запроса без терминов ответ должен быть **побайтово** идентичен текущему (кроме добавленных пустых `glossary: []` и `notes`). Если проще — не добавлять ключи, когда терминов нет. Выбрать один вариант и закрепить тестом.

## 6. Интеграция в `arch docs context`

`context(store, task_key, case_id, ...)` уже собирает объявленные ссылки задачи. Добавить:

1. Прочитать `glossary_terms` из `task.json`.
2. Для каждого ID добавить `{"id","term","definition","status"}` в новый блок `glossary`.
3. Неизвестный ID — элемент с `state: "missing"`, как уже делается для документов (`doc_ops.py:917-925`).
4. Блок добавляется в конец ответа, не меняя существующие ключи.

## 7. `glossary lint`

```bash
arch glossary lint --file <path> [--json]
```

- `match_text` по файлу (пропуская frontmatter, fenced-блоки, inline-code, цели ссылок — та же функция исключений, что в `scan`).
- Классификация:
  - вхождение `avoid` → `error`;
  - вхождение `search_synonym`, если в этом же документе нет официальной формы → `warning`;
  - термин есть в тексте, но отсутствует в `terms` → `info` (только с `--check-declared`).
- Exit 1 при наличии `error`, иначе 0. `warning`/`info` — 0.
- Ответ: `{"path":…, "findings":[{"severity","code","term_id","line","column","text","suggestion"}]}`.

`lint` не пишет. Замена прозы — вне scope.

## 8. Валидация связей

### 8.1 `store.py`

`validate_related` проверяет frontmatter `related`. Добавить аналогичную проверку `terms`:

- `terms` — массив строк, `pattern ^TERM-`;
- каждый ID существует в `glossary.json`;
- дубликаты запрещены.

Неизвестный ID → `"{path}: unresolved term id 'TERM-…'"`. Формат совпадает с существующим сообщением для `related`, чтобы вывод оставался однородным.

### 8.2 `validation.py`

`_validate_glossary_terms(value, errors)` по образцу `_validate_related_docs`:

- массив строк;
- `pattern ^TERM-`;
- уникальность.

Вызвать рядом с `_validate_related_docs`. Поле **не** добавлять в `task_schema_required_fields`: оно опционально.

### 8.3 `task_record.py`

Если `FIELDS`/известные поля перечисляются — добавить `glossary_terms`, чтобы `task migrate` не потерял поле.

## 9. Тесты

`doc/tools/tests/test_glossary.py`:

1. `lookup` известного → одна запись; неизвестного → exit 1.
2. `search`: id > term > official > search > prefix > fuzzy > definition.
3. `search` не возвращает `avoid`.
4. `search` `display_term` всегда официальный.
5. `match`: longest match, вложенный термин не дублируется.
6. `match`: `avoid` отсутствует в результате.
7. `match`: позиции и `line` корректны для многострочного текста.
8. `query`: `declared` не дублируется в `inferred`.
9. `refs`: задача и документ попадают в `referenced_by`.
10. `docs search` с термином: `term_declared` 900; без термина — прежний результат.
11. `docs search --no-expand-terms` — документ не найден по синониму.
12. `docs context` содержит `glossary`.
13. `lint`: `avoid` → error, синоним → warning.

## 10. Порядок

1. `normalize`, `lookup`, `search` (+ тесты 1–4).
2. `match` (+ 5–7).
3. `query` (+ 8).
4. `refs` и `referenced_by` в `build`; `check` учитывает drift индекса (+ 9).
5. `store.py` и `validation.py` для `terms`/`glossary_terms`.
6. `docs search` expansion (+ 10–11).
7. `docs context` (+ 12).
8. `lint` (+ 13).
9. Карта CLI и правила валидации.
10. `verification.json`: CASE-6…16, 23–25, 29–30.

## 11. Ловушки

- Вторая нормализация в `doc_ops.py` — расхождение с `glossary search`.
- `search_synonyms` в `expanded` — размывание ранжирования и ложные хиты.
- `avoid` в `expanded` — поиск начнёт «подтверждать» запрещённое.
- Сравнение сырого текста вместо `normalize` — падение на регистре и `ё`.
- `match` без поглощения токенов — дубли вложенных терминов.
- `refs`, сканирующий дерево на каждый вызов — медленно и дублирует `build`.
- Расширение, меняющее результат для запросов без терминов — ломает существующие тесты и ожидания.
- Возврат `search_synonym` как `display_term` — искажает отчёты.
- Ошибка загрузки индекса, роняющая `docs search` — поиск должен деградировать, а не падать.

## 12. Проверка шага

```bash
arch glossary lookup TERM-system-task-key --json
arch glossary search "ключ задачи" --json
arch glossary match --file doc/architecture/system/manifest.md --json
arch glossary query --task UI-0028 --json
arch glossary refs TERM-system-task-key --json
arch docs search "ключ задачи" --json
arch docs search "ключ задачи" --no-expand-terms --json
arch docs context --task UI-0028 --json
arch glossary lint --file doc/tasks/UI-0028/stage1/plan.md --json
arch validate --brief && arch index check && arch docs paths --check
python3 -m pytest doc/tools/tests/test_glossary.py -q
```
