---
id: SPEC-cli-implementation
type: implementation-spec
title: Спецификация реализации Arch CLI
summary: "Сигнатуры функций, структура argparse, обработка ошибок, форматы файлов и процедуры, необходимые для восстановления CLI из документации без исходного кода."
status: draft
domain: system
related: [REG-cli-command-map, VIEW-cli-package, REG-cli-validation-rules, SPEC-cli-implementation]
implemented: false
---

# Спецификация реализации Arch CLI

Эта спецификация описывает, как именно реализовать детерминированный Arch CLI, чтобы система могла быть пересобрана только по архитектурной документации. Все функции, сигнатуры, форматы и коды ошибок заданы здесь достаточно подробно, чтобы реализовать эквивалентный CLI без доступа к исходному коду.

## 1. Точка входа и пакетная структура

### 1.1 Пакет

```
doc/tools/arch/
├── __init__.py        — публичный API, версия 0.2.0 (совпадает с pyproject.toml)
├── __main__.py        — точка входа python -m arch и прямой запуск
├── cli/
│   ├── app.py         — argparse парсер, run(), диспетчеризация
│   ├── errors.py      — CliError, CliEnvelope, семантические exit-коды
│   ├── output.py      — JSON-envelope и human/brief/quiet/verbose вывод
│   └── commands/      — Command-интерфейс, реестр и команды
│       ├── base.py
│       ├── registry.py — реестр отвергает повторную регистрацию имени
│       ├── builtin.py — list/show/index/validate/scan/docs
│       ├── task.py    — parser, dispatch и вывод task/subtask
│       └── task_key.py — task-key
├── constants.py       — regex, имена ключей для YAML, path_is_allowed()
├── identity.py        — task-key derive, task_dir(), parse_task_key()
├── schema.py          — task.json шаблон (draft-0.2), scaffold_task_json()
├── validation.py      — validate_task_json(), task-conf loaders, check_subtasks_closed(), validate_paths()
├── store.py           — ArchitectureStore, Document, UniqueKeyLoader
├── subtask.py         — subtask_dir(), scaffold_subtask_json(), list_stages(), list_sub_subtasks()
├── fs_atomic.py       — атомарная запись файла и журнал составной записи
├── task_ops.py        — lifecycle-сценарии task/subtask без argparse и вывода
├── acceptance.py      — покрытие запланированных кейсов и проверка SHA-256 доказательств
├── evidence.py        — запись результата явной проверки на выбранном снимке
└── body_validation.py — validate_document_body(), get_supported_body_types()
```

### 1.2 Точка входа

- установленный console script `arch` — entry point `arch.cli.app:run` из `pyproject.toml`
- `python3 -m arch` — из директории `doc/tools/`
- `python3 doc/tools/arch/__main__.py` — прямой запуск, работает из любого cwd
- Аргумент `--root <path>` — опционально, проектный корень (по умолчанию: `Path(__file__).resolve().parents[4]` из `cli/app.py`)

## 2. Константы и регулярные выражения (constants.py)

### 2.1 Регулярные выражения

| Константа | Регулярное выражение | Назначение |
|-----------|---------------------|------------|
| `FRONTMATTER` | `r"\A---\r?\n(.*?)\r?\n---\r?\n"` | YAML frontmatter в начале .md файла |
| `LINK` | `r"\[[^\]]*\]\((<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)"` | Markdown ссылки |
| `FENCE` | `r"^\s*(```+|~~~+)"` | Code fence блоки |
| `TASK_NUMBER_RE` | `r"^[0-9]{4}$"` | Ровно четыре десятичные цифры |
| `TASK_PREFIX_RE` | `r"^[A-Z][A-Z0-9]{0,7}$"` | 1-8 заглавных букв/цифр, начинается с буквы |
| `TASK_KEY_RE` | `r"^(?:([0-9]{4})|UI-([0-9]{4})|([A-Z][A-Z0-9]{0,7})-([0-9]{4}))$"` | task_key: Jira bare number, UI-<number>, PREFIX-<number> |
| `FLOW_RE` | `r"^[a-z][a-z0-9-]{1,63}$"` | slug для flujo |

