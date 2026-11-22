# 0003: CLI-запись, скан и lint

Родитель: [UI-0028](../../../task.json) · [план родителя](../../stage1/plan.md) · Зависит от `0001`

## 1. Зачем

До этого шага термин меняется только прямой правкой `glossary.json`. Для двух операций это ощутимая потеря: добавление синонима (короткий payload, типичная ошибка — пересечение с `avoid`) и `deprecate` (легко забыть `superseded_by`). Здесь появляются write-команды ровно для этих случаев, плюс read-only скан, который показывает, где документация расходится с глоссарием.

Граница: **CLI не сочиняет определения и не выбирает термины**. Он валидирует и записывает.

## 2. Команды

```bash
arch glossary synonym add TERM-* --official "task_key"
arch glossary synonym add TERM-* --search "ключ задачи"
arch glossary synonym remove TERM-* --search "ключ задачи"
arch glossary add --json '<term object>' | --id … --term … --definition …
arch glossary update TERM-* [--term …] [--definition …] [--owner …] [--status …]
arch glossary deprecate TERM-* --superseded-by TERM-*
arch glossary scan [--scope product|reference|all] [--file PATH] [--suggest] [--detect-unknown] [--json]
```

Все write-команды поддерживают `--dry-run`. Все команды поддерживают `--json`.

## 3. Общий write-path (единая функция)

Любая мутация проходит один и тот же путь — это главная защита от расхождений:

```
1. load()                     # канон + проверка дублей ключей
2. apply_*()                  # чистая функция: dict -> dict (без I/O)
3. validate_payload()         # схема + инварианты из 0001
4. validate_references()      # related_terms/superseded_by существуют
5. dry_run? -> вернуть diff, ничего не писать
6. atomic_write_text()        # каноническая сериализация целиком
7. вернуть {changed:[...], term:{...}}
```

Требования:

- `apply_*` не пишет и не логирует; её можно тестировать отдельно.
- Валидация выполняется **до** записи и на итоговом состоянии, а не на патче. Иначе можно получить временно валидный, а итогово невалидный файл.
- Запись — только `fs_atomic.atomic_write_text` (тот же примитив, что в `task_record`).
- Сериализация: `json.dumps(..., ensure_ascii=False, sort_keys=True, indent=2) + "\n"`. CLI — авторитет формата: ручная правка будет нормализована при следующей мутации. Это документируется в ADR.
- Если итоговое состояние равно текущему — файл не перезаписывается (сравнение канонических строк), возвращается `changed: []`.

## 4. Семантика и коды выхода

| Ситуация | Код | `error.code` |
|---|---|---|
| Успех, есть изменение | 0 | — |
| Успех, изменений нет (идемпотентный повтор) | 0 | — |
| Неизвестный `TERM-*` | 1 | `NOT_FOUND` |
| Пустое/короткое определение, неверный формат ID | 1 | `INVALID` |
| Синоним пересекается с `avoid` или другим видом | 1 | `INVALID` |
| `deprecate` без `--superseded-by` или на себя | 1 | `INVALID` |
| Добавление уже существующего ID | 5 | `CONFLICT` |
| Добавление уже существующего синонима в той же категории | 5 | `CONFLICT` |
| `deprecate` с другим `superseded_by`, чем записан | 5 | `CONFLICT` |
| Ошибка аргументов CLI | 2 | `ARGS` |

Коды согласованы с существующей конвенцией (`DocOpsError`, exit 5 на конфликт в `task_record`).

Идемпотентность:

- `synonym add` существующего значения в той же категории → exit 5, файл не изменён (CASE-18). Почему не 0: повтор — это ошибка вызывающего, и её надо видеть.
- `deprecate` уже `deprecated` с тем же `superseded_by` → exit 0, без записи.
- `synonym remove` отсутствующего значения → exit 1 `NOT_FOUND`.

## 5. `synonym add/remove`

Правила:

