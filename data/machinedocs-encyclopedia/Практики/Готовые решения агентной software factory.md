---
title: "Готовые решения агентной software factory"
description: "Загружайте при сравнении готовых agentic software factory, multi-agent coding platforms, task-to-PR automation и open-source building blocks перед проектированием или выбором стека."
paths: []
tags: [research, software-factory, multi-agent, orchestration, tools]
aliases: ["Agentic Software Factory Solutions", "Готовые фабрики агентной разработки"]
---

# Готовые решения агентной software factory

> [!abstract] Вывод
> На рынке есть несколько решений, закрывающих разные части software factory, но их нельзя считать эквивалентными. Ближе всего к управляемой end-to-end фабрике — коммерческие платформы Factory и Devin; для GitHub-first workflow — Copilot вместе с GitHub Agentic Workflows; для собственного платформенного слоя — OpenHands; Symphony и опубликованная OpenAI Performance Factory полезны прежде всего как reference patterns, а не как готовая production-система для нашего процесса. В просмотренных публичных описаниях ни у одного кандидата не подтверждён весь наш контракт сразу: разные источники задач и ручная постановка → единый `task.json`/namespaced ID → release-specific branches → task/stage artifacts → внешняя canonical architecture delta → контролируемое человеком PR/merge.

**Проверено:** 2026-11-21. Это обзор официальных продуктовых страниц, документации и репозиториев, дополненный сравнением с текущими требованиями манифеста. Публичные vendor claims — заявления поставщиков; они не являются независимым сравнением качества или причинным доказательством роста производительности.

## 1. Сначала различить классы решений

| Класс | Что покупаем/берём | Примеры | Чего сам по себе не даёт |
|---|---|---|---|
| **End-to-end коммерческая платформа** | Несколько входов, среды исполнения, агенты/оркестрация, интеграции, контроль и UI | Factory, Devin | Гарантию совместимости с нашими ID, стадиями, release branches, docs-root и approval policy |
| **Git-hosting-native automation** | Репозиторные события, Actions/CI, workflow-as-code, безопасные выходы | GitHub Agentic Workflows + Copilot/поддерживаемый coding agent | Общую организационную очередь задач, независимую от GitHub, и полную модель релизов/документации фабрики |
| **Расширяемая agent platform** | UI/API/SDK, sandbox/workspace и автоматики, на которых строим свои процессы | OpenHands | Готовый универсальный task lifecycle и нормализатор всех источников |
| **Task runner / reference spec** | Polling задач, отдельные workspaces, retries, concurrency и dispatcher | OpenAI Symphony | Полный workflow engine, enterprise control plane или готовую поддержку всего нашего task contract |
| **Внутренний reference architecture** | Уроки построения фабрики из production workflow | OpenAI Performance Factory | Продукт/репозиторий, который можно установить и использовать как есть |
| **Coding-agent runtime/workbench** | Параллельные сессии, worktrees, subagents, API/harness | Codex app/Agents API | Сам по себе — универсальную долговременную очередь и source-of-truth для задач |

Разделение важно: наличие subagents ещё не означает наличие фабрики; наличие «issue → PR» не означает, что продукт умеет управлять несколькими типами задачников, версиями релизов, стадиями и принятыми архитектурными изменениями.

## 2. Кандидаты и практическая пригодность

### 2.1 Factory — самый широкий коммерческий software-factory продукт

Factory описывает платформу как связанный lifecycle от intake/triage через planning, execution и validation до release/monitoring. В продуктовой линейке документированы Droids для отдельных запусков, persistent compute, Automations и Missions для длинной многоагентной работы. Missions начинают с совместного уточнения результата, строят features/milestones и после согласования плана координируют workers и валидацию. Automations могут стартовать по расписанию, Slack-событию, GitHub event или webhook; шаблон Ticket-to-PR рассчитан на Linear/Jira. Платформа заявляет model routing и deployment варианты SaaS, hybrid, on-prem и air-gapped.