### 2.2 Ключи конфигурации

Все имена ключей для загрузки из YAML (нет хардкода значений):

| Константа | Путь в YAML | Назначение |
|-----------|-------------|------------|
| `PATHS_CONFIG_RELATIVE` | `"doc/config/paths.yaml"` | Относительный путь к конфигу путей |
| `ALLOWED_PATHS_KEY` | `"allowed_paths"` | Допустимые пути в doc/ |
| `PROJECT_KEY` | `"project"` | Секция проекта в paths.yaml |
| `PROJECT_TASK_TYPES_KEY` | `"project.task_types"` | Допустимые task_type |
| `PROJECT_PHASES_KEY` | `"project.phases"` | Допустимые phase |
| `PROJECT_RISK_LEVELS_KEY` | `"project.risk_levels"` | Допустимые уровни риска |
| `PROJECT_SOURCE_TYPES_KEY` | `"project.source_types"` | Допустимые source.type |
| `PROJECT_TASK_SCHEMA_REQUIRED_FIELDS_KEY` | `"project.task_schema_required_fields"` | Базовые обязательные поля task.json |
| `TASK_CONF_TYPES_DIR` | `"doc/config/task-conf/types"` | Директория типов task-conf |
| `TASK_CONF_ID_KEY` | `"id"` | Идентификатор типа/флоу |
| `TASK_CONF_ALLOWED_FLOWS_KEY` | `"allowed_flows"` | Разрешённые flujo для типа |
| `TASK_CONF_DEFAULT_FLOW_KEY` | `"default_flow"` | Default flujo типа |
| `TASK_CONF_SUBTASK_POLICY_KEY` | `"subtask_policy"` | required/optional/forbidden |
| `TASK_CONF_CLOSE_POLICY_KEY` | `"close_policy"` | all_subtasks_required |
| `TASK_CONF_REQUIRED_FIELDS_KEY` | `"required_fields"` | Дополнительные обязательные поля типа |
| `TASK_CONF_COMPLEXITY_ALLOWED_KEY` | `"complexity_allowed"` | Допустимые уровни сложности |
| `TASK_CONF_COMPLEXITY_DEFAULT_KEY` | `"complexity_default"` | Default сложность типа |

### 2.3 Функция path_is_allowed

```python
def path_is_allowed(relative_path: str, allowed_paths: list[str]) -> bool:
    """Проверяет, разрешён ли путь по шаблонам paths.yaml."""
    # Поддерживает {name} сегменты и ** для вложенных директорий
    # Пример: "doc/tasks/{task_key}/task.json" соответствует "doc/tasks/UI-0001/task.json"
```

### 2.4 _glob_match

```python
def _glob_match(pattern: str, path: str) -> bool:
    """Простое соответствие пути шаблону с фигурными скобками."""
    # Экранирует всё кроме {name} и **
    # {name} -> [^/]+
    # ** -> .*
```

## 3. Identity (identity.py)

### 3.1 parse_task_key

```python
def parse_task_key(task_key: str) -> dict:
    """Разбирает task_key на компоненты.
    
    Возвращает: {"task_number": str, "source_type": str, "source_prefix": str | None}
    
    source_type: "jira" | "ui" | "other"
    source_prefix: None для jira, None для ui, префикс для other (например "GH")
    
    Выбрасывает ValueError если task_key не совпадает с TASK_KEY_RE.
    """
```

### 3.2 normalize_task_identity

```python
def normalize_task_identity(source: str, number: str, prefix: str | None) -> dict:
    """Вычисляет task_key из источника, номера и префикса.
    
    source: "jira" | "ui" | "other"
    number: ровно 4 десятичные цифры (валидируется TASK_NUMBER_RE)
    prefix: обязателен для "other", не используется для "jira"/"ui"
    
    Возвращает: {"task_key": str, "task_number": str, "source_type": str, "source_prefix": str | None}
    """
```