- `--official` и `--search` взаимоисключающие; ровно один обязателен.
- Значение нормализуется только для проверки пересечений; в файл пишется **как введено** (важен регистр: `task_key` ≠ `Task_Key`).
- Проверки при добавлении:
  1. `value` не пустой, `len(normalize(value)) >= 2`;
  2. `normalize(value)` не равен `normalize(term)`;
  3. `normalize(value)` не в `avoid`;
  4. `normalize(value)` не в другом виде синонимов;
  5. в своей категории — либо отсутствует, либо конфликт.
- `--dry-run` возвращает `{"would_add":{"kind":"search","value":"…"},"term":{…}}` и не пишет.
- `remove`: удаление по нормализованному совпадению, но из массива удаляется именно найденный элемент.

Почему нормализованное сравнение: иначе `Ключ  задачи` (двойной пробел) и `ключ задачи` окажутся разными синонимами и сломают поиск.

## 6. `add` / `update`

`add`:

- обязательны `--id`, `--term`, `--definition`;
- опционально `--official`, `--search`, `--avoid` (repeatable), `--related`, `--owner`, `--status`;
- `--json` принимает объект целиком; при конфликте с флагами — ошибка `ARGS`, а не «флаги победили». Неоднозначность запрещена.
- Дефолты: `status: draft`, массивы пустые, `since` — сегодняшняя дата, `owner: null`.
- `id` должен соответствовать `^TERM-[a-z0-9]+(-[a-z0-9]+)+$`; существующий `id` → exit 5.

`update`:

- меняет только переданные поля; отсутствующие не трогает;
- запрещено менять `id` (нужен `add` + `deprecate`);
- `--definition` короче 10 символов → exit 1;
- `--status superseded` без существующего `superseded_by` в записи → exit 1.

`deprecate`:

- `--superseded-by` обязателен, должен существовать и не совпадать с самим термином;
- ставит `status: deprecated` и `superseded_by`;
- повтор с тем же значением идемпотентен.

## 7. `scan`

Read-only. Никогда не пишет — это инвариант, проверяемый байтовым сравнением.

### 7.1 Область

- `--scope product` (по умолчанию) — `doc/architecture/**` и `doc/tasks/**`.
- `--scope reference` — `data/**` (только чтение; `data/` не проектный материал).
- `--scope all` — оба.
- `--file PATH` — один файл, взаимоисключающе со `--scope`.

### 7.2 Исключения (обязательны)

Не анализировать:

