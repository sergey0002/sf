---
title: "Исследование software factory: пробелы и готовые практики"
description: "Загружайте при выборе модели Jira intake, внутренней оркестрации агентов, проектной документации, бизнес-правил и связи изменений с релизом."
paths: []
tags: [research, software-factory, orchestration, jira, docs-as-code]
aliases: [Software Factory Research, Исследование фабрики разработки]
---

# Исследование software factory: пробелы и готовые практики

> [!abstract] Краткий вывод
> В текущих материалах уже описаны слои фабрики, контракт задачи, изоляция, проверка и связанная документация. Основной пробел — **интеграционные контракты и сквозная трассируемость**: что именно должно быть долговечно записано между внешней задачей, внутренними работами, агентскими запусками, изменениями бизнес-правил, проверками и релизом. Источники подтверждают полезность готовых паттернов, но не доказывают, что конкретный продукт следует принять. Это исследовательская заметка, не архитектурное решение; [корневой манифест](../../../Манифест агентной software factory.md) не изменялся.

**Проверено:** 2026-11-21. **Уровень доказательств:** преимущественно первичная документация платформ/стандартов. Она подтверждает их контракт и возможности, но не независимое сравнительное качество и не пригодность конкретно для данной фабрики.

## 1. Сверка с имеющейся документацией

В vault уже есть: issue/task contract и handoff; разделение внешнего intent и внутренней декомпозиции; bounded workspaces, least privilege, независимый CI/verifier; сущности, флоу, тесты, ADR и docs-as-code; актуальность и release-oriented workflow. См. [[Архитектура агентной software factory]], [[Операционная модель агентных команд]], [[Контракт задачи для агента]], [[Управление контекстом многоагентных систем]], [[Сущности]], [[Флоу]], [[Docs-as-Code и CI]], [[Агентский CI-CD]], [[Актуальность и staleness]].

Исследованиями стоит закрыть не общие принципы, а следующие конкретные вопросы:

| Пробел | Что нужно определить/зафиксировать | Исследовательский результат |
|---|---|---|
| Jira intake | Как получать изменения, восстанавливаться после пропусков, переживать дубли и rate limits; что хранить как внешний источник правды | Webhook ingress + reconciliation / polling policy, права и failure modes |
| Durable внутренняя работа | Идентификаторы, владельцы/leases, состояния, зависимости, retries, отмена, resume, audit, ручные approvals | Выбрать между лёгкой очередью/DB, graph runtime или workflow engine по требованиям, а не по названию продукта |
| Knowledge model | Как связать code evidence с утверждённым смыслом сущностей, флоу и правил; кто владелец и как отмечается уверенность | Stable IDs, provenance, owner, version/validity, links на тесты и код; candidate facts не становятся policy без review |
| Rule-to-release trace | Как принудительно обнаруживать изменение правила без обновления документации/тестов и фиксировать, что вошло в релиз | PR impact map/checklist или автоматизированные links; release record с commit, миграциями, проверками и rollback |
| Trust boundary | Как разделить полномочия координатора, агента, verifier и release identity | Проверяемые права, sandbox/egrеss, credentials, approvals и audit; документация сама по себе не gate |

## 2. Jira Cloud: события не равны очереди

### Что подтверждает документация Atlassian