### 3.3 task_dir

```python
def task_dir(root: Path, task_key: str) -> Path:
    """Возвращает путь к директории задачи: doc/tasks/<task_key>/"""
    return root / "doc" / "tasks" / task_key
```

## 4. Schema (schema.py)

### 4.1 TASK_DIR_TEMPLATE

```python
TASK_DIR_TEMPLATE = "doc/tasks/{task_key}/"
```

### 4.2 scaffold_task_json

```python
def scaffold_task_json(task_key: str, task_number: str, source_type: str, source_prefix: str | None) -> str:
    """Генерирует JSON строку scaffold task.json (draft-0.2).
    
    Включает все базовые поля из paths.yaml task_schema_required_fields
    с пустыми/unset значениями.
    """
```

## 5. Validation (validation.py)

### 5.1 validate_task_json

```python
def validate_task_json(data: dict, task_key: str, root: Path | None = None) -> list[str]:
    """Валидирует распарсенную структуру task.json.
    
    Возвращает список человекочитаемых сообщений об ошибках (пустой список = валидно).
    
    Все правила загружаются из YAML конфигов:
      - doc/config/paths.yaml (project секция): task_types, phases, risk_levels, source_types, task_schema_required_fields
      - doc/config/task-conf/types/<type>/config.yaml: required_fields, allowed_flows, complexity_allowed, subtask_policy, close_policy
    
    Нет хардкода enum'ов в Python коде.
    """
```

### 5.2 load_task_conf_types

```python
def load_task_conf_types(root: Path) -> tuple[dict[str, Any], list[str]]:
    """Загружает все конфиги типов из doc/config/task-conf/types/*/config.yaml.
    
    Возвращает: ({type_id: conf_with_flows}, errors)
    Каждый conf включает поле "flows" — словарь {flow_id: flow_conf}.
    """
```

### 5.3 load_task_conf_flows_for_type

```python
def load_task_conf_flows_for_type(root: Path, type_id: str) -> tuple[dict[str, Any], list[str]]:
    """Загружает конфиги flujo для конкретного типа.
    
    Возвращает: ({flow_id: conf}, errors)
    """
```

### 5.4 load_task_conf_prompt

```python
def load_task_conf_prompt(root: Path, type_id: str) -> tuple[str | None, list[str]]:
    """Загружает стартовый промпт типа из types/<type>/prompt.md."""
```

### 5.5 load_task_conf_flow_prompt

```python
def load_task_conf_flow_prompt(root: Path, type_id: str, flow_id: str) -> tuple[str | None, list[str]]:
    """Загружает стартовый промпт flujo из types/<type>/flows/<flow>/prompt.md."""
```

### 5.6 check_subtasks_closed

```python
def check_subtasks_closed(root: Path, task_key: str) -> tuple[bool, list[str]]:
    """Проверяет, все ли subtasks задачи имеют phase: completed.
    
    Возвращает: (all_closed, errors)
    """
```

### 5.7 load_paths_config

```python
def load_paths_config(root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """Загружает doc/config/paths.yaml."""
```

### 5.8 validate_paths

```python
def validate_paths(root: Path) -> list[str]:
    """Валидирует doc/ против declared paths в paths.yaml.
    
    Проверки:
      1. Каждый файл под doc/ соответствует хотя бы одному шаблону allowed_paths
      2. Каждый точный declared path (без { }) существует на диске
      3. .md файлы под doc/architecture/ имеют валидный YAML frontmatter с обязательными полями (id, type, title, summary, status)
      4. document type и status входят в допустимые из paths.yaml project секции
    
    Возвращает список ошибок (пустой = валидно).
    """
```

## 6. Store (store.py)

### 6.1 ArchitectureStore

