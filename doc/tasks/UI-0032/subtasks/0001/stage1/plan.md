<!-- plan-tier: standard -->
# UI-0032-0001: Схема, дефолты, правила и шаблоны всех типов

Карточка: [task.json](../task.json). Родитель: [UI-0032](../../../task.json), AC-1, AC-2, AC-3, AC-7, AC-8 и каталог правил из AC-5. Стадия `stage1`.

## Цель и границы

- Текущее поведение: tier'ы, разделы и лимит заданы константами в `doc/tools/arch/acceptance.py:15-27`; в task-conf нет дефолтов, каталога правил, блока `plan` и шаблонов; каталог без `config.yaml` пропускается молча.
- Требуемое поведение: `plan-defaults.yaml` воспроизводит текущие tier'ы и объявляет каталог правил, `task-conf.schema.json` задаёт единую форму, все десять типов объявляют свои разделы, шаблоны и правила, обнаружение типов и сверка с `paths.yaml` не пропускают ошибки.
- Сохраняется: имена tier'ов, маркер `<!-- plan-tier: ... -->`, поведение карточек без блока `plan`, незакоммиченный срез UI-0031 в `paths.yaml`, legacy-чтение `subtask`.
- Не входит: резолвер и оценщик правил, команда `plan-policy`, правки `acceptance.py`/`task_ops.py`, скилл, архитектурные записи, файлы новых типов.

## Правила проекта

| ID или путь | Правило | AC или CASE |
|---|---|---|
| `VIEW-cli-package:75` | Правила читаются из YAML, не из кода | AC-1, AC-2 |
| `ENT-verification-evidence:48` | Имена tier'ов, маркер и обязательность при `estimate_hours` сохраняются | AC-1 |
| `doc/tools/arch/flows.py:72-95` | YAML проверяется общей JSON Schema из `config.schemas_root` | AC-1, AC-2, AC-5 |
| `doc/config/paths.yaml:107-113,120-136,242-252` | Разрешённые пути и `task_types` перечислены поимённо | AC-4, AC-5 |
| `ARCH-contract` | task-conf — единственный источник правил типа | AC-2, AC-5 |
| UI-0030, «Один источник политики» | Политика объявляется типом, не flow | AC-2 |
| `data/sdd-research/06-...` | Требование без метода верификации — пожелание | AC-1, AC-2 |

## Решения и порядок

Сначала единая схема, затем дефолты и каталог правил, затем конфиги десяти типов и 27 шаблонов, затем обнаружение типов, пути и проверки. Списки в политике заменяются целиком. Шаблон — отдельный Markdown-файл. Схема использует `additionalProperties: true`, чтобы UI-0030 добавил `children_policy`/`parent_policy`. Каталог правил ограничен kind'ами `section_present`, `section_min_items`, `link_min`, `table_column`, `case_min`, `command`; неизвестный kind отвергается.

Порядок: схема → дефолты и каталог → десять конфигов → 27 шаблонов → обнаружение и сверка → пути → тесты.

## Артефакты

| Путь | Действие |
|---|---|
| `doc/architecture/schemas/task-conf.schema.json` | создать |
| `doc/config/task-conf/plan-defaults.yaml` | создать |
| `doc/config/task-conf/types/<type>/config.yaml` | изменить (10 типов) |
| `doc/config/task-conf/types/<type>/plan/<tier>.md` | создать (27 файлов) |
| `doc/config/paths.yaml` | изменить поверх среза UI-0031 |
| `doc/tools/arch/validation.py`, `doc/tools/arch/cli/commands/builtin.py` | изменить |
| `doc/tests/test_plan_policy.py` | создать |

## Приёмка

| CASE | AC | Дано | Действие | Ожидание и проверка | Ребёнок |
|---|---|---|---|---|---|
| CASE-1 | AC-1 | `plan-defaults.yaml` | Валидировать по схеме и сравнить значения с текущими константами | Схема валидна; complexity, разделы, лимит micro 60 и каталог правил корректны | нет |
| CASE-2 | AC-2 | Десять конфигов типов | Валидировать по схеме и прочитать блоки `plan`/`acceptance` | Все валидны; профильные типы отличаются от дефолта; scaffold только micro; subtask legacy | нет |
| CASE-3 | AC-3 | 27 шаблонов | Сопоставить заголовки шаблонов с `required_sections` | Каждый разрешённый tier имеет непустой шаблон со всеми разделами | нет |
| CASE-4 | AC-4 | Обновлённый `paths.yaml` | `arch docs paths --check`; `arch scan --scope paths` | Exit 0; новые файлы не помечены мусором; срез UI-0031 сохранён | нет |
| CASE-5 | AC-5 | Негативные фикстуры схемы, шаблона, complexity, дубля, лимита и правила | `arch validate --brief`; `arch scan --scope task-conf` | Каждая фикстура даёт диагностику с путём и полем; текущее дерево проходит | нет |
| CASE-6 | AC-6 | Временный каталог без `config.yaml`; `id` не равен каталогу; тип только в `paths.yaml`; каталог без записи; карточка удалённого типа | `arch scan --scope task-conf`; `arch validate --brief` | Каждый случай диагностируется без изменения дерева; карточка типа вне `paths.yaml` отвергается | нет |

## Оценка

24 ч, `medium`: схема и каталог правил 5 ч, дефолты 2 ч, десять конфигов 4 ч, 27 шаблонов 7 ч, обнаружение и сверка 3 ч, пути и тесты 3 ч. Подзадач нет: один проверяемый результат конфигурационного слоя.

## Проверка

```bash
python3 -m unittest doc.tests.test_plan_policy -q -k config
arch scan --scope task-conf
arch validate --brief
arch docs paths --check
```

- Ожидание: exit 0; негативные фикстуры дают ненулевой код.
- Откат: удалить новые файлы, вернуть десять конфигов, `paths.yaml`, `validation.py`, `builtin.py` и тесты к снимку, сохранив срез UI-0031.