- Jira Cloud повторяет неуспешный webhook до пяти раз с randomized backoff в интервале 5–15 минут; повторные запросы используют одинаковый `X-Atlassian-Webhook-Identifier`. После исчерпания retries доступны failed-webhook operations. Следовательно, обработчик должен дедуплицировать события, а эксплуатация — иметь путь обнаружить и повторно обработать пропуски. [Webhook documentation](https://developer.atlassian.com/cloud/jira/platform/webhooks/)
- Приёмник должен быстро ответить и перенести фактическую работу в асинхронную обработку; поток может иметь всплески, Jira ограничивает число параллельных доставок. Значит, endpoint не должен синхронно запускать LLM или ждать завершения coding run. [Webhook consuming/reliability](https://developer.atlassian.com/cloud/jira/platform/webhooks/)
- Для динамических webhook registrations срок активности — 30 дней с создания/refresh; это применимо именно к таким registration paths, не ко всем способам конфигурации. [Webhook registration](https://developer.atlassian.com/cloud/jira/platform/webhooks/)
- Jira REST имеет rate-limit механизмы; на `429` следует соблюдать `Retry-After` и backoff. Документация перечисляет несколько независимых лимитов для соответствующих типов интеграций; точные лимиты зависят от метода авторизации/endpoint и должны перепроверяться для выбранного способа подключения. [Rate limiting](https://developer.atlassian.com/cloud/jira/platform/rate-limiting/)

### Практический вывод (рекомендация, не Jira guarantee)

Использовать webhook как **сигнал изменения**, а не как единственную запись задачи или гарантированный command queue. На приёме: проверить подпись/доверенный канал согласно типу интеграции, записать event ID и payload/ссылку на событие в durable inbox, быстро подтвердить доставку, затем enqueue. Consumer идемпотентно перечитывает актуальную задачу из Jira перед dispatch; периодический reconciliation сравнивает eligible issues и внутренние состояния, чтобы исправлять потерянные события и рассинхронизацию. При внутренних dual-write операциях (например, запись task state + публикация события) применим transactional outbox; consumer всё равно проектируется идемпотентным. AWS описывает именно этот паттерн и предупреждает о duplicate delivery. [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

Отдельно исследовать аутентификацию (OAuth app vs API token, пользовательский/сервисный контекст), scope/permissions, project selection, pagination, JQL filters, attachment/comment/transition use cases и восстановление очереди. Не сохранять issue descriptions/comments как доверенные инструкции: это входные данные с prompt-injection риском, что уже покрывает [[Threat model агентной разработки]].

## 3. Внутренний task graph и выбор runtime

| Вариант | Что даёт по первичной документации | Ограничение/граница | Где проверять в пилоте |
|---|---|---|---|
| **Своя небольшая очередь + SQL/DB** | Меньше новых понятий и сервисов; достаточно для ограниченного workflow, если команда сама владеет leases, retries, recovery, event log и UI | Сложность надёжности и операционных edge cases полностью остаётся у команды; нужно формализовать гарантию доставки/восстановления | Нужны ли длительные waits, human pause, многоэтапное восстановление, cross-service операции? |
| **Temporal** | Долгоживущие workflow, replay/event history, durable timers, workflow/activity separation; retries на Activities. Activity может исполниться более одного раза, поэтому side effects должны быть идемпотентны; ошибки можно классифицировать как retryable/non-retryable. [Workflows](https://docs.temporal.io/workflows), [Python error handling](https://docs.temporal.io/develop/python/best-practices/error-handling) | Это workflow platform с service/worker/operations footprint; детерминированный replay требует изолировать внешние эффекты в Activities; не решает автоматически смысл task model или безопасность агента | Восстановление после рестарта/долгой паузы, human approval, отмена, retries, event-history growth, операционная стоимость |
| **LangGraph persistence** | Checkpointer сохраняет graph state по thread/checkpoint и поддерживает interrupt/human-in-the-loop, resume/replay и fault recovery; Store предназначен для данных, разделяемых между threads. [Checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers), [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | Checkpointer — состояние graph/thread, а не автоматически внешняя task DB, ticket inbox, audit ledger или multi-project ownership model. Проверить выбранный backend, retention, ACL и migration | Достаточно ли graph-level resume? Как разделить долгоживущую задачу от thread/session memory? |
| **OpenAI Symphony** | Открытая спецификация описывает tracker polling, per-issue workspaces, ограниченную concurrency, retry/reconciliation, workflow config и coding-agent runner. На дату проверки репозиторий показывает экспериментальную реализацию и предупреждает, что это evaluation-only; README перечисляет Linear, GitHub Issues, Jira Cloud, Asana, GitLab adapters. [SPEC](https://github.com/openai/symphony/blob/main/SPEC.md), [Elixir README](https://github.com/openai/symphony/blob/main/elixir/README.md), [Repo README](https://github.com/openai/symphony) | Не универсальный durable workflow engine; SPEC допускает tracker/filesystem-driven recovery без постоянной orchestrator DB и явно оставляет safety posture реализации. Prototype не следует трактовать как production-ready. Репозиторий меняется: проверять commit/version перед применением | Сверить tracker adapter, event-vs-polling, persistence/recovery, security isolation, worktree semantics, approval UX и test coverage на конкретном commit |

**Осторожный вывод:** эти варианты не взаимозаменяемы. LangGraph — graph runtime/persistence; Temporal — durable workflow orchestration; Symphony — специализированный issue-driven agent scheduler/reference implementation; собственная очередь — минимальная архитектура с максимальной ответственностью за её гарантии. Не принимать Symphony или любой framework целиком только из-за сходства с задачей: использовать его как каталог требований и тестовых сценариев.

## 4. Каноническая модель знаний и изменение бизнес-правил

Текущие заметки о сущностях и флоу уже задают машиночитаемые документы. Для перехода к рабочей модели добавить в реализацию/схему только недостающие поля: `stable_id`, `owner`, `status` (candidate/reviewed/active/superseded), `source/provenance`, `valid_from`/версия, ссылки на `code paths`, `tests`, `ADR`, `release`. Это рекомендация к прототипу schema, а не готовый универсальный стандарт. Код, схема и runtime — evidence о текущем поведении; они не всегда устанавливают бизнес-намерение.

**Docs-as-code** — разумная начальная точка: Markdown рядом с кодом, version control, PR review и CI. Backstage TechDocs подтверждает такой продуктовый вариант и каталогизацию docs из service catalog, но это vendor documentation и не доказательство, что Backstage нужен маленькой фабрике. Начинать можно без портала; внедрять его только при подтверждённой потребности в discovery/catalog. [Backstage TechDocs](https://backstage.io/docs/features/techdocs/)

**ADR/MADR** пригоден для rationale и последствий архитектурного выбора; он не должен дублировать текущее правило или проектную документацию. MADR — формат-шаблон, а не стандарт с гарантией качества решения. [MADR](https://adr.github.io/madr/)

**DMN** предоставляет формальную модель требований/логики решений, включая decision tables. На официальной странице OMG на момент проверки отображается DMN 1.7 beta (сентябрь 2026) с явной пометкой, что для conformance следует ориентироваться на final approved specification; обнаруженный PDF 1.6 содержит `Release Date: tbd`. Поэтому не записывать 1.6 как актуальный финальный стандарт без дополнительной верификации и не вводить DMN повсеместно: рассматривать его только для сложных, часто меняющихся, таблицоподобных правил, где нужны бизнес-review и исполняемая согласованность. Простые правила остаются в обычных canonical docs + коде + тестах. [OMG DMN](https://www.omg.org/spec/DMN/)

### Минимальный rule-to-release контроль

1. У PR/изменения есть parent task ID и список затронутых сущностей, флоу/правил, контрактов и migrations (может быть `none` с обоснованием).
2. Если меняется утверждённая семантика — ссылка на canonical doc и его owner; test/fixture покрывает новый кейс и известные исключения.
3. CI проверяет разрешимость ссылок/ID и наличие требуемых артефактов по labels/paths/PR metadata; сначала advisory, затем required gate после измерения false positives.
4. Release record создаётся из конкретных merged commits/tags и содержит изменённые rule/doc IDs, migrations, validation evidence, known issues и rollback pointer. Не копировать туда всю текущую документацию.
5. Change owner/доменный владелец подтверждает смысл правила; verifier/CI независимо подтверждают тесты; release authority отдельно выполняет promotion согласно [[Безопасный деплой агентами]].

Это предложенная схема контроля. Она требует пилота и не подтверждена отраслевым сравнительным исследованием в рамках этой заметки.

## 5. Как продолжать проектирование — до любого пилотного прогона

**Вывод по энциклопедии:** сейчас рано «прогонять пилот» или выбирать оркестратор. Сначала нужно спроектировать сам workflow фабрики и его контракты. Tabletop walkthrough ниже — это только проверка полноты бумажной модели на сценариях; это не запуск агентов и не эмпирический пилот.

### Рекомендуемая последовательность

1. **Зафиксировать границы и цели.** Какие продукты/репозитории и команды входят в первую проектируемую систему; какие источники задач ожидаются (Jira, другие trackers, ручная постановка); где проходит граница target release; какие действия остаются исключительно за человеком. Не предполагать единственный задачник или репозиторий.
2. **Спроектировать общий task contract и intake.** Определить source-neutral поля `task.json`, сохранение provenance/source snapshot, устойчивый `task_key`, правила папок/веток, обновление снимка, ручной `create task` и интерфейс CLI-адаптера. Разделить внешний source of truth, внутреннее состояние выполнения и generated context. Требования должны следовать из [[Контракт задачи для агента]] и слоёв памяти в [[Управление контекстом многоагентных систем]].
3. **Нарисовать основной lifecycle и состояния.** Для каждого состояния указать входное событие, actor, guard, артефакт, разрешённые действия и выход. В качестве черновой гипотезы проверить: `received → normalized → needs-clarification/ready → planned → approved-if-required → executing → verifying → human-review → PR/merged/released → closed`; отдельно определить `blocked`, `cancelled`, `rejected`, `failed`, stale input и повторное открытие/новую stage. Не копировать автоматически audit/repair states из reference architecture: это другой workflow-паттерн, пригодный лишь там, где действительно есть audit-first finding flow.
4. **Спроектировать ветвления, циклы и handoff.** Отдельно описать: недостающие требования → уточнение; fail проверки → исправление в той же/новой стадии; новое требование → новая stage; high-risk/неясная семантика → owner decision; source update/cancel → приостановка и пересборка scope; проверенный результат → human PR/release. На каждом переходе определить typed handoff/artifact, что сохраняется durable и что перечитывается из исходного источника.
5. **Задать полномочия и trust boundaries.** Матрица `actor × read/write/action × resource` для CLI-адаптера, координатора, исполнителя, verifier, owner и release authority. Входы из Jira/другого tracker/чата считать недоверенными данными: требования можно извлекать, но они не должны расширять полномочия. Установить policy, isolated workspace, credentials, network, protected tests/gates и обязательные human approvals до рассмотрения автономности ([[Threat model агентной разработки]], [[Инструменты агентной среды]]).
6. **Описать отказоустойчивость как часть флоу.** Повторные/устаревшие/out-of-order входы, rate limits, недоступный tracker, падение worker, resume после паузы, cancel, повторный запуск, конфликт ветки/грязная рабочая копия, timeout/лимиты, зависшая human approval. Для каждого: ожидаемое состояние, idempotency key, retry/no-retry, reconcile path, owner/alert и доказательство восстановления. Webhook/queue/runtime выбирать позднее по этим требованиям.
7. **Определить done, evidence и eval criteria.** Что должно быть истинно для окончания каждой стадии и всей задачи: acceptance, обязательные тесты по риску, review, architecture delta/`none`, проверяемые команды и traceable evidence. Заранее определить метрики и ограничения успеха: correctness, first-pass acceptance, review time, rework, cost per accepted change, recovery и policy violations; не считать число PR/строк успехом ([[Evals и метрики агентной разработки]], [[Операционная модель агентных команд]]).
8. **Провести design review на сценариях, не исполняя агентов.** После фиксации состояний вручную пройти happy path и отказные случаи из пункта 6; отметить недостающие переходы, неоднозначного владельца или потерянные данные. Это tabletop-проверка спецификации. Лишь после неё можно сравнить подходящие runtime/queue варианты и подготовить пилотный протокол.
9. **Пилотировать только после entry criteria.** Нужны конкретный репозиторий/task, acceptance oracle, детерминированный CI, ограниченный sandbox, владельцы/approval, baseline/eval set и stop/rollback path. Начать с assisted режима, где агент предлагает изменения, а человек контролирует шаги; не включать auto-merge/deploy. Масштабировать только по заранее заданным exit criteria из [[Операционная модель агентных команд]].

### Что сделать следующим в проекте

Следующий проектный артефакт — **одна сквозная диаграмма состояний + таблица переходов** для нейтральной к источникам задачи, а не pilot run. Для каждой строки таблицы: `from | event | guard | actor | action | artifact/evidence | to | retry/stop/owner`. Начать с верхнего уровня, не расписывая сразу все внутренние поля и сервисы. Сначала обсудить поток/полномочия, затем отразить согласованное в единственном корневом манифесте; точный CLI schema и выбор runtime идут после.

Опорные материалы энциклопедии: [[Архитектура агентной software factory]] (control plane, изоляция, независимая verification); [[Контракт задачи для агента]] (intent/scope/acceptance/authority); [[Управление контекстом многоагентных систем]] (источники, свежесть, ACL, handoff); [[Threat model агентной разработки]] (untrusted input/permissions); [[Операционная модель агентных команд]] (entry/exit criteria); [[Evals и метрики агентной разработки]] (оценка исхода, траектории и стоимости). Рекомендация — synthesis этих материалов, а не уже утверждённое архитектурное решение.

## 6. Evidence и ограничения

- **Первичные product docs/specs:** Atlassian, Temporal, LangChain, OpenAI Symphony repository/spec, AWS, OMG, Backstage, MADR. Они надёжны для описания своих API/предложенной модели, но vendor/maintainer-owned и не доказывают comparative superiority.
- **Независимая best-practice оценка:** в этом проходе не проводилась. Следующие источники проверки — production pilot, failure injection, local eval suite и review владельцев.
- **Изменчивые данные:** Jira API limits, Symphony repo/spec/adapters, LangGraph/Temporal APIs и статус OMG DMN перепроверять перед tool choice и implementation.
- **Не завершено:** стоимость/операционная модель managed vs self-hosted; Jira auth/permissions details; durable event store choice; business rules ownership schema; production sandbox/network policy; проверка DORA 2025 полного отчёта на предмет применения метрик. Не делать по этой заметке вывод о причинном влиянии AI на throughput/instability.

## Источники

Все URL проверены 2026-11-21; динамические страницы нужно перепроверять перед реализацией.

- Atlassian, Jira Cloud Webhooks — https://developer.atlassian.com/cloud/jira/platform/webhooks/ — первичная документация API, retry/delivery/registration.
- Atlassian, Jira Cloud Rate Limiting — https://developer.atlassian.com/cloud/jira/platform/rate-limiting/ — первичная документация; лимиты зависят от интеграционного режима.
- AWS Prescriptive Guidance, Transactional Outbox — https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html — официальный паттерн-проводник, не нейтральный сравнительный эксперимент.
- Temporal Workflows — https://docs.temporal.io/workflows — первичная документация продукта.
- Temporal Python error handling — https://docs.temporal.io/develop/python/best-practices/error-handling — первичная SDK документация.
- LangGraph Checkpointers — https://docs.langchain.com/oss/python/langgraph/checkpointers — первичная документация продукта.
- LangGraph Persistence — https://docs.langchain.com/oss/python/langgraph/persistence — первичная документация, разграничение checkpointer/store.
- OpenAI Symphony SPEC — https://github.com/openai/symphony/blob/main/SPEC.md — maintainer-authored draft spec; pin конкретный commit для любого implementation review.
- OpenAI Symphony README — https://github.com/openai/symphony — проект помечен engineering preview для trusted environments.
- OpenAI Symphony Elixir README — https://github.com/openai/symphony/blob/main/elixir/README.md — implementation/evaluation-only warning и список adapters; не считать это независимой проверкой.
- MADR — https://adr.github.io/madr/ — maintainer docs и шаблоны ADR.
- OMG DMN — https://www.omg.org/spec/DMN/ — страница версий и статуса; на момент проверки 1.7 beta.
- Backstage TechDocs — https://backstage.io/docs/features/techdocs/ — первичная документация продукта.

## Связи

- [Корневой манифест](../../../Манифест агентной software factory.md) · [[Архитектура агентной software factory]] · [[Операционная модель агентных команд]] · [[Контракт задачи для агента]] · [[Управление контекстом многоагентных систем]]
- [[Инструменты агентной среды]] · [[Готовые решения агентной software factory]] · [[Исследование формата документации проекта и входящей задачи]] · [[Сквозной цикл разработки]] · [[Docs-as-Code и CI]] · [[Сущности]] · [[Флоу]] · [[Тесты]] · [[Threat model агентной разработки]] · [[Агентский CI-CD]] · [[Актуальность и staleness]] · [[Безопасный деплой агентами]]