```python
class ArchitectureStore:
    def __init__(self, root: Path):
    
    def load_documents(self) -> tuple[list[Document], list[str]]:
        """Загружает все документы doc/architecture/ с frontmatter."""
    
    def build_index(self) -> tuple[dict, list[str]]:
        """Строит сгенерированный index.json."""
    
    def write_index(self, index: dict) -> None:
        """Атомарно записывает index.json."""
    
    def validate(self, check_index: bool = False) -> list[str]:
        """Валидирует все frontmatter, refs и опционально индекс."""
```

### 6.2 Document

```python
class Document:
    id: str
    metadata: dict
    body: str
    relative_path: str
```

### 6.3 UniqueKeyLoader

YAML loader который отслеживает дублирующиеся ключи и бросает ошибку при их 발견е.

## 7. Subtask (subtask.py)

### 7.1 subtask_dir

```python
def subtask_dir(root: Path, parent_task_key: str, subtask_id: str) -> Path:
    """Возвращает путь: doc/tasks/<parent_task_key>/subtasks/<subtask_id>/
```

### 7.2 scaffold_subtask_json

```python
def scaffold_subtask_json(parent_task_key: str, subtask_id: str, title: str = "") -> str:
    """Генерирует JSON scaffold для subtask task.json."""
```

### 7.3 list_stages

```python
def list_stages(directory: Path) -> list[str]:
    """Возвращает список stageN директорий."""
```

### 7.4 list_sub_subtasks

```python
def list_sub_subtasks(directory: Path) -> list[str]:
    """Возвращает список вложенных subtask директорий."""
```

## 8. Body Validation (body_validation.py)

### 8.1 validate_document_body

```python
def validate_document_body(doc_type: str, body: str) -> list[str]:
    """Валидирует тело документа по JSON Schema для данного типа."""
```

### 8.2 get_supported_body_types

```python
def get_supported_body_types() -> list[str]:
    """Возвращает список типов документов с поддерживаемой body валидацией."""
```

## 9. CLI (cli.py)

### 9.1 build_parser

```python
def build_parser() -> argparse.ArgumentParser:
    """Строит argparse парсер из зарегистрированных команд реестра."""
```

### 9.2 run

```python
def run(argv: list[str] | None = None) -> int:
    """Главная точка входа CLI.

    Возвращает семантический exit code:
      0 — успех
      1 — ошибка валидации/индекса
      2 — ошибка аргументов
      5 — конфликт
      10 — ошибка авторизации
      20 — не найдено
      75 — временная ошибка
    """
```

### 9.3 Команда task types

```
arch task types [--json]
```

