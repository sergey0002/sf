# 0001: JSON-канон, схема и миграция терминов

Родитель: [UI-0028](../../../task.json) · [план родителя](../../stage1/plan.md)

## 1. Зачем именно этот шаг первым

`0002` и `0003` читают и пишут `glossary.json`. Если начать с поиска или write-команд, придётся дважды менять формат. Поэтому сначала фиксируется ADR (решение), затем схема (контракт), затем данные (миграция), и только после этого генерация и проверки.

Порядок внутри шага обязателен: `paths.yaml` с `generated_files` объявляется **после** появления генератора, иначе `arch docs paths --check` начнёт падать на отсутствующих производных.

## 2. ADR — что и почему

Файл: `doc/architecture/decisions/ADR-0002-glossary-json-store.md`

Обязательный frontmatter:

```yaml
---
id: ADR-0002
type: decision
title: "Глоссарий: JSON-канон, Markdown как производное представление"
summary: "Структурированные термины хранятся в JSON; Markdown, индекс и словарь генерируются; CLI владеет чтением, проверкой и генерацией."
status: draft
decision_status: proposed
domain: system
related: [GLO-system, VIEW-data, ADR-0001]
implemented: false
---
```

`decision_status: proposed` до подтверждения владельца; после подтверждения — `accepted`, `status: current`, `implemented: true`. Не ставить `accepted` самостоятельно: это `approval_required` в карточке.

Разделы ADR (MADR-подобно, как в существующих ADR):

- **Контекст и проблема:** Markdown не даёт адресуемости, уникальности, схемы, связей; 6 наблюдаемых дефектов из плана родителя.
- **Драйверы:** машиночитаемость, детерминированный поиск, docs-as-code, отсутствие новых зависимостей, совместимость с `index.json`.
- **Рассмотренные варианты:** Markdown (текущий), файл на термин, CSV/XLSX, YAML, JSON, TBX/SKOS. Отметить, почему отклонены: файл на термин — против `manifest.md:482`; CSV — не держит multi-value и плохо диффится; YAML — запрещён `VIEW-data`; TBX/SKOS — только обмен.
- **Итог решения:** JSON-канон, три производных, CLI-граница из §2.2 плана родителя.
- **Последствия:** плюсы (валидация, поиск, связи), минусы (нужен генератор, JSON-diff менее читаем), риски (drift — закрывается `check`).
- **Связь с ADR-0001:** ADR-0001 остаётся в силе для повествовательной архитектуры; меняется только источник данных глоссария. Это надо написать явно, иначе решение выглядит как отмена ADR-0001.
- **Подтверждение:** `arch glossary validate`, `arch glossary check`, `arch index check`, `arch validate --brief`.

## 3. Схема `glossary.schema.json`

Файл: `doc/architecture/schemas/glossary.schema.json`, Draft 2020-12.

Требования к схеме:

- `$id` в стиле существующих схем: `https://example.invalid/simple-factory/glossary.schema.json`.
- `additionalProperties: false` на всех уровнях, кроме `technical_mapping`-строк.
- `schema_version` — `const: 1`.
- `id` — `pattern: "^GLO-[a-z0-9-]+$"`.
- `domain` — `pattern: "^[a-z][a-z0-9-]*$"`.
- `status` документа — `enum: [draft, current, deprecated, superseded]`.
- `terms` — `minItems: 1`, `uniqueItems` не поможет (объекты), уникальность `id` проверяется в коде.

Схема термина:

| Поле | Тип | Ограничение |
|---|---|---|
| `id` | string | `^TERM-[a-z0-9]+(-[a-z0-9]+)+$` (минимум домен + slug) |
| `term` | string | `minLength: 1` |
| `definition` | string | `minLength: 10` |
| `official_synonyms` | array[string] | `uniqueItems`, default `[]` |
| `search_synonyms` | array[string] | `uniqueItems`, default `[]` |
| `avoid` | array[string] | `uniqueItems`, default `[]` |
| `abbreviation` | string \| null | default `null` |
| `examples` | array[string] | default `[]` |
| `technical_mapping` | array[string] | default `[]` |
| `related_terms` | array[string] | `pattern: "^TERM-..."`, default `[]` |
| `status` | string | `enum: [draft, proposed, approved, deprecated, superseded]` |
| `owner` | string \| null | default `null` |
| `since` | string \| null | `format: date` |
| `superseded_by` | string \| null | `pattern: "^TERM-..."` |

