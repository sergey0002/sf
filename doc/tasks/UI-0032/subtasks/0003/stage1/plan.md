<!-- plan-tier: standard -->
# UI-0032-0003: Скилл, каталог правил и архитектурные записи

Карточка: [task.json](../task.json). Родитель: [UI-0032](../../../task.json), AC-9. Зависит от [0002](../0002/task.json). Стадия `stage1`.

## Цель и границы

- Текущее поведение: `doc/skills/plan-task/SKILL.md:21-50` задаёт таблицу tier'ов как единственный источник; архитектурные записи не упоминают политику типа, каталог правил и `plan-policy`.
- Требуемое поведение: скилл получает политику и правила командой, открывает один шаблон по её пути; пять архитектурных записей описывают конфигурацию, слияние, правила и проверки.
- Сохраняется: существующие планы и доказательства, смысловые разделы документов вне политики.
- Не входит: код, конфиги, шаблоны, файлы новых типов.

## Правила проекта

| ID или путь | Правило | AC или CASE |
|---|---|---|
| `doc/skills/plan-task/SKILL.md:21-50` | Tier и правило одного шаблона | AC-1, CASE-1 |
| `ENT-verification-evidence:48` | Контракт tier'ов | AC-2, CASE-2 |
| `SPEC-cli-implementation:466` | Описание `acceptance_plan_ready` | AC-2, CASE-2 |
| `REG-cli-command-map:32-39` | Карта команд | AC-2, CASE-2 |
| `REG-cli-validation-rules:23` | Правила task-conf | AC-2, CASE-2 |
| `VIEW-cli-package:75` | Конфиг-driven валидация | AC-2, CASE-2 |
| `ADR-0001` | Индекс производный, пересобирается CLI | AC-3, CASE-3 |
| `data/sdd-research/06-...` §3 | Правило проверяемо или остаётся смысловым | AC-1, CASE-1 |

## Решения и порядок

Скилл остаётся описанием процесса, но значения и правила получает из `plan-policy`; глобальная таблица помечается как дефолт. Каталог правил описывается с kind'ами и границей: что проверяет CLI и что оценивает агент. Политика объявляется типом, не flow. Документы обновляются точечно, без переписывания смысловых разделов. Раздел выбора типа ребёнка в `plan-task` принадлежит UI-0030-0002; здесь меняется только маршрутизация tier'ов и правил. Индекс пересобирается через CLI после правок frontmatter.

## Артефакты

| Путь | Действие |
|---|---|
| `doc/skills/plan-task/SKILL.md` | изменить |
| `doc/architecture/domains/task-lifecycle/entities/verification-evidence.md` | изменить |
| `doc/architecture/system/implementation-spec.md` | изменить |
| `doc/architecture/system/cli-validation-rules.md` | изменить |
| `doc/architecture/system/cli-command-map.md` | изменить |
| `doc/architecture/system/cli-package.md` | изменить |

## Источники

- `doc/skills/plan-task/SKILL.md` — текущая таблица tier'ов и правило одного шаблона.
- `doc/architecture/domains/task-lifecycle/entities/verification-evidence.md` — контракт tier'ов.
- `doc/architecture/system/cli-command-map.md`, `cli-validation-rules.md`, `cli-package.md` — карта команд и принципы валидации.
- `doc/tasks/UI-0032/research/plan-policy-and-type-taxonomy.md` — каталог правил и таксономия.

## Затронутые документы

- `doc/skills/plan-task/SKILL.md` — маршрутизация через `plan-policy` и правила приёмки.
- `doc/architecture/domains/task-lifecycle/entities/verification-evidence.md` — источник политики.
- `doc/architecture/system/implementation-spec.md` — описание `acceptance_plan_ready`.
- `doc/architecture/system/cli-validation-rules.md` — проверки task-conf.
- `doc/architecture/system/cli-command-map.md` — команда `plan-policy`.
- `doc/architecture/system/cli-package.md` — конфиг-driven перечень.

## Проверка путей и ссылок

```bash
arch validate --brief
arch index check
arch docs paths --check
```

- Каждая новая ссылка указывает на существующий ID или путь; индекс пересобирается только через CLI.
- Противоречия с новым контрактом удаляются, а не дублируются: жёсткое соответствие tier→complexity заменяется ссылкой на политику.

## Риски

- Документация может разойтись с кодом при последующих правках: контроль — `validate` и чтение разрешённой политики.
- Смысловые разделы вне политики легко затронуть: правки точечные, diff проверяется владельцем.


## Приёмка

| CASE | AC | Дано | Действие | Ожидание и проверка | Ребёнок |
|---|---|---|---|---|---|
| CASE-1 | AC-1 | Обновлённый скилл | Прочитать маршрут и сверить с `arch task plan-policy` | Скилл определяет тип, получает политику и правила, открывает один шаблон по её пути; глобальная таблица помечена как дефолт | нет |
| CASE-2 | AC-2 | Пять архитектурных записей | Прочитать разделы о политике, правилах и команде | Описаны дефолты, схема, блок `plan`, разрешение `type → defaults`, слияние, `plan_policy`, каталог правил, `plan-policy`, обнаружение типов и проверки | нет |
| CASE-3 | AC-3 | Итоговое дерево | `arch validate --brief`; `arch index check`; `arch docs paths --check`; `arch task diagnose UI-0031 --json --brief` | Все команды exit 0; UI-0031 остаётся готовым без правок | нет |

## Оценка

8 ч, `medium`: скилл 3 ч, каталог правил 2 ч, пять записей 2 ч, индекс и проверки 1 ч. Подзадач нет: один проверяемый документационный результат.

## Проверка

```bash
arch validate --brief
arch index check
arch docs paths --check
arch task diagnose UI-0031 --json --brief
```

- Ожидание: exit 0; UI-0031 остаётся готовым.
- Откат: вернуть скилл и пять записей к снимку, пересобрать индекс.
