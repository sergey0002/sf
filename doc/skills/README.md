# Скиллы фабрики

Эти инструкции хранятся в проекте и не зависят от клиента агента. Открывайте нужный `SKILL.md` по маршруту из [doc/AGENTS.md](../AGENTS.md). Конфиг фабрики находится в `doc/config/`; клиентские конфиги не являются частью проекта.

## Каталог действующих скиллов (v0.1)

Четыре скилла составляют ядро рабочего процесса фабрики. У каждого — условия загрузки, ссылка на исходник и проверяемые команды.

| Скилл | Условие выбора (when to load) | Команды CLI (проверяемые) | Источник |
|---|---|---|---|
| [arch-cli](arch-cli/SKILL.md) | Нужен доступ к CLI фабрики: чтение задач, архитектуры, индекса, путей, сессий Kilo; валидация записей; превью закрытия. | `task diagnose`, `task validate`, `task close --dry-run`, `list`, `show`, `docs search`, `docs read`, `docs context`, `index check`, `index build`, `validate`, `scan`, `session find`, `session digest` | `doc/skills/arch-cli/SKILL.md` |
| [architecture-read](architecture-read/SKILL.md) | Нужно найти и прочитать применимый архитектурный контракт по ID, домену или термину для задачи (intake, реализация, ревью). | `docs search`, `docs read`, `docs toc`, `docs check-links`, `docs impact`, `docs tree`, `list --id`, `list --domain`, `docs context --task`, `docs related` | `doc/skills/architecture-read/SKILL.md` |
| [create-task](create-task/SKILL.md) | Постановка новой задачи или декомпозиция плана: собрать контекст, выбрать тип/flow, сделать приёмку исполнимой, собрать карточку и стадию. Не выполняет задачу: завершается предложением приступить после явного подтверждения. | `task types`, `task flows --type`, `task flow-prompt`, `task new`, `task init`, `task decompose`, `task-key --next`, `task registry`, `task registry check`, `task registry sync`, `task validate`, `docs paths --check` | `doc/skills/create-task/SKILL.md` |
| [go-to-task](go-to-task/SKILL.md) | Выполнение, продолжение, верификация или закрытие зарегистрированной задачи по точному ключу: разрешить зависимости, выполнить план, записать evidence. | `task diagnose`, `task flow-steps`, `task flow-prompt`, `task workspace`, `task evidence`, `task close`, `task status`, `task subtask validate`, `task subtask status` | `doc/skills/go-to-task/SKILL.md` |

## Дополнительные скиллы (черновики / специализированные)

| Скилл | Назначение | Статус |
|---|---|---|
| [plan-task](plan-task/SKILL.md) | Подготовка и ревью `stageN/plan.md`: tier `micro`/`standard`/`full` по сложности и часам, обязательные разделы и safety floor, оценка, решение о декомпозиции. Шаблоны — в `references/` | draft |
| [architecture-docs](architecture-docs/SKILL.md) | Строгий регламент изменений архитектурной документации: declared paths, frontmatter/schema, валидация через CLI | draft |
| [review-implementation](review-implementation/SKILL.md) | Ревью реализации на стабильном снимке против AC и архитектуры | — |
| [document-session](document-session/SKILL.md) | Зафиксировать подтверждённые решения и evidence из текущего диалога | draft |
| [kilo-session-audit](kilo-session-audit/SKILL.md) | Универсальный аудит сессии Kilo Code по локальной SQLite | — |

## Учебный прогон (baseline scenario)

### Сценарий: «От диагностики задачи к прочтению контракта»

**Цель:** измерить латентность CLI и попадание поиска для входа в задачу. В замер входит только процесс CLI, без времени модели.

**Предусловия:**
- Команды запускаются из корня репозитория как `python3 doc/tools/arch/__main__.py`. Установка пакета в этот прогон не входит: `pip install` требует отдельного окружения и не нужен для воспроизведения.
- Якорь чтения берётся из `docs toc`, а не из предположения о разделе. На текущем дереве это `DOM-task-lifecycle#инварианты`.
- Проверенный снимок — `git rev-parse HEAD` на момент прогона. Незакоммиченные чужие правки в рабочем дереве означают, что замер относится к дереву, а не к чистому коммиту.

**Шаги (все должны завершиться с exit 0):**
1. `python3 doc/tools/arch/__main__.py --version` — холодный старт
2. `python3 doc/tools/arch/__main__.py task diagnose UI-0011 --json --brief` — вход по ключу
3. `python3 doc/tools/arch/__main__.py docs context --task UI-0011 --case CASE-1 --json` — объявленный контекст
4. `python3 doc/tools/arch/__main__.py docs search "task lifecycle" --limit 3 --json` — поиск; оракул: 3 из 3 хитов с `task-lifecycle` в пути
5. `python3 doc/tools/arch/__main__.py docs read DOM-task-lifecycle#инварианты --max-bytes 4000 --json` — раздел, который печатает `docs toc`
6. `python3 doc/tools/arch/__main__.py validate --brief` — структурная проверка
7. `python3 doc/tools/arch/__main__.py index check` — свежесть индекса
8. `python3 doc/tools/arch/__main__.py docs paths --check` — объявленные пути

**Как измерять:** для каждого шага записать `duration_ms` (wall time процесса), `exit_code`, `stdout_bytes` и `stderr_bytes` по фактическому выводу, без округления. Сумма байт шагов 2–5 должна быть меньше 50 КБ. Время шагов 1–3, 5–8 — ориентир < 1000 мс, шаг 4 — < 1500 мс на этой машине; превышение не отменяет exit 0.

**Ограничения:**
- Одна машина, один checkout, без времени рассуждения модели.
- Поиск оценивается по пути хита, а не по смыслу сниппета.
- При изменении CLI, индекса или якоря раздел надо выбрать заново через `docs toc` и перезаписать baseline.

**Запись:** `doc/tasks/UI-0015/baseline-0.2.0-2026-11-22.json` хранит `arch_version`, `git_rev`, команду, время, exit и точные размеры вывода. Повторять те же восемь команд из корня; не подменять якорь и не дописывать причину падения, которой нет в stderr.