Условное правило: если `status` = `superseded`, то `superseded_by` обязателен и не `null`.

Почему `definition` `minLength: 10`: отсекает пустые и однословные заглушки, но не мешает коротким точным определениям.

## 4. Миграция 8 терминов

Исходник: текущий `doc/architecture/glossary.md`. Таблица маппинга (решение по legacy ID — `open_question`, требует подтверждения владельца; до подтверждения использовать колонку «Вариант A» и зафиксировать исключение в ADR):

| Старый ID | Вариант A (переименовать) | Вариант B (исключение) |
|---|---|---|
| `TERM-task-json` | `TERM-system-task-json` | оставить как есть |
| `TERM-task-key` | `TERM-system-task-key` | оставить |
| `TERM-source-adapter` | `TERM-system-source-adapter` | оставить |
| `TERM-agent-skill` | `TERM-system-agent-skill` | оставить |
| `TERM-architecture-delta` | `TERM-system-architecture-delta` | оставить |
| `TERM-task-stage` | `TERM-system-task-stage` | оставить |
| `TERM-verification-evidence` | `TERM-system-verification-evidence` | оставить |
| `TERM-future-code-scanner` | `TERM-system-future-code-scanner` | оставить |

Что заполнить при миграции:

- `term` — текущий H3-заголовок без ID.
- `definition` — текущее поле «Определение».
- `official_synonyms` — из «Синонимы» (например, `task.json` у `TERM-system-task-json`).
- `search_synonyms` — **новое поле**: добавить реальные варианты, которые люди и агенты пишут (`task key`, `ключ задачи`, `номер задачи`). Не дублировать `official_synonyms`.
- `avoid` — из «Избегайте».
- `related_terms` — только `TERM-*`; текущее `Связано: doc/skills/` заменить на `TERM-system-agent-skill` (это путь, а не ID — дефект).
- `status: approved` для всех, `owner` — по домену, `since` — дата миграции.

Внешние ID из «Связано» (`ENT-task-input`, `CAP-task-intake`, `FLOW-create-task`, `DOM-task-intake`, `DOM-task-lifecycle`, `ENT-stage-artifact`, `FLOW-document-session`, `ENT-verification-evidence`, `CAP-single-agent-execution`, `SYS-simple-factory`) **не** переносятся в `related_terms`: это связи с документами, а не терминами. Они переезжают в frontmatter/задачи на шаге `0002`. Это ключевое решение: `related_terms` — только term↔term, иначе поле теряет смысл.

Проверка миграции: ни один термин не потерян (8 → 8), ни одно определение не изменено по смыслу, все внешние ID из старого «Связано» сохранены в списке для `0002`.

## 5. Модуль `doc/tools/arch/glossary.py`

Публичные функции (минимальный контракт, чтобы `0002`/`0003` не зависели от внутренностей):

```python
GLOSSARY_PATH = "doc/architecture/glossary.json"
INDEX_PATH = "doc/architecture/glossary.index.json"
VIEW_PATH = "doc/architecture/glossary.md"
VOCAB_DIR = "doc/config/vocab"

def load(config) -> dict            # читает канон, кэша нет
def normalize(text: str) -> str     # NFC → casefold → ё→е → пунктуация → пробелы
def validate(config) -> list[str]   # схема + инварианты + ссылки; список ошибок
def build(config, dry_run=False) -> dict   # пишет 4 производных атомарно
def check(config) -> list[str]      # сравнение производных с пересборкой в памяти
def term_ids(config) -> set[str]
```

Требования к реализации:

- Загрузка JSON — `json.loads` с `object_pairs_hook`, отвергающим дубли ключей (как `UniqueKeyLoader` для YAML в `project_config.py`). Иначе дубль `id` в объекте молча перезапишется.
- Схема — `jsonschema.Draft202012Validator`, ошибки форматировать как `glossary.json: terms[3].id: <message>`.
- Инварианты — отдельная функция, не в схеме: пересечения массивов, дубли `id`, `superseded_by` на себя, `related_terms` на несуществующий ID.
- Сообщения об ошибках — actionable, с ID и полем, как в `body_validation.py`.
- Запись — только `fs_atomic.atomic_write_text`. Не писать через `Path.write_text`.
- Детерминизм: `json.dumps(..., ensure_ascii=False, sort_keys=True, indent=2) + "\n"`.

## 6. Производные

### 6.1 `glossary.md`

- Frontmatter: `id: GLO-system`, `type: glossary`, `title`, `summary`, `status`, `domain: system`, `related` (существующие ID).
- Тело: H1, вводная строка «сгенерировано из glossary.json, не редактировать», затем H3-записи в формате `### <term> — \`TERM-...\`` и поля `Определение / Официальные синонимы / Поисковые синонимы / Избегайте / Примеры / Техническое отображение / Связанные термины`.
- Сортировка: по `id` (детерминизм важнее алфавита по русскому).
- Этот формат сохраняет совместимость с текущим читателем и с тестом `test_task_identity.py:273` (фраза про `UI-1234`), если она перенесена в определение `TERM-system-task-key`.

### 6.2 `glossary.index.json`

Структура — §4.2 плана родителя. Дополнительно:

- `referenced_by` заполняется только на `0002`, на `0001` — пустой объект `{}`. Это позволяет `build` существовать до появления связей и не делать два формата индекса.
- `anchor` — `term-<id без префикса TERM->`, в нижнем регистре, неразрывные символы → дефис. Anchor нужен только для удобства, ссылки всё равно идут по ID.

### 6.3 `vocab/accept.txt` и `vocab/reject.txt`

- `accept.txt`: по одному на строку — `term`, затем `official_synonyms`. Без `search_synonyms` (иначе Vale начнёт требовать поисковые формы в прозе).
- `reject.txt`: `avoid`.
- Экранирование: Vale трактует строки как regex. Экранировать `.`, `(`, `)`, `[`, `]`, `*`, `+`, `?`, `{`, `}`, `|`, `^`, `$`, `\`.
- Комментарий в начале файла: `# generated from doc/architecture/glossary.json`.

## 7. CLI `arch glossary validate|build|check`

Файл-обёртка: `doc/tools/arch/cli/commands/glossary.py`. Регистрация — в `registry.py` рядом с существующими группами; проверить `arch --help` и `arch glossary --help`.

| Команда | Флаги | Выход |
|---|---|---|
| `validate` | `--json` | `{"ok":true,"code":0,"data":{"terms":8,"errors":[]}}` |
| `build` | `--dry-run`, `--json` | перечень созданных/изменённых файлов |
| `check` | `--json` | пусто при отсутствии drift; список расхождений и exit 1 |

Коды выхода: `0` успех, `1` невалидные данные или drift, `2` ошибка аргументов. Совпадает с `DocOpsError`-конвенцией (`doc_ops.py`).

`check` не пишет: пересобирает производные в памяти и сравнивает байты с файлами на диске. Это единственный способ поймать ручную правку `glossary.md`.

## 8. `paths.yaml`

Добавить в `allowed_paths` (секция архитектуры и конфигурации):

```yaml
- "{architecture}/glossary.json"
- "{architecture}/glossary.index.json"
- "{architecture}/glossary.md"        # уже есть
- "{config}/vocab/accept.txt"
- "{config}/vocab/reject.txt"
```

В `structure_rules.generated_files`:

```yaml
- "{architecture}/glossary.md"
- "{architecture}/glossary.index.json"
- "{config}/vocab/accept.txt"
- "{config}/vocab/reject.txt"
```