**Где пригоден:** если нужен наиболее цельный готовый продукт для нескольких видов повторяемой инженерной работы, а не только единичный coding-agent run; особенно если важны интеграции, управляемые automations, миссии и централизованные controls.

**Что проверить именно нам:** какие источники и действия доступны в нужной конфигурации/тарифе; как задаются target release и branch mapping; можно ли сохранить наш source-specific `task_key`, локальный `task.json`, `doc.md`, per-stage plan/verification, generated diff и architecture delta; кто и при каких настройках делает push, создаёт PR и может merge. Публичная документация подтверждает общие интеграции и workflows, но не подтверждает наш конкретный артефактный контракт.

**Доказательная оговорка:** product claims о метриках результата и customer case studies принадлежат поставщику; использовать их как вопросы для due diligence, не как прогноз нашего ROI.

Источники: [Factory — Software Factory](https://factory.ai/product/software-factory), [Factory Missions](https://docs.factory.com/missions/overview), [Factory Automations](https://docs.factory.com/automations/custom), [Droid Exec / Mission Mode](https://docs.factory.com/droid-exec/overview).

### 2.2 Devin / Cognition — автономный исполнитель с multi-agent delegation

Публично описанный Managed Devins pattern: главный Devin координирует работу, разбивает её на узкие подзадачи, запускает отдельные Devin сессии в изолированных VM, наблюдает за ними, разрешает конфликты и собирает результаты; у человека остаются ссылки на отдельные сессии и возможность остановить/направить исполнителя. Cognition также описывает интеграции через Jira/Linear, Slack, CLI/API, PR review и автоматический triage. Это сочетает async execution и делегирование, но платформа и внутренний orchestration/control plane закрыты.

**Где пригоден:** большие, достаточно делимые инженерные работы, миграции, повторяемый triage/QA и backlogs, где отдельные агенты могут работать в независимых песочницах, а lead сводит результаты.

**Что проверить именно нам:** task-source coverage для всех нужных систем и manual task entry; возможности задавать task IDs/папки/ветки и несколько release branches; перенос provenance/stages в наши документы; доступ к конфигурации planning, policies, retries и audit; возможность удержать обязательный human approval. Наличие orchestrator-agent не делает его state machine наблюдаемой или детерминированной снаружи.

**Ограничения доказательств:** описания поведения и внутренних результатов опубликованы самим поставщиком; не следует переносить их заявленные throughput/productivity результаты на наш процесс без собственного baseline и eval.

Источники: [Devin Can Now Manage a Team of Devins](https://cognition.com/blog/devin-can-now-manage-devins), [How Cognition Uses Devin to Build Devin](https://cognition.com/blog/how-cognition-uses-devin-to-build-devin), [Devin Desktop](https://cognition.com/blog/introducing-devin-desktop), [Multi-Agents: What’s Actually Working](https://cognition.com/blog/multi-agents-working).

### 2.3 GitHub Copilot + GitHub Agentic Workflows — automation близко к репозиторию

GitHub Copilot предоставляет coding-agent sessions, review и работу с issue/PR; доступны также сторонние coding agents. Отдельный проект **GitHub Agentic Workflows (gh-aw)** стал generally available 28 октября 2026: задачи задаются Markdown с frontmatter, компилируются в стандартные GitHub Actions workflows, используют Copilot или поддерживаемый внешний coding agent и могут выполнять triage issues, анализ CI, обновление документации и написание тестов.

В опубликованной security architecture workflow-agent по умолчанию работает с read-only правами в sandbox; записи идут через validated safe outputs/отдельные jobs, а proposed changes проходят threat detection. Это сильный пример явного разделения «agent proposes» и «privileged workflow applies».

**Где пригоден:** если большая часть работы и review уже живёт в GitHub; для событийных и периодических workflow вокруг issue/PR/CI; когда важно хранить инструкции и automation как versioned repository files и использовать существующие Actions runner policies.

**Что не считать решённым автоматически:** `gh-aw` — workflow automation для GitHub, не общий task service для любых задачников. Другой tracker теоретически можно присоединить инструментами/API/webhook, но это не равнозначно встроенному source-neutral contract и общей очереди. Пользовательские правила release branch, ручной chat intake и stage/documentation model потребуют отдельного слоя.

Источники: [GA announcement](https://github.blog/changelog/2026-10-28-github-agentic-workflows-generally-available/), [gh-aw repository](https://github.com/github/gh-aw), [security architecture](https://github.com/github/gh-aw/blob/main/docs/src/content/docs/introduction/architecture.mdx), [Copilot coding agent](https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent), [third-party coding agents](https://docs.github.com/en/copilot/concepts/agent-capabilities/about-agents/about-third-party-coding-agents).

### 2.4 OpenHands — расширяемая платформа, а не готовая фабричная схема

Текущая документация разделяет Agent Canvas (open-source browser client/control center), Software Agent SDK и Agent Server (agent execution/workspace API), Automation Server и Sandbox Server. Есть hosted Cloud и коммерческие Enterprise варианты. Automations создают отдельные разговоры в свежих sandboxes и запускаются по расписанию; официальные примеры включают PR review, dependency upgrade, incident triage, QA и vulnerability remediation. OpenHands можно использовать как готовую поверхность для coding-agent работы или как SDK/backend для создания более специфичных внутренних workflows.

**Где пригоден:** когда важны открытый/расширяемый agent layer, выбор моделей/агентов, собственные sandboxes и готовность команды написать/поддерживать task lifecycle и интеграционные адаптеры.

**Что проверить:** какие компоненты и лицензии относятся к выбранному deployment; модель user-scoped automation и credential access; event triggers/retention/recovery/concurrency; реальную схему approval и изоляции. В текущих docs отдельно отмечено, что прежний OpenHands CLI и legacy GUI больше не являются поддерживаемым путём — ориентироваться на Agent Canvas/SDK, не на старые quickstarts.

**Граница:** SDK, Agent Server и Automations дают строительные блоки и интерфейс управления агентными запусками; из публичного overview не следует, что они уже предоставляют наш универсальный multi-tracker graph, release-aware branch policy или семантические architecture deltas.

Источники: [OpenHands Introduction](https://docs.openhands.dev/overview/introduction), [Agent Canvas](https://docs.openhands.dev/openhands/usage/agent-canvas/overview), [SDK](https://docs.openhands.dev/sdk), [Automations](https://docs.openhands.dev/openhands/usage/automations/overview), [Enterprise](https://docs.openhands.dev/enterprise).

### 2.5 OpenAI Symphony — полезный task-runner spec, но не готовый универсальный orchestrator

Symphony — опубликованный language-agnostic draft spec для долгоживущего сервиса, который poll-ит настроенный issue tracker, нормализует задачи, создаёт workspace на issue, dispatch-ит coding-agent sessions с bounded concurrency и занимается retries/reconciliation/observability. В актуальной спецификации описаны issue tracker adapter, orchestrator, workspace manager, agent runner и workflow contract; reference implementation помечена авторами как evaluation-only/prototype. В implementation перечислены adapters для нескольких trackers, но это не доказательство динамической маршрутизации каждой задачи между любыми источниками в одном процессе: спецификация ориентируется на один настроенный tracker.

**Где пригоден:** как каталог конкретных операционных требований и edge cases для нашего будущего flow: polling/reconciliation, eligibility, bounded concurrency, workspaces, retries, human-review handoff и operator visibility.

**Не рекомендуется принимать как готовое решение без проверки:** draft protocol, prototype status, выбранная интеграция с Codex app-server и explicitly implementation-defined trust/approval posture означают, что production hardening и наши task-source semantics остаются нашей ответственностью.

Источники: [Symphony SPEC](https://github.com/openai/symphony/blob/main/SPEC.md), [repository README](https://github.com/openai/symphony), [Elixir reference implementation](https://github.com/openai/symphony/tree/main/elixir).

### 2.6 OpenAI Performance Factory — наиболее полезный опубликованный pattern для lifecycle

Это внутренняя система OpenAI, не скачиваемый продукт. В статье от 19 ноября 2026 описан её composition: configurable task service/workflows, dispatch loop выбирает следующий ready step, Codex cloud API исполняет его, subscriptions будят ожидающие задачи по событиям вроде PR review/deploy. Состояние и findings сохраняются, workflow может переходить между агентами и людьми и продолжаться после review/deployment. Regression workflow идёт от alert/исследования через предложение fix к последующей проверке восстановления.

**Почему это важно для нашего дизайна:** показывает, что фабричный flow может быть event-driven state machine с долговечным task state, а не одним длинным prompt/agent session. Ровно такой тип модели нужен, чтобы отдельно определить ожидание человека/CI/release и возобновление работы.

**Граница доказательства:** описаны внутренние компоненты и поставщицкие результаты одного специализированного performance workflow; это не универсальный blueprint, не продукт и не независимая оценка.

Источник: [How OpenAI’s Performance Factory keeps ChatGPT fast](https://openai.com/index/how-openai-performance-factory-keeps-chatgpt-fast/).

### 2.7 Codex app / Agents API — рабочая поверхность и runtime primitives

Codex app документирует параллельные agent threads, проекты и worktrees; Agents API описывает managed Codex harness, long-running sessions/tool use и делегирование независимых подзадач subagents. Это может закрывать исполнение/делегирование в собственной системе, но не заменяет отдельную модель источников задач, durable task lifecycle, release routing и governance.

Источники: [Introducing the Codex app](https://openai.com/index/introducing-the-codex-app/), [Agents API](https://openai.com/index/introducing-the-agents-api/), [Codex subagents](https://developers.openai.com/codex/subagents).

## 3. Сопоставление с текущими требованиями проекта

Статус **«не видно в публичных материалах»** означает только, что проверенные описания не подтверждают capability; это не доказательство её отсутствия. Возможность может быть enterprise-only, hidden behind configuration или доступна через API — её надо подтвердить у поставщика.

| Требование проекта | Factory | Devin | GitHub Copilot + gh-aw | OpenHands | Symphony / OpenAI reference |
|---|---|---|---|---|---|
| Несколько task entry points | Jira/Linear, Slack/webhook и другие integrations в документации; проверить точный scope | Jira/Linear, Slack/CLI/API заявлены | Отлично для GitHub events/issues/PR; внешние источники требуют своего adapter | Интеграции и MCP/automations; общий intake контракт строить | Symphony adapter model да; обычно один настроенный tracker; Performance Factory — внутренний task service |
| Ручная постановка через чат/CLI | Prompt entry есть; normalized task record надо проверить | Prompt/session entry есть; наш `task.json` не подтверждён | Prompt/session и CLI есть, но перевод в наш task directory — custom | Prompt-based conversation/automation есть; task ID lifecycle — custom | Возможно реализовать в собственной системе, не предоставляется как наш контракт |
| Source-prefix ID + `tasks/<task_key>` + branch naming | Публично не подтверждено | Публично не подтверждено | Можно реализовать в workflow/repo, не встроенная политика | Наша реализация | Требует специфицировать и реализовать |
| Stages, plan/verification/diff artifacts | Missions дают milestones, но не наш task/stage schema | Есть plans/sessions/reviews; наша stage structure не подтверждена | Artifacts в Actions возможны, но общий lifecycle — custom | Conversations/artifacts/SDK; точная schema — custom | PF имеет task states/findings; Symphony workflow contract, детали нашей schema — custom |
| External canonical docs + semantic architecture delta | Не найдено подтверждение | Не найдено подтверждение | Не входит в GitHub issue/PR workflow из коробки | Можно строить через SDK/integrations, но не встроенный наш формат | Потребует нашей модели и adapter |
| Human-controlled code PR/release | Controls заявлены, точные defaults проверить | Reviewable PR flows описаны; merge policy проверить | PR/review integration есть; policies/permissions задаются на GitHub | Integration flow configurable; credential scope проверять | Symphony posture implementation-defined; PF внутренний case |
| Durable pause/restart/event resume | Persistent missions/automations заявлены; точные state guarantees проверить | Long-running/managed sessions заявлены; guarantees проверить | Actions execution/event model; task workflow continuity ограничена платформой | Automation conversations persist/reviewable; scheduler/backend semantics проверить | Это сильная часть PF pattern; Symphony draft описывает retries/reconciliation, но state recovery ограничен спецификацией |
| Multi-agent orchestration | Missions + workers/validators | Managed Devins / team coordination | Параллельные agent tasks и workflows; не считать автоматически shared task graph | Extensible SDK/agent platform; состав координации реализовать/проверить | Symphony — параллельные task runs; PF — последовательные workflow steps, несколько запусков/агентов |
| Self-host/model/provider flexibility | Vendor claims broad deployment/model routing; due diligence | Product/platform-specific; deployment options проверять | Тесно связано с GitHub Actions/policies и доступными engines | Сильная гибкость SDK/backend/deployment, при выборе компонентов учесть licenses | Symphony spec language-agnostic, но reference runtime ориентирован на Codex; PF внутренний |

## 4. Что из этого следует для проектирования нашей фабрики

### Наблюдения

1. **Нет единого понятия «multi-agent».** Параллельные независимые task sessions (Copilot/Codex/Symphony), разделение одной большой задачи на work packages (Missions/Managed Devins), внутренние субагенты одного вызова модели и долгоживущие managers — разные механизмы с разными гарантиями.
2. **Сильные готовые платформы объединяют entry points, compute, agents, control и automations**, но их публичный contract не совпадает автоматически с нашим: несколько источников, Jira без prefix/прочие с prefix, ручное создание, release branch mapping, task/stage history, generated diffs, и внешняя canonical architecture база.
3. **Публикации, полезные для нашего flow:** Factory Missions показывают plan/milestones до исполнения; Symphony формализует task polling/workspaces/retries; OpenAI Performance Factory показывает configurable states + dispatch + event subscriptions + resumable human/deployment waits; GH Agentic Workflows демонстрирует separation of agent proposal from privileged write actions.
4. **Multi-agent не следует принимать как обязательное свойство каждой задачи.** Практические материалы OpenHands/Codex и Cognition подчёркивают выигрыш от read-heavy/independent subtasks и отдельного контекста; concurrent edits по одним files/contracts добавляют конфликты и merge overhead. Сначала проектируется task graph и ownership write surface, затем допустимые места fan-out.

### Предварительная рекомендация — не решение о выборе продукта

Пока не выбирать «одну платформу как всю фабрику». Разделить будущую архитектуру на два логических слоя:

- **Factory control plane (наш проектный контракт):** source adapters, source-neutral task identity/snapshot, task lifecycle/state, stages, release/branch policy, approvals, task artifacts, semantic architecture delta provenance, audit/evals.
- **Replaceable execution plane:** один coding-agent runtime или управляемая платформа, работающая в ограниченной workspace и возвращающая typed output/evidence/patch. Multi-agent delegation включается только в шагах с безопасно делимым scope.

Затем проверять кандидатов по deployment/data constraints и операциям: Factory/Devin для наиболее готовой коммерческой платформы; GitHub Agentic Workflows для GitHub-centric repository automations; OpenHands для собственно расширяемого слоя; Symphony/PF как reference designs. Это гипотеза разделения ответственности, требует отдельного обсуждения.

## 5. Как продолжить ресёрч без запуска пилота

Пока наш task lifecycle не спроектирован, делать не product bake-off и не execution pilot, а **requirements-led desk review**:

1. Закрыть верхнеуровневый flow и state transitions в манифесте.
2. Составить список обязательных capabilities/constraints и разделить `must`, `should`, `unknown`.
3. Для 3–4 коротко выбранных кандидатов запросить/проверить одинаковые факты: source adapters, task ID, branches/release, stage/artifact model, pause/resume/retry, permissions, audit, data region, human review, cost model и export/exit path.
4. Помечать каждую ячейку как `documented`, `vendor-confirm`, `not documented`; не выводить отсутствие возможности из молчания публичной страницы.
5. Только после этого решить, нужна ли одна платформа, custom control plane поверх runtime, или комбинация GitHub-native automations и отдельного task service.

Полевой прогон понадобится позже, когда есть согласованный flow и подходящая задача/репозиторий. До этого достаточно paper design review и vendor due diligence.

## Evidence и ограничения

- **Primary / vendor-owned:** официальная документация Factory, Cognition, GitHub, OpenHands и OpenAI; точна для заявленных интерфейсов/контрактов, не для независимой оценки пользы.
- **Internal reference case:** OpenAI Performance Factory — инженерная статья о собственной реализации; не продукт и не нейтральный архитектурный стандарт.
- **Draft/reference:** Symphony SPEC обозначен как Draft v1; Elixir implementation — evaluation-only/prototype по README на дату просмотра. Проверять статус/commit перед использованием.
- **Ограниченный scope:** не проводился hands-on test, security audit продукта, benchmark, pricing/contract review или разговор с sales. Не ранжировать по рекламным case studies/SWE benchmark без task mix и независимой проверки.
- **Freshness:** продуктовые страницы и feature availability меняются быстро. Повторно проверять лицензии, планы, preview/GA, ограничения и deployment перед procurement/implementation.

## Источники

Проверено 2026-11-21; URL ведущие на первичные материалы, если не отмечено иначе.

- Factory, Software Factory — https://factory.ai/product/software-factory
- Factory, Missions — https://docs.factory.com/missions/overview
- Factory, Automations — https://docs.factory.com/automations/custom
- Factory, Droid Exec — https://docs.factory.com/droid-exec/overview
- Cognition, Managed Devins — https://cognition.com/blog/devin-can-now-manage-devins
- Cognition, Multi-Agents: What’s Actually Working — https://cognition.com/blog/multi-agents-working
- Cognition, How Cognition Uses Devin to Build Devin — https://cognition.com/blog/how-cognition-uses-devin-to-build-devin
- GitHub, Agentic Workflows generally available (2026-10-28) — https://github.blog/changelog/2026-10-28-github-agentic-workflows-generally-available/
- GitHub, Agentic Workflows source — https://github.com/github/gh-aw
- GitHub, third-party coding agents — https://docs.github.com/en/copilot/concepts/agent-capabilities/about-agents/about-third-party-coding-agents
- GitHub, Copilot coding agent — https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent
- OpenHands, Introduction / component map — https://docs.openhands.dev/overview/introduction
- OpenHands, Automations — https://docs.openhands.dev/openhands/usage/automations/overview
- OpenHands, SDK — https://docs.openhands.dev/sdk
- OpenAI, Symphony SPEC — https://github.com/openai/symphony/blob/main/SPEC.md
- OpenAI, Symphony repository — https://github.com/openai/symphony
- OpenAI, Performance Factory (2026-11-19) — https://openai.com/index/how-openai-performance-factory-keeps-chatgpt-fast/
- OpenAI, Codex app — https://openai.com/index/introducing-the-codex-app/
- OpenAI, Agents API — https://openai.com/index/introducing-the-agents-api/
- OpenAI, Codex subagents — https://developers.openai.com/codex/subagents

## Связи

- [Корневой манифест](../../../Манифест агентной software factory.md) · [[Исследование software factory — пробелы и готовые практики]] · [[Архитектура агентной software factory]] · [[Операционная модель агентных команд]]
- [[Контракт задачи для агента]] · [[Исследование формата документации проекта и входящей задачи]] · [[Инструменты агентной среды]] · [[Управление контекстом многоагентных систем]] · [[Threat model агентной разработки]] · [[Evals и метрики агентной разработки]]
