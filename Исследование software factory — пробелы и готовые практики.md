---
title: "Исследование software factory: пробелы и готовые практики"
description: "Загружайте при выборе модели Jira intake, внутренней оркестрации агентов, проектной документации, бизнес-правил и связи изменений с релизом."
paths: []
tags: [research, software-factory, orchestration, jira, docs-as-code]
aliases: [Software Factory Research, Исследование фабрики разработки]
---

# Исследование software factory: пробелы и готовые практики

> [!abstract] Краткий вывод
> В текущих материалах уже описаны слои фабрики, контракт задачи, изоляция, проверка и связанная документация. Основной пробел — **интеграционные контракты и сквозная трассируемость**: что именно должно быть долговечно записано между внешней задачей, внутренними работами, агентскими запусками, изменениями бизнес-правил, проверками и релизом. Источники подтверждают полезность готовых паттернов, но не доказывают, что конкретный продукт следует принять. Это исследовательская заметка, не архитектурное решение; [[Манифест агентной software factory]] не изменялся.

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

## 5. Набор решений для следующего архитектурного штурма

Сначала определить требования и пилот, затем выбрать инструмент:

1. Внешний tracker точно Jira Cloud? Какой тип auth и один project/team или несколько?
2. Нужна ли durable resume после перезапуска и handoff человеку на часы/дни, или достаточно очереди с повторной сверкой tracker?
3. Где живёт task state: Jira parent/child issues, отдельная DB/queue либо workflow engine? Какие данные должны быть audit-retained?
4. Сколько репозиториев/команд, какие доверенные и недоверенные inputs, нужен ли сетевой egress?
5. Какие изменения правил требуют обязательного доменного approval и release snapshot?
6. Определить один пилотный сценарий (например, Jira issue → изолированный PR → независимый CI → обновление docs → release record) и измерить task success, missed/duplicate dispatch, recovery, time-to-review, rework, cost, security policy violations.

**Пока нет ответа на эти вопросы — инструменты остаются кандидатами.** Рекомендуемая ближайшая работа: специфицировать typed task/event contract и acceptance tests; сделать tabletop/failure test для webhook duplicate, out-of-order update, `429`, outage/restart, cancellation, stale task и повторного запуска; затем сравнить минимальную DB queue с одним готовым orchestrator на одном репрезентативном workflow.

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

- [[Манифест агентной software factory]] · [[Архитектура агентной software factory]] · [[Операционная модель агентных команд]] · [[Контракт задачи для агента]] · [[Управление контекстом многоагентных систем]]
- [[Инструменты агентной среды]] · [[Сквозной цикл разработки]] · [[Docs-as-Code и CI]] · [[Сущности]] · [[Флоу]] · [[Тесты]] · [[Threat model агентной разработки]] · [[Агентский CI-CD]] · [[Актуальность и staleness]] · [[Безопасный деплой агентами]]