В `project.cli.allowed_commands` — все команды глоссария (`glossary validate`, `build`, `check`, `lookup`, `search`, `match`, `query`, `refs`, `scan`, `lint`, `add`, `update`, `deprecate`, `synonym add`, `synonym remove`). `strict_mode: true`, поэтому без этого CLI откажет.

**Не добавлять** `.txt` в `structure_rules.architecture_doc_extensions`: vocab лежит в `doc/config/`, правило для архитектуры не меняется.

## 9. `body_validation.py`

Текущая проверка для `type: glossary` бессмысленна: `has_terms` + мёртвый `term_format`. Варианты:

- **A (рекомендуется):** убрать `"glossary": "glossary.json"` из `BODY_SCHEMA_BY_TYPE` и удалить `schemas/bodies/glossary.json`; реальная валидация — в `glossary.py`. Минус: удаление файла схемы надо согласовать с `paths.yaml`.
- **B:** оставить проверку `has_terms` как sanity-check сгенерированного `glossary.md` и удалить неиспользуемое свойство `term_format`.

Выбрать A: две схемы для одной сущности — источник расхождений. Удаление `bodies/glossary.json` требует убрать строку из `allowed_paths`.

## 10. Тесты (`doc/tools/tests/test_glossary.py`)

Обязательные кейсы:

1. Валидный канон → `validate()` возвращает `[]`.
2. Дубль `id` → ошибка с ID.
3. `official ∩ search` → ошибка с термином и полем.
4. `avoid ∩ term` → ошибка.
5. ID без домена → ошибка формата.
6. `related_terms` на несуществующий ID → ошибка.
7. `superseded` без `superseded_by` → ошибка.
8. `build` создаёт 4 файла; второй `build` идемпотентен побайтно.
9. `check` после ручной правки `glossary.md` → расхождение.
10. `build --dry-run` не пишет ничего (сравнить mtime/байты).

Плюс интеграция в `doc/tests/run.sh` не требуется на этом шаге: сценарии приёмки гоняются в `verification.json` вручную, а `run.sh` покрывает `validate`/`index`/`paths`.

## 11. Порядок выполнения

1. ADR (`decision_status: proposed`).
2. `glossary.schema.json`.
3. `glossary.json`: 8 терминов по таблице маппинга; `referenced_by` ещё нет.
4. `glossary.py`: `load`, `normalize`, `validate`; тесты 1–7.
5. `build` + `glossary.md`, `glossary.index.json`, `vocab/*`; тесты 8–10.
6. `check`.
7. `paths.yaml`, `body_validation.py`, регистрация CLI, карта CLI и правила валидации.
8. `arch glossary validate && arch glossary build && arch glossary check && arch validate --brief && arch index build && arch index check && arch docs paths --check`.
9. Записать CASE-1, CASE-2, CASE-3, CASE-4, CASE-5, CASE-22 в `verification.json`.

## 12. Ловушки

- Записать `glossary.md` до `paths.yaml` — `docs paths --check` упадёт на необъявленном файле. Объявлять пути вместе с генератором, не раньше.
- Забыть `generated_files` — `docs paths --check` не отличит производный файл от мусора.
- Оставить `bodies/glossary.json` и одновременно добавить новую схему — две правды.
- Использовать `sort_keys=True` без `ensure_ascii=False` — кириллица превратится в `\uXXXX`, diff станет нечитаемым.
- Писать файл через `write_text` — нет атомарности, читатель увидит половину.
- Заполнить `referenced_by` вручную — на `0002` он будет перезаписан, а на `0001` даст ложное ощущение связей.
- Перенести внешние ID (`ENT-*`, `FLOW-*`) в `related_terms` — смешает два разных вида связей.
- Поставить `decision_status: accepted` без владельца — нарушение `approval_required`.

## 13. Проверка шага

```bash
arch glossary validate --json
arch glossary build --json
arch glossary check --json
arch validate --brief
arch index build && arch index check
arch docs paths --check
python3 -m pytest doc/tools/tests/test_glossary.py -q
```

Все — exit 0; повторный `build` не меняет байты производных.
