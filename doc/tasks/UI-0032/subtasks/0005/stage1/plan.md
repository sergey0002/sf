<!-- plan-tier: standard -->
# UI-0032-0005: Таксономия типов: фаза 1 и решение по фазе 2

Карточка: [task.json](../task.json). Родитель: [UI-0032](../../../task.json), AC-10. Зависит от [0001](../0001/task.json) и [0002](../0002/task.json). Стадия `stage1`.

## Цель и границы

- Текущее поведение: таксономия из десяти типов без критерия добавления; типы выбираются по названию активности.
- Требуемое поведение: критерий «отдельный оракул + отдельные разделы» зафиксирован; фаза 1 (`spike`, `migration`, `incident`) реализована и проходит те же проверки; фаза 2 имеет решение без реализации; отклонённые кандидаты перечислены с причиной.
- Сохраняется: существующие десять типов, их flow и карточки.
- Не входит: реализация `release`, `security`, `decision`; `chore`, `test`, `experiment`, `epic`, `retrospective`, `impediment`.

## Вопросы и метод

- Вопрос: какие типы дают отдельный проверяемый результат и не дублируют существующие?
- Метод: сравнение оракулов и обязательных разделов по исследованию [plan-policy-and-type-taxonomy](../../../research/plan-policy-and-type-taxonomy.md); проверка каждого кандидата на отдельный оракул.
- Источники: `data/sdd-research/05-шаблоны.md`, `06-качество-и-трассируемость.md`; `data/sdd-encyclopedia/Сущности/{Research,ADR,План,Спецификация}.md`; `data/machinedocs-encyclopedia/Практики/{Сквозной цикл разработки,Инструменты аудита для software factory}.md`; внешние практики ticket types, GitLab/IBM/Azure work items, taxonomy compose, IEEE SWEBOK.

## Варианты и критерии

| Вариант | Оракул | Решение |
|---|---|---|
| Добавить `spike` | decision: вопрос и следующий шаг | Фаза 1 |
| Добавить `migration` | integrity: целостность, повтор, откат | Фаза 1 |
| Добавить `incident` | timeline: влияние, митигация, follow-ups | Фаза 1 |
| Добавить `release` | rollout и наблюдаемость | Фаза 2 |
| Добавить `security` | модель угроз и severity | Фаза 2 |
| Добавить `decision` | ADR-запись | Фаза 2 |
| Слить в существующие | — | `chore`, `test`, `experiment`, `epic`, `retrospective`, `impediment` отклонены |

Критерии: отдельный оракул; отдельный набор обязательных разделов; отдельный набор правил; нет пересечения с существующим типом больше чем на половину разделов.

## Правила проекта

| ID или путь | Правило | AC или CASE |
|---|---|---|
| `ARCH-contract` | Тип задачи — часть task-conf и проверяется теми же правилами | AC-2 |
| `data/sdd-research/06-...` §3 | Требование без метода верификации — пожелание | AC-1, AC-3 |
| UI-0030, «Один источник политики» | Политика объявляется типом, не flow | AC-2 |
| `doc/config/paths.yaml:242-252` | Список `task_types` синхронизирован с каталогами | AC-2 |

## Артефакты и порядок

| Путь | Действие |
|---|---|
| `doc/tasks/UI-0032/research/plan-policy-and-type-taxonomy.md` | изменить: зафиксировать решение по фазам |
| `doc/tasks/UI-0032-0005/research/taxonomy-decision.md` | создать: решение, предусловия фазы 2, отклонённые кандидаты |
| `doc/config/task-conf/types/{spike,migration,incident}/config.yaml` | создать |
| `doc/config/task-conf/types/{spike,migration,incident}/prompt.md` | создать |
| `doc/config/task-conf/types/{spike,migration,incident}/flows/<flow>/{config.yaml,prompt.md}` | создать |
| `doc/config/task-conf/types/{spike,migration,incident}/plan/<tier>.md` | создать |
| `doc/config/paths.yaml` | изменить: пути и `task_types` |
| `doc/tests/test_plan_policy.py` | изменить: проверки новых типов |

1. Зафиксировать решение и предусловия фазы 2 в исследовании.
2. Создать конфиги, промпты и flow трёх типов.
3. Создать шаблоны по разрешённым tier.
4. Объявить пути и типы, прогнать `plan-policy`, `scan`, `validate` на временных карточках.

## Приёмка

| CASE | AC | Дано | Действие | Ожидание и проверка | Ребёнок |
|---|---|---|---|---|---|
| CASE-1 | AC-1 | Исследование и карточка | Прочитать решение по фазам | Критерий, фаза 1, фаза 2 с предусловиями и отклонённые кандидаты зафиксированы | нет |
| CASE-2 | AC-2 | Три новых типа | `arch task types`; `arch scan --scope task-conf`; `arch validate --brief` на временной карточке каждого типа | Типы доступны, имеют flow и промпты, проходят проверки | нет |
| CASE-3 | AC-3 | Политики spike, migration, incident | `arch task plan-policy --type <type> --json` | Разделы и правила профильные: таймбокс и решение, целостность и повтор, таймлайн и follow-ups | нет |
| CASE-4 | AC-4 | Корпус и `approvals` | `arch task diagnose` по корпусу; прочитать approvals | Существующие карточки не изменились; одобрение записано до реализации | нет |

## Выводы и рекомендация

- Рекомендация: принять фазу 1 и зафиксировать фазу 2 как отложенную; отклонённые кандидаты не добавлять.
- Ограничение: критерий «отдельный оракул» оценивает агент; CLI проверяет только структуру разделов и правил. Flow: `spike-first`, `migration-first`, `incident-response`.

## Оценка

16 ч, `medium`: решение и исследование 3 ч, три конфига и промпта 4 ч, три flow 3 ч, шаблоны 4 ч, проверки 2 ч. Подзадач нет: один проверяемый результат таксономии.

## Проверка

```bash
python3 -m unittest doc.tests.test_plan_policy -q -k new_types
arch task types
arch task plan-policy --type spike --json
arch scan --scope task-conf
arch validate --brief
arch docs paths --check
```

- Ожидание: exit 0; новые типы доступны и валидны; фаза 2 не реализована.
- Откат: удалить три каталога типов, их записи в `paths.yaml` и `task_types`; исследование оставить как историю.