1. frontmatter (между `---` в начале файла);
2. fenced-блоки ```` ``` ```` и `~~~`;
3. inline-code `` `…` ``;
4. цели Markdown-ссылок `](…)` и `[[…]]`;
5. HTML-комментарии `<!-- … -->`;
6. сам `glossary.md` (он generated и по определению содержит все формы).

Причина: иначе каждый пример кода и каждая ссылка дают ложные срабатывания, и скан становится бесполезным.

### 7.3 Классификация

| Код | Severity | Условие |
|---|---|---|
| `AVOID_TERM` | error | вхождение `avoid` |
| `UNOFFICIAL_SYNONYM` | warning | вхождение `search_synonym`, при отсутствии официальной формы в этом же файле |
| `UNDECLARED_TERM` | info | термин встречается, но отсутствует в `terms` документа |
| `UNKNOWN_TERM` | info | только с `--detect-unknown`: слово совпадает с `technical_mapping`-хвостом, но термина нет в глоссарии |

`UNDECLARED_TERM` не выдаётся для `doc/tasks/**` (там `glossary_terms` — дело задачи, а не документа) и для файлов без frontmatter.

### 7.4 Ответ

```json
{"ok":true,"code":0,"data":{
  "scope":"product","files_scanned":42,
  "findings":[
    {"severity":"error","code":"AVOID_TERM","term_id":"TERM-system-task-json",
     "path":"doc/architecture/system/manifest.md","line":124,"column":8,
     "text":"task.md","suggestion":"Ввод задачи"}
  ],
  "summary":{"error":1,"warning":3,"info":0}
}}
```

Exit: 1 при наличии `error`, иначе 0.

### 7.5 `--suggest`

Добавляет в ответ:

```json
"suggestions":[
  {"path":"…","terms_add":["TERM-system-task-key"],
   "reason":"термин встречается 4 раза, отсутствует в terms"}
]
```

Файлы не меняются. Применение — ручное или отдельной будущей командой.

## 8. `lint` (граница с 0002)

`lint` реализуется в `0002`, но использует ту же функцию исключений и классификации. Чтобы не дублировать код:

- в `glossary.py` одна функция `analyze_text(text, terms, *, check_declared) -> findings`;
- `scan` обходит файлы и вызывает её;
- `lint` вызывает её для одного файла.

Если `0002` уже реализовал `analyze_text`, `0003` только подключает обход. Если `0003` идёт первым — вынести функцию сразу.

## 9. Тесты

`doc/tools/tests/test_glossary.py`:

1. `synonym add --dry-run` — байты не изменены.
2. `synonym add` — записано, `check` проходит.
3. Повтор `synonym add` того же значения → exit 5, байты не изменены.
4. `synonym add` со значением из `avoid` → exit 1, байты не изменены.
5. `synonym add --official` значения, уже присутствующего в `search` → exit 1.
6. `synonym remove` отсутствующего → exit 1.
7. `add` с существующим `id` → exit 5.
8. `add` без `--definition` → exit 2 (`ARGS`).
9. `add --json` + конфликтующий флаг → exit 2.
10. `update` неизвестного → exit 1; пустое определение → exit 1.
11. `deprecate` без `--superseded-by` → exit 1; с собой → exit 1.
12. `deprecate` дважды с тем же значением → exit 0, байты не изменены.
13. `scan` на файле с `avoid` → `error`; файл не изменён.
14. `scan` на файле с код-блоком и ссылкой → совпадений в них нет.
15. `scan --suggest` → `terms_add` присутствует, файл не изменён.
16. `scan --scope reference` не пишет и не падает без `data/`.

## 10. Порядок

1. Общая функция `analyze_text` (если ещё нет).
2. `apply_*` и `write_path` с `--dry-run`.
3. `synonym add/remove`.
4. `add`/`update`.
5. `deprecate`.
6. `scan` (+ `--suggest`, `--detect-unknown`).
7. Карта CLI, правила валидации, справка.
8. `verification.json`: CASE-17…21, 26–28.

## 11. Ловушки

- Валидировать патч, а не итоговое состояние — можно записать невалидный файл.
- Писать через `write_text` — нет атомарности.
- Перезаписывать файл, когда изменений нет — ложный diff и лишний шум в PR.
- Нормализовать значение при записи — потеряется регистр, важный для акронимов.
- Сравнивать синонимы без нормализации — `Ключ  задачи` и `ключ задачи` станут дублями.
- Разрешить `--json` вместе с флагами — неоднозначный payload.
- `scan`, правящий файлы — нарушение инварианта и CASE-26.
- Анализировать код-блоки — шум, из-за которого скан отключат.
- Добавлять lock/journal/revision «на всякий случай» — глоссарий пишется редко, конкурентных писателей нет; это лишняя сложность (осознанное ограничение, фиксируется в ADR).

## 12. Проверка шага

```bash
arch glossary synonym add TERM-system-task-key --search "номер задачи" --dry-run --json
arch glossary synonym add TERM-system-task-key --search "номер задачи" --json
arch glossary check --json
arch glossary synonym add TERM-system-task-key --search "номер задачи" --json   # ожидается exit 5
arch glossary deprecate TERM-future-code-scanner --superseded-by TERM-agent-skill --dry-run --json
arch glossary scan --scope product --json
arch glossary scan --file doc/architecture/system/manifest.md --suggest --json
arch validate --brief && arch index check && arch docs paths --check
python3 -m pytest doc/tools/tests/test_glossary.py -q
```