- Читает task-conf/types/*/config.yaml
- Выводит для каждого типа: id, title, default_flow, subtask_policy, close_policy, flow_count, allowed_flows
- JSON output если --json

### 9.4 Команда task flows --type

```
arch task flows --type <type> [--json]
```

- Читает task-conf/types/<type>/allowed_flows
- Выводит список flujo с title и description

### 9.5 Команда task type-prompt --type

```
arch task type-prompt --type <type>
```

- Читает types/<type>/prompt.md
- Выводит содержимое на stdout

### 9.6 Команда task flow-prompt --type --flow

```
arch task flow-prompt --type <type> --flow <flow>
```

- Читает types/<type>/flows/<flow>/prompt.md
- Выводит содержимое на stdout

### 9.7 Команда task init

```
arch task init <task_key>
```

- Создаёт doc/tasks/<task_key>/ с task.json и stage1/
- Валидирует task_key через TASK_KEY_RE
- Не аллоцирует task_number (берется из task_key)
- Отказывает если директория уже существует

### 9.8 Команда task validate

```
arch task validate <task_key>
```

- Читает doc/tasks/<task_key>/task.json
- Вызывает validate_task_json()
- Проверяет отсутствие task.md рядом с task.json
- Выводит "task <key> is valid" или список ошибок

### 9.9 Команда task workspace

```
arch task workspace <task_key>
```

- Читает task.json, валидирует
- Выводит target_release, branch_hint, directory, task_json пути
- branch_hint: "futures/<number>" для jira, "bugfix/<key>" для других

### 9.10 Команда task status

```
arch task status <task_key>
```

- Читает task.json
- Выводит stage list, verification файлы, task_type, flow, complexity, phase, target_release

### 9.11 Команда task decompose

```
arch task decompose <task_key> --subtask-id NNNN --subtask-title "..." [--subtask-id NNNN --subtask-title "..." ...]
```

- Читает родительский task.json; требует, чтобы `subtasks` был массивом, а `task.md` отсутствовал. Остальные поля родителя проверяет `task validate`, чтобы decompose не блокировал первый пакет из-за ещё не заполненных семантических полей
- Проверяет весь пакет до записи: `--subtask-id` и `--subtask-title` в равном количестве, ID из четырёх цифр и уникальны внутри пакета, заголовки непустые, ID не объявлены в родителе, каталоги ещё не существуют
- При любой ошибке пакета не создаёт каталогов и не меняет родителя
- Создаёт `subtasks/<id>/` с `task.json` и `stage1/`, затем добавляет запись в `subtasks` родителя
- Одиночные записи заменяются атомарно; перед составной записью создаётся журнал `.arch-write-journal.json`, который удаляется последним
- Повторный вызов с тем же пакетом при наличии журнала возобновляет запись; другой пакет даёт конфликт

### 9.12 Команда task diagnose

```
arch task diagnose <task_key> [--json] [--brief]
```

- Проверяет карточку и объединение объявленных детей с непосредственными каталогами. `can_close` отражает машинные предусловия.
- Разрешает `depends_on` через настроенный корень задач, включая ключи детей. `dependencies` содержит `task_key`, `required_by`, `state` и доступную фазу. Краткий режим ограничивает список тремя строками. Эти же зависимости применяет `close`.
- При `acceptance_policy: case-coverage-v1` сверяет связанные кейсы и хеши заявленных входов. `acceptance_plan_ready` сообщает о структурной готовности текущей стадии. Формат и правила описаны в [записи доказательств](../domains/task-lifecycle/entities/verification-evidence.md).
- Полный ответ включает сведения о детях и блокировки. `--brief` сохраняет счётчики, показывает до трёх блокировок и возвращает `refs` к карточке и существующим артефактам последней по номеру стадии.

### 9.13 Команда task close

```
arch task close <task_key> [--json] [--dry-run]
```

- Использует предусловия `diagnose`. При `--dry-run` возвращает `would_close` и блокировки без записи.
- Отказ по предусловиям — exit 1 и JSON envelope в stderr при `--json`. Карточка сохраняется.
- При успешном закрытии устанавливает `phase: completed` атомарной заменой файла. Агент до вызова проверяет приёмку и применимое одобрение.

### 9.14 Устойчивая запись и восстановление

- `fs_atomic.atomic_write_text` пишет временный файл в каталоге цели, вызывает `fsync` и заменяет цель через `os.replace`. При исключении временный файл удаляется. Завершение процесса до замены может оставить файл из зарезервированного пространства имён `.<имя-цели>.<суффикс>.tmp`.
- `decompose`, фактический `close` и `subtask init` под одним родителем используют неблокирующий advisory `flock` каталога задачи. Занятый писатель даёт exit 5 до записи. Гарантия относится к этим операциям CLI на поддерживающей `flock` локальной POSIX ФС. Для восстановления проверяется прерывание процесса. Сохранность после отключения питания и координация прямого редактирования файлов находятся за этой границей.
- Составная запись публикует `.arch-write-journal.json` со `schema_version: 1`, `kind: decompose`, `task_key` и упорядоченным пакетом `subtasks: [{id, title}]`. Родитель дополняется после детей, временные остатки убираются перед удалением журнала.

| Состояние | Поведение CLI |
|---|---|
| Журнал отсутствует | Проверяются все ID, заголовки и коллизии. Файлы создаются только после полного preflight. |
| Журнал повреждён или недоступен для чтения | `diagnose` и `status` возвращают `incomplete_write.state: invalid`; `scan --scope tasks` сообщает причину. Preview закрытия возвращает `would_close: false`, фактическое закрытие блокируется. Операции записи сохраняют дерево. Оператор сверяет журнал и записи до восстановления. |
| Журнал валиден, пакет отличается или существующие записи конфликтуют | Exit 5. Родитель, дети, журнал и временные файлы сохраняются. При повторе весь пакет проверяется до первой записи или уборки. |
| Журнал валиден, пакет совпадает | Сверяются ключ и заголовок ребёнка, а для объявленного ребёнка также заголовок и путь в родителе. Частичный каталог может содержать `stage1` и обычные временные файлы записи `task.json` из зарезервированного пространства имён. Недостающая запись восстанавливается. Повтор после записи родителя удаляет журнал без повторной записи родителя. |
| Журнал валиден, вызван `close` или `subtask init` | Запись блокируется. Возобновите `decompose` с тем же пакетом. |

### 9.15 Команда task subtask

```
arch task subtask init <parent_key> <subtask_id>
arch task subtask validate <parent_key> <subtask_id>
arch task subtask status <parent_key> <subtask_id>
```

- init: создаёт subtask директорию с task.json
- validate: валидирует subtask task.json через validate_task_json()
- status: показывает phase, task_type, flow, stages

### 9.16 Команда docs paths --check

```
arch docs paths --check
```

- Вызывает validate_paths()
- Выводит "All doc/ paths are declared and valid" или список ошибок

### 9.17 Команда task-key

```
arch task-key --source <source> --number <number> [--prefix <prefix>]
```

- Вызывает normalize_task_identity()
- Выводит JSON с task_key, task_number, source_type, source_prefix

### 9.18 Команда validate (архитектура)

```
arch validate [--json]
```

- Вызывает store.validate(check_index=True)
- Проверяет все frontmatter, refs, ID, индекс

### 9.19 Команда docs related

```
arch docs related <id> [--depth N]
```

- Строит граф связанных документов начиная с id
- Обход по metadata.related до глубины depth

### 9.20 Команды list/show/index

| Команда | Описание |
|---------|----------|
| `arch list [--id ID ...] [--type] [--domain] [--status] [--json]` | Метаданные и путь без тела. Повторные ID объединяются, фильтры по типу, домену и статусу пересекаются с ними. При отсутствии совпадений возвращается пустой список с exit 0. |
| `arch docs tree` | JSON envelope с `architecture_root` относительно проекта, опциональным `guide` и `tree`. Каждый узел содержит `directories` по имени и массив `documents` с `id`, `title`, `type`, `status`, `path`. Путь документа относителен к архитектуре, тело выдаёт `arch show <id>`. |
| `arch task flow-steps --type <type> --flow <flow>` | JSON envelope с `type`, `flow`, `steps`. Массив сохраняет порядок YAML. Каждый элемент содержит `id`, доступные метаданные шага и проектно-относительный `prompt_path`. |
| `arch task flow-prompt --type <type> --flow <flow> [--step <id>]` | Без `--step` возвращает общий Markdown. Для объявленного шага читает `stepsprompt/<id>.md` или выделяет его пронумерованный пункт из общего промпта. Неизвестный или отсутствующий промпт даёт exit 20. |
| `arch show <id> [--format markdown\|json]` | Один документ по точному ID |
| `arch index build` | Построить index.json |
| `arch index check` | Проверить актуальность индекса |

### 9.21 Формат вывода

- JSON в stdout для структурированных команд (indent=2, ensure_ascii=False)
- Текст в stdout для читаемых команд (list, show markdown, validate без --json)
- Всё диагностическое (прогресс, предупреждения, ошибки) — в stderr
- `--quiet` — только голые значения без обёртки
- `--brief` — сокращённый текстовый режим
- `--fields` — выбор подмножества полей JSON

### 9.22 Exit-коды

| Код | Смысл |
|-----|-------|
| 0 | Успех |
| 1 | Ошибка валидации/индекса |
| 2 | Ошибка аргументов / неизвестная команда |
| 5 | Конфликт (например, существующая директория) |
| 10 | Ошибка авторизации |
| 20 | Объект не найден |
| 75 | Временная ошибка |

### 9.23 Обработка ошибок

Все доменные модули возвращают списки строк ошибок или выбрасывают `ValueError`/`OSError`. `cli.main()` конвертирует их в exit code 1 с сообщением `ERROR: <текст>` на stderr.

Каждая ошибка валидации содержит:
- Поле, вызвавшее ошибку (где применимо)
- Ожидаемое vs фактическое значение
- Предложение по исправлению (suggestion)

### 9.24 Команда session (аудит Kilo)

```
arch session find --match <text> [--db <path>] [--directory <dir>] [--all-projects] [--role any|user|assistant] [--limit N] [--json]
arch session digest <session_id> [--db <path>] [--match <text>] [--max-events N] [--full-text] [--no-children]
arch session events <session_id> [--db <path>] [--message <id>] [--part <id>] [--offset N] [--limit N] [--full]
```

- Модуль `session_audit.py` открывает базу через `mode=ro` и `PRAGMA query_only=ON`; путь берётся из `--db`, затем `KILO_AUDIT_DB`, затем `~/.local/share/kilo/kilo.db`.
- `find` ищет подстроку в `part.data.text`, исключает synthetic/ignored части и ограничивает область каталогом проекта либо `--all-projects`. Возвращает `match_count`, `matched_message_ids`, первое совпадение и сниппет.
- `digest` возвращает `schema: kilo-session-digest-v1`: `session`, `dialog`, `stats.tools`, `stats.activities`, `tool_calls`, `markers`, `timeline`, `timeline_omitted`, `label_index`, `phases`, `anomalies`, `drill`. `tool_calls` содержит полный компактный список вызовов и не обрезается вместе с `timeline`. Метки выводятся из путей и команд детерминированно: `skill:`, `rule:`, `flow:`, `flow-step:`, `type:`, `task:`, `subtask:`, `stage:`, `arch:`, `arch-flow:`, `cli:`, `test:`, `ref:`.
- `timeline` ограничивается `--max-events` (по умолчанию 1000), сохраняя начало и конец и вставляя событие `omitted`. `label_index` хранит до 20 ссылок на метку.
- `events` фильтрует части по `--message`/`--part`, поддерживает `--offset`/`--limit` и по умолчанию обрезает текст и вывод до 4000 символов; `--full` отключает обрезку.
- Исход вызова: `failure` при `state.status` в `error`/`failed` или ненулевом `metadata.exit`; `success` при `completed`; иначе `unknown`. Токены суммируются по assistant-сообщениям.
- Команда read-only: не пишет в базу, task records и рабочее дерево. Смысловая оценка сессии остаётся у агента.

## 10. Форматы файлов

### 10.1 task.json (draft-0.2)

См. `doc/architecture/system/cli-validation-rules.md` для полного перечня полей и ограничений.

Базовые обязательные поля (из paths.yaml project.task_schema_required_fields):
- schema_version, task_key, task_number, source, title, kind, intent, scope, acceptance_criteria, target_release, project_context_refs, constraints, assumptions, open_questions, risk, authority, approvals, task_type, flow, complexity, subtasks, depends_on, phase, rollback_plan, related_docs, related_tests, research_docs, changed_files, owner, priority, stage_history

Типовые обязательные поля (из task-conf/types/<type>/config.yaml required_fields) добавляются к базовым.

### 10.2 task-conf/types/<type>/config.yaml

| Поле | Тип | Описание |
|------|-----|----------|
| id | строка | Идентификатор типа (должен совпадать с именем папки) |
| title | строка | Человекочитаемое название |
| description | строка | Описание типа |
| complexity_default | строка | Default уровень сложности |
| complexity_allowed | список строк | Допустимые уровни сложности |
| allowed_flows | список строк | Разрешённые flujo |
| default_flow | строка | Default flujo |
| subtask_policy | строка | required/optional/forbidden |
| close_policy | строка | all_subtasks_required |
| required_fields | список строк | Дополнительные обязательные поля task.json |
| forbidden_in_scope | список строк | Запрещённые элементы в scope |

### 10.3 task-conf/types/<type>/prompt.md

Стартовый промпт типа, читаемый при начале работы над задачей этого типа.

### 10.4 task-conf/types/<type>/flows/<flow>/config.yaml

| Поле | Тип | Описание |
|------|-----|----------|
| id | строка | Идентификатор flujo |
| title | строка | Название flujo |
| type | строка | Ссылка на родительский тип |
| description | строка | Описание flujo |
| subtask_policy | строка | required/optional/forbidden |
| close_policy | строка | all_subtasks_required |
| steps | список | Шаги с id, name, action, output, gate |

### 10.5 task-conf/types/<type>/flows/<flow>/prompt.md

Стартовый промпт flujo, регламентирующий выполнение задачи этого типа и этого flujo.

### 10.6 Frontmell для .md файлов doc/architecture/

Обязательные поля: id, type, title, summary, status.

Допустимые type: из paths.yaml project.document_types.
Допустимые status: из paths.yaml project.document_statuses.

### 10.7 index.json

Сгенерированный файл, never edit manually. Содержит документы с метаданными из frontmatter.

## 11. Конфигурация paths.yaml

### 11.1 Структура

```yaml
version: "1.0"
doc_root: "doc"

allowed_paths:
  - "doc/AGENTS.md"
  - "doc/architecture/README.md"
  # ... все допустимые пути

project:
  id_formats:
    task_key: "^(?:[0-9]{4}\|UI-[0-9]{4}\|[A-Z][A-Z0-9]{0,7}-[0-9]{4})$"
    document_id: "^[A-Za-z][A-Za-z0-9._:-]*$"
    subtask_id: "^[0-9]{4}$"
  document_types: [...]
  document_statuses: [...]
  task_types: [...]
  phases: [...]
  risk_levels: [...]
  source_types: [...]
  task_schema_required_fields: [...]
  cli:
    allowed_commands: [...]
    strict_mode: true
    garbage_detector: true
  structure_rules:
    only_declared_paths: true
    architecture_doc_extensions: [".md", ".json"]
    frontmatter_required_for: ["doc/architecture/**/*.md"]
    generated_files: ["doc/architecture/index.json"]
```

### 11.2 Шаблоны путей task-conf

```
doc/config/task-conf/types/{type}/config.yaml
doc/config/task-conf/types/{type}/prompt.md
doc/config/task-conf/types/{type}/flows/{flow}/config.yaml
doc/config/task-conf/types/{type}/flows/{flow}/prompt.md
```

### 11.3 Шаблоны путей задач

```
doc/tasks/{task_key}/task.json
doc/tasks/{task_key}/stage{stage}/plan.md
doc/tasks/{task_key}/stage{stage}/verification.json
doc/tasks/{task_key}/subtasks/{subtask_id}/task.json
doc/tasks/{task_key}/subtasks/{subtask_id}/stage{stage}/plan.md
doc/tasks/{task_key}/subtasks/{subtask_id}/stage{stage}/verification.json
doc/tasks/{task_key}/research/{slug}.md
```

## 12. Dependencies

```text
PyYAML >= 6.0
jsonschema >= 4.0
```

Устанавливаются из `doc/tools/requirements.txt`.

## 13. Технологические решения (не выбор библиотеки)

- Python 3.13+ для CLI
- argparse для парсинга команд
- YAML для конфигурации (paths.yaml, task-conf)
- JSON для task.json, index.json, verification.json
- Git для версионирования документов
- Без автоматического выделения task_number ( пользователь или allocator)
- Без task.md (task.json единственный canonical input)
- Без семантических решений в CLI (только детерминированная валидация)
