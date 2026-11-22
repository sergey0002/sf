# План развития Agent-oriented Software Factory

**Статус:** проект дорожной карты 2.5 с конфигурируемыми путями и структурой артефактов задач

**Дата сверки:** 2026-11-22

**Объект:** переход от document/task kernel к безопасной evidence-driven software factory

**Принцип:** превосходство над OpenSpec и Spec Kit сначала доказывается на одинаковых сценариях, а не объявляется по числу функций.

**Как читать.** Для ручной доработки фабрики начните с §22. Конфигурация путей и размещение артефактов описаны в §23. Порядок релизов задан в §19, состав скиллов и команд — в §20, модель flow и подзадач — в §21. Контракт CLI описан в §17, форматы и контекст — в §16, ограничения реализации — в §15.

## 1. Назначение документа

Этот документ задаёт последовательность архитектурных решений и вертикальных срезов для модернизации проекта. Он не является обещанием сроков и не разрешает push, merge, deploy, доступ к секретам или внешнюю запись.

План должен привести к системе, которая:

- принимает задачи из UI, трекера или другого источника в единый типизированный контракт;
- хранит неизменяемый intent отдельно от изменяемого состояния и evidence;
- выбирает минимальный контекст из архитектуры, кода и справочников;
- выполняет bounded change в изолированном worktree;
- применяет command/path/network policy до выполнения;
- сохраняет проверяемое происхождение каждого решения и результата;
- отделяет автора изменения от независимого verifier;
- допускает автономность только по измеренному риску и качеству;
- продолжает работу после сбоя без переписывания истории;
- обнаруживает drift между intent, specs, architecture, code, tests и deployed state.

## 2. Результат аудита исходного плана

Исходный план содержал полезные идеи — constitution, clarify, delta specs, traceability, progressive disclosure и evals, — но не был безопасным implementation roadmap.

### 2.1 Критические проблемы

1. **Маркетинговая цель вместо проверяемой гипотезы.** Утверждения «лучше всех» и «12 из 12» не имели воспроизводимой baseline.
2. **Устаревшее сравнение.** OpenSpec и Spec Kit описывались по ранним версиям и уже поддерживают больше workflow, расширений и артефактов.
3. **Завышенный статус проекта.** Специфицированные model routing, execution и agent-friendly возможности отмечались как реализованные.
4. **Feature list вместо dependency graph.** MCP, model invoke и semantic-команды планировались раньше sandbox, CI, evidence и approval.
5. **Смешение агента и CLI.** Clarification и semantic code/spec analysis ошибочно назначались детерминированному CLI.
6. **Изменяемый canonical input.** Ответы clarify предлагалось дописывать в исходный `task.json`, что разрушает provenance входа.
7. **Небезопасное применение delta.** Не были определены base revision, approval attestation, dry-run, conflict, idempotency и rollback.
8. **Аллокатор без concurrency model.** Последовательный YAML-реестр не решает коллизии между процессами, worktrees и внешними источниками.
9. **Неверный Git hook.** `.git/hooks/pre-commit` не версионируется, а пример проверял только первый найденный task.
10. **Тестирование отложено.** Первые три фазы могли создать большой непроверенный контур.
11. **Нет trust zones.** Один субъект мог бы написать изменение, тесты, policy и сам подтвердить успех.
12. **Нет migration/recovery model.** Не определены schema versions, CAS, crash recovery, replay и совместимость старых задач.

### 2.2 Решение по аудиту

- Заменить календарные «недели» на dependency-ordered gates.
- Реализовывать только вертикальные срезы: контракт → механизм → negative tests → evidence → runbook.
- Semantic operations оставить skills/agent runtime; CLI должен собирать факты, валидировать, хранить и применять заранее разрешённые переходы.
- Выпускать v1.0 только после пилота, миграционных гарантий и повторяемых evals.

## 3. Честный baseline

### 3.1 Реализовано

- Arch CLI и конфигурационно управляемая task validation.
- Стабильная identity задач и подзадач.
- Типы задач, flows и prompt files.
- Architecture Markdown с typed frontmatter, stable IDs, links и generated index.
- Path/frontmatter validation и контроль свежести индекса.
- Task init/validate/status/diagnose/close и subtask lifecycle.
- 5 unit и 35 environment acceptance tests.

### 3.2 Частично реализовано

- Agent-friendly output envelope и семантические ошибки.
- Traceability-поля в `task.json`.
- Stage plans и verification records.
- Skills как инструкции.
- Architecture delta как описанный контракт.

### 3.3 Только специфицировано или отсутствует

- Packaging, versioned release и обязательный CI.
- Immutable task snapshot, event log, approval attestation и schema migrations.
- Worktree executor, sandbox и command/path/network enforcement.
- Независимый verifier и защищённый acceptance oracle.
- Product repo/test/runtime maps и drift detection.
- Model runtime/routing, MCP и source adapters.
- Evals, telemetry, cost accounting и controlled pilot.

Это различие должно отражаться в полях `status` и `implemented`; документация не должна превращать design intent в факт.

## 4. Актуальная конкурентная рамка

### 4.1 Что уже умеет OpenSpec

По официальной документации OpenSpec:

- разделяет current specs и change folders;
- использует proposal, delta specs, optional design и tasks;
- применяет `ADDED/MODIFIED/REMOVED` при archive;
- поддерживает explore/propose/apply, update/sync/verify/archive;
- предлагает core/expanded workflow profiles;
- поддерживает custom artifact schemas и dependency graph;
- выдаёт JSON/instructions для agent workflows.

Следовательно, delta specs и настраиваемые артефакты сами по себе не являются нашим конкурентным преимуществом.

### 4.2 Что уже умеет Spec Kit

По официальной документации Spec Kit:

- поддерживает constitution → specify → plan → tasks → implement → converge;
- добавляет clarify, checklist и read-only analyze;
- имеет процессы для feature, bugfix и idea assessment;
- поддерживает integrations с coding agents;
- имеет extensions, hooks/runtime events, presets, workflows, overlays, bundles и catalogs.

Следовательно, constitution, clarify и converge сначала нужно качественно **сопоставить**, а не объявлять уникальными.

### 4.3 Где проект может доказуемо стать лучше

Потенциальные дифференциаторы:

1. Типизированный intake из tracker/chat/UI с provenance, risk и authority.
2. Immutable intent + append-only events + separate state/evidence.
3. Capability/architecture knowledge layer со stable IDs и doc↔code links.
4. Deny-by-default worktree executor с command/path/network/secret policy.
5. Evidence chain: task digest, base/head commits, command, environment, logs/artifact digests, CI identity и human approval.
6. Независимые audit/adjudication/repair/verification trust zones.
7. Policy gates, которые блокируют переход, а не только предупреждают.
8. Context routing через MOC/index/code graph с измерением token budget и retrieval quality.
9. Resume/replay/crash recovery и идемпотентные внешние эффекты.
10. Risk-tiered autonomy с promotion только после hidden-oracle evals.
11. Operational loop: rollout, observation, rollback и feedback в specs.

Преимущество считается доказанным только для конкретного сценария, модели, бюджета и опубликованного benchmark protocol.

## 5. Архитектурные инварианты

1. **Один canonical input, несколько производных артефактов.** `task.json` — нормализованный intent, но не state, log или evidence.
2. **CLI не принимает смысловых решений.** Он валидирует, индексирует, фиксирует события, применяет policy и запускает разрешённые механизмы.
3. **Agent output — proposal.** Acceptance определяют protected checks, verifier и полномочный владелец.
4. **Audit-first, repair-second.** Discovery read-only; mutation начинается только после triage и scope lock.
5. **Один writer на контракт/файл.** Параллелить независимый анализ, сериализовать пересекающиеся мутации.
6. **Fail closed.** Ошибка/неполная coverage не означает «чисто»; это `inconclusive`.
7. **Policy и oracle защищены от repair actor.** Изменения policy/tests/workflows требуют отдельного review.
8. **Внешние эффекты deny-by-default.** Push, merge, deploy, tracker write и secret access требуют явного gate.
9. **Все переходы трассируемы.** Actor, input version/digest, permissions, decision, evidence и timestamp обязательны.
10. **Retries только классифицированные.** Write operations требуют idempotency key; повтор одинаковой ошибки включает circuit breaker.
11. **Процесс адаптивен риску.** Quick path для low-risk, полный SDD/security path для high-risk.
12. **Каждая фаза мигрируема и обратима.** Schema change без migration/rollback не принимается.

## 6. Целевая архитектура

```text
source adapters
    ↓ immutable intake snapshot
task record + policy/risk classification
    ↓
context router ── architecture index / repo graph / contracts / test map
    ↓
durable workflow state machine
    ├─ read-only audit/research
    ├─ adjudication + scope lock
    ├─ isolated worktree repair
    ├─ independent verification
    └─ human approval
    ↓
PR / staged delivery / observation / rollback
    ↓
events + evidence + spec/architecture drift feedback
```

### 6.1 Минимальные trust zones

| Зона | Права | Результат |
|---|---|---|
| Intake/context | Read external, write snapshot | Typed task intent + provenance |
| Auditor | Read-only repo/specs/graph | Findings с location/evidence/confidence |
| Adjudicator | Read findings/baseline | Accepted/rejected/needs-human decision |
| Repair | Scoped write в одном worktree | Minimal patch; без merge/deploy |
| Verifier | Read patch, run protected checks | Pass/fail evidence; patch не меняет |
| Human/policy owner | Approve high-risk/external effect | Attributable approval |

### 6.2 Целевая модель task record

```text
<tasks_root>/<task_key>/
├── task.json                 # immutable normalized intent + source digest
├── state.json                # с введением сохраняемых переходов
├── events.jsonl              # с введением журнала переходов
├── attachments/              # исходные материалы задачи
├── research/                 # исследовательские заметки задачи
├── subtasks/<subtask_id>/    # самостоятельные результаты
└── stage<N>/
    ├── plan.md
    ├── verification.json
    ├── diff/                 # снимок изменений при необходимости
    └── architecture-delta/   # предложение к каноническим документам
```

Сохраняем формат `stageN/`. Расположение и правила для артефактов описаны в §23.

### 6.3 Состояния верхнего уровня

```text
intake → clarified → scoped → planned → executing → verifying → review → completed
   └──────────────→ needs-human / rejected / failed / timed-out / rolled-back
```

Для каждого перехода нужна таблица:

`from | event | guard | actor | action | artifact/evidence | to | retry/stop/owner`.

## 7. Dependency-ordered roadmap

Этапы ниже описывают зависимости целевых возможностей. Состав конкретных выпусков и порядок внедрения определены в §19–20. Для каждого среза определить проверяемый контракт, тесты и необходимые шаги совместимости, обновления документации и восстановления.

### Этап 0 — Baseline, упаковка и решения

**Цель:** сделать текущий kernel воспроизводимым и измеримым.

Deliverables:

- inventory `implemented / partial / specified / absent`;
- ADR: task record, workflow state, approvals, allocator, execution boundary;
- `pyproject.toml`, console entry point, pinned dependencies и version output;
- локальный versioned gate `bash doc/tests/run.sh --gate` с unit, acceptance, architecture validation, index freshness и path checks;
- локальная проверка перед коммитом как ускорение, но не замена gate;
- **CI/CD и Git-hosted workflow запрещены** решением владельца 2026-11-22: никаких `.github/workflows/`, GitLab CI, Jenkinsfile и аналогов;
- schema version policy и fixtures предыдущей версии;
- benchmark corpus и baseline текущего kernel;
- threat-model baseline и список protected paths.

Не делать:

- model invoke, MCP write access, auto-allocation;
- semantic «analyze» внутри CLI;
- обязательный новый artifact без migration.

**Exit gate**

- установка и CLI воспроизводятся из clean checkout;
- локальный gate запускает существующие unit и acceptance тесты;
- dependency versions зафиксированы;
- benchmark tasks, oracle и scoring versioned;
- конкурентное утверждение содержит source, date, scenario и result.

### Этап 1 — Durable task record

**Цель:** отделить intent от lifecycle и сделать изменения crash-safe.

Deliverables:

- immutable `task.json` с `schema_version`, source revision/digest;
- `state.json`, append-only `events.jsonl`, typed approvals;
- optimistic concurrency/CAS и revision conflicts;
- idempotency keys для mutations;
- schema migration/validate/replay/doctor commands;
- clarify как skill: вопросы формулирует агент, CLI валидирует answer artifact и записывает event;
- recovery после обрыва записи.

**Exit gate**

- старые fixtures мигрируются без потерь и повторная миграция идемпотентна;
- intent нельзя переписать обычной lifecycle-командой;
- concurrent update обнаруживается;
- corrupted/partial event не материализуется как успешное состояние;
- replay даёт тот же state и digest.

### Этап 2 — Living specifications и policy

**Цель:** получить проверяемый spec lifecycle без тяжёлой церемонии для простых задач.

Deliverables:

- versioned project principles/policy, а не декоративная constitution;
- capability specs со stable requirement IDs;
- delta operations `ADDED/MODIFIED/REMOVED/RENAMED`;
- base revision, dry-run, conflict detection, apply record и rollback для docs delta;
- EARS как optional authoring profile, не keyword regex;
- bidirectional traceability:
  `requirement → design → task → changed files → tests → evidence`;
- verification method на requirement: Test/Demonstration/Inspection/Analysis;
- structural policy CLI и отдельный semantic review skill;
- quick/standard/high-risk profiles.

**Exit gate**

- delta применяется только к ожидаемой base revision;
- conflict не меняет canonical docs;
- каждый MUST/SHALL имеет owner, verification method и trace link;
- low-risk задача не обязана создавать пустые proposal/design документы;
- stale/orphan requirement обнаруживается в CI.

### Этап 3 — Safe single-task executor

**Цель:** безопасно выполнить один bounded change в одном локальном репозитории.

Deliverables:

- отдельный worktree и зафиксированный base commit;
- allow/deny policy для commands, paths, processes и network;
- timeout, resource budget, cancellation и cleanup;
- secret isolation/redaction;
- dirty-tree/collision protection;
- immutable execution evidence: command, cwd, environment fingerprint, exit code, timestamps, stdout/stderr/artifact digests;
- approval gate до внешних эффектов;
- rollback/reconcile после crash;
- запрет repair actor менять protected policy/oracle.

**Exit gate**

- negative tests блокируют path traversal, forbidden command, unexpected network, secret leakage, push/deploy без approval;
- interrupted run безопасно resume/reconcile;
- повтор команды с тем же idempotency key не дублирует эффект;
- verifier может воспроизвести evidence из clean environment.

### Этап 4 — Agent harness и независимая verification

**Цель:** добавить semantic intelligence поверх безопасного механизма.

Deliverables:

- context manifest с source/version/digest/ACL/freshness;
- progressive disclosure: MOC → domain → symbol/graph → source;
- token/context budget и причины каждого retrieval;
- каталог навыков с условиями выбора, ссылками и проверками срабатывания. Версии и совместимость отслеживать вместе с релизом;
- семантические операции распределить по существующим навыкам, добавить `review-change` для сверки до и после реализации. Состав и условия выделения других навыков описаны в §20;
- independent verifier, которому недоступна mutation patch;
- hidden-oracle eval corpus;
- regression eval при смене prompt, skill, model, tools или policy;
- model routing только после baseline.

CLI contract:

- JSON envelope; stdout=data, stderr=diagnostics;
- semantic exit codes и `retryable`;
- `--brief`, `--fields`, `--quiet`, `--human`;
- `--dry-run`, actionable errors, doctor/replay;
- noninteractive execution.

**Exit gate**

- skill имеет must-trigger/must-not-trigger tests;
- одинаковый eval повторяется в fresh sandbox;
- output содержит provenance и uncertainty;
- quality не хуже baseline при заданном cost/context budget;
- verifier обнаруживает ослабление tests/policy/workflows/thresholds.

### Этап 5 — Read-only integrations, затем controlled write

**Цель:** подключить внешние источники без расширения blast radius.

Deliverables:

- source adapter contract и immutable snapshots;
- сначала read-only Jira/Git/MCP adapters;
- tool provenance, allowlist, auth scopes, timeout/output limits;
- prompt-injection handling для task/docs/tool output;
- revoked credential, rate-limit, duplicate delivery и stale revision handling;
- write preview + explicit approval + idempotency key;
- outbox/reconciliation для внешней записи.

**Exit gate**

- malicious external content не меняет policy/authority;
- потерянный ответ и повтор webhook не создают дубликат;
- revoked/expired credentials дают controlled state;
- write-back воспроизводимо связан с approval и task event.

### Этап 6 — Pilot, сравнение и релиз

**Цель:** доказать полезность на реальных, ограниченных задачах.

Entry criteria:

- один low-risk репозиторий и владелец;
- deterministic CI и заранее заданный oracle;
- sandbox, rollback и kill switch;
- eval baseline и cost budget;
- запрет auto-merge/deploy.

Pilot sequence:

1. Observe: read-only audit и evidence-rich suggestions.
2. Propose: draft patch/PR, human applies/approves.
3. Bounded repair: один класс low-risk задач.
4. Расширять автономность по одному классу только после promotion gate.

Release policy:

- первые пилоты — `v0.x`;
- `v1.0` требует стабильной schema/migration policy, повторяемых evals, security review и успешного recovery exercise.

## 8. Как измерять «лучше OpenSpec и Spec Kit»

### 8.1 Сценарии

Сравнивать на одинаковых исходных ревизиях, моделях, лимитах, базовых инструментах и критериях приёмки. Использовать штатные prompts каждого варианта и фиксировать их версии. Состав сравнения указан в §18.

1. greenfield feature;
2. brownfield bugfix;
3. architecture-changing feature;
4. ambiguous intake;
5. interrupted/resumed task;
6. malicious/untrusted input;
7. conflicting parallel changes;
8. stale specification.

### 8.2 Метрики

| Группа | Метрики |
|---|---|
| Outcome | acceptance pass rate, escaped regressions, task success |
| Human effort | corrections, review rounds, intervention time |
| Traceability | requirements linked to tests/code/evidence, orphan rate |
| Efficiency | lead time, tokens, API cost, context loaded |
| Reliability | repeated-run variance, resume success, flaky outcomes |
| Safety | prevented policy violations, unauthorized effects, secret exposure |
| Maintainability | stale/conflicting artifacts, migration success, setup time |

Не использовать как главную цель: PR count, строки кода, raw coverage, число агентов, auto-fix rate или количество CLI-команд.

### 8.3 Promotion gate

Преимущество формулируется узко, например:

> В сценарии brownfield bugfix версия X снизила median human corrections на N% при не большей regression rate и стоимости, чем зафиксированные версии OpenSpec и Spec Kit.

Результат публикуется вместе с corpus version, commits, environment, model/tool versions, raw runs и confidence/variance. До этого допустима только формулировка «гипотеза дифференциатора».

## 9. Threat model и negative-test matrix

| Угроза | Обязательный контроль | Проверка |
|---|---|---|
| Prompt injection из issue/docs/code | Treat as data, provenance, policy precedence | Malicious fixture |
| Path traversal/symlink escape | Canonical path + allowlist | Escape attempts |
| Shell injection | Structured argv, no implicit shell | Metacharacter corpus |
| Secret leakage | Scoped secret store + redaction | Canary secret test |
| Oracle weakening | Protected paths + independent review | Delete/skip/threshold mutations |
| Unauthorized push/deploy | Separate identity + approval gate | Denied side-effect test |
| Duplicate external write | Idempotency/outbox | Replay delivery |
| Partial scan reported clean | Coverage status required | Interrupted scanner |
| Endless repair loop | Attempts/time/cost limit | Repeated failure |
| Dependency/tool drift | Pin/digest/SBOM + replay eval | Upgrade canary |

High-risk auth, payment, crypto, IAM, destructive schema and release-policy changes не допускаются к auto-fix на ранних уровнях.

## 10. Решения, которые нельзя принять молча

До реализации требуются ADR/owner decision:

- совместимость существующего формата `stageN/` при миграции состояния;
- event storage and atomicity;
- source of task-number uniqueness и concurrency model;
- approval identity/signature model;
- sandbox technology и network policy;
- protected oracle ownership;
- supported product repo topology;
- runtime/workflow engine;
- retention/privacy policy evidence;
- критерии перехода от v0.x к v1.0.

Если выбор меняет permissions, target repo/release, acceptance meaning или необратимый эффект, работа останавливается до решения владельца.

## 11. Антипаттерны, запрещённые этим планом

- «Больше агентов означает выше assurance».
- Один агент пишет patch, ослабляет tests/policy и сам подтверждает успех.
- Chat transcript как единственный workflow state.
- Общая mutable memory без owner, provenance, ACL и TTL.
- Загрузка всей документации в prompt.
- Finding без location, reachability, reproduction или oracle.
- Auto-retry write/deploy без idempotency.
- Перезапись specs задним числом вместо delta/event.
- Обязательная большая спецификация для тривиальной low-risk задачи.
- MCP/model integration до sandbox, policy и evidence.
- Заявление «лучше» без одинакового benchmark и опубликованных результатов.

## 12. Traceability плана

Перед реализацией каждый этап должен быть связан с существующими architecture IDs и открытыми ограничениями. Минимальная карта:

| План | Текущий проектный контекст |
|---|---|
| Task record/state/events | `DOM-task-lifecycle`, `ENT-task-input`, stage/evidence entities |
| Context routing | `DOM-project-knowledge`, architecture index |
| Executor/verifier | `DOM-execution-verification`, `CAP-single-agent-execution` |
| Model routing | `DOM-model-routing`, только после eval baseline |
| Security/policy | `VIEW-security`, `VIEW-open-constraints` |
| CLI contract | `SPEC-cli-implementation`, command/validation registries |

Первое изменение каждого этапа — уточнить точные IDs через generated index и создать task-specific architecture delta.

## 13. Источники

### 13.1 Локальные материалы `data/`

- `data/machinedocs-encyclopedia/Практики/Архитектура агентной software factory.md`
- `data/machinedocs-encyclopedia/Практики/Сквозной цикл разработки.md`
- `data/machinedocs-encyclopedia/Практики/Управление контекстом многоагентных систем.md`
- `data/machinedocs-encyclopedia/Практики/Harness-инжиниринг.md`
- `data/machinedocs-encyclopedia/Практики/Evals и метрики агентной разработки.md`
- `data/machinedocs-encyclopedia/Практики/Threat model агентной разработки.md`
- `data/machinedocs-encyclopedia/Практики/Безопасный деплой агентами.md`
- `data/sdd-encyclopedia/Процессы/Workflow SDD.md`
- `data/sdd-encyclopedia/Процессы/SDD в CI-CD.md`
- `data/sdd-research/06-качество-и-трассируемость.md`
- `data/sdd-research/09-bdd-исполняемые-спеки.md`
- `data/sdd-research/11-sdd-в-ci-cd.md`
- `data/cli-skills-encyclopedia/Практики/Agent-Friendly CLI Design.md`
- `data/cli-skills-encyclopedia/Практики/Безопасность CLI для агентов.md`
- `data/cli-skills-encyclopedia/Практики/Тестирование скиллов.md`

### 13.2 Официальные конкурентные источники

- [OpenSpec concepts](https://github.com/Fission-AI/OpenSpec/blob/main/docs/concepts.md)
- [OpenSpec workflows](https://github.com/Fission-AI/OpenSpec/blob/main/docs/workflows.md)
- [OpenSpec CLI](https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md)
- [OpenSpec custom schemas](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/customize/schemas.md)
- [GitHub Spec Kit README](https://github.com/github/spec-kit/blob/main/README.md)
- [GitHub Spec Kit quickstart](https://github.github.com/spec-kit/quickstart)

Официальные возможности конкурентов нужно перепроверять перед каждым benchmark release. Их отсутствие в этом документе не доказывает отсутствие в продукте.

## 14. Следующее действие

Не начинать с constitution или новых semantic CLI-команд.

Выпуски и порядок реализации определены в §19. Для первого пакета нужны следующие работы.

1. открыть зарегистрированный багфикс `UI-0011` по §22 и §24;
2. создать verified inventory текущих capabilities;
3. зафиксировать контракт `diagnose` и `close` и проверить сбои записи;
4. добавить упаковку, воспроизводимые зависимости и CI;
5. зафиксировать набор задач для сравнения и исходные замеры;
6. оценить необходимость отдельного состояния и журнала после проверки первого среза.

Это создаёт фундамент, на котором последующие specs, agents и integrations можно развивать без потери истории, безопасности и измеримости.

## 15. Аудит текущей системы

Срез относится к текущему checkout. Проверены поверхности CLI, обработчики, архитектурные форматы, структура задач, политики YAML, проектные навыки, тесты и упаковка. Команды `validate`, `index check`, `docs paths --check` и `scan --scope all --brief` прошли. Этот результат описывает проверки локальных данных и документации.

Приоритеты в таблице относятся к выпуску первого поддерживаемого kernel. P0 закрывает риск ошибочного результата или потери данных, P1 даёт основной выигрыш в применимости, P2 расширяет возможности после подтверждения спроса.

| Подсистема | Что подтверждено сейчас | Разрыв и критерий исправления |
|---|---|---|
| Intake и identity | CLI нормализует ключ с указанным номером, создаёт запись, проверяет коллизии при инициализации. | **P1.** Определить область уникальности, связи с внешним ID и условия повторного импорта. Сохранить ручное выделение до необходимости многопользовательской записи. Повтор одного входа даёт тот же результат либо явный конфликт. |
| Типы и flows | Девять типов, YAML-конфиги, стартовые prompts, проверка совместимости типа и потока. | **P1.** Объявленные шаги и gates требуют отдельного исполняемого контракта. `close_policy` отображается в CLI, а закрытие использует собственную проверку. Каждое нормативное поле получает потребителя и тест либо обозначается как подсказка. |
| Закрытие задачи | `_task_close` проверяет непосредственные каталоги подзадач и выставляет `phase: completed`. При отсутствии каталога проверка подзадач проходит. | **P0.** Свести `diagnose` и `close` к общему вычислению готовности. Сверять объявленные подзадачи с диском, валидировать родительскую запись и обязательные артефакты. Учитывать принятую политику подтверждения владельцем. Проверить отсутствие записи при отказе. [Обработчик](doc/tools/arch/cli/commands/builtin.py#L1347) · [Проверка подзадач](doc/tools/arch/validation.py#L541) |
| Запись и восстановление | `decompose` пишет записи детей и родителя отдельными операциями, `close` обновляет файл напрямую. | **P0.** Сначала атомарная замена одиночной записи и обнаружение незавершённой составной записи. Тесты на прерывание, повтор и конфликт ревизии. Полноценный журнал нужен, когда появляется подтверждённая потребность в восстановлении и параллельной работе. [Запись подзадач](doc/tools/arch/cli/commands/builtin.py#L1203) |
| Workspace и выпуск | `task workspace` валидирует задачу и возвращает подсказку ветки. Сборка и выпуск продукта описаны в документации. | **P1.** Отразить read-only поведение в help. Для пилота вынести назначение рабочего каталога и запуск проверок за границу task metadata. Worktree фиксирует рабочую копию, изоляцию процессов и сети обеспечивает отдельная среда. [Workspace](doc/tools/arch/cli/commands/builtin.py#L1114) |
| Проектные знания | Stable IDs, ссылки, frontmatter, `related`, схемы metadata и generated index. `scan` даёт структурную диагностику. | **P1.** Отдельно показывать целостность, свежесть относительно кода и подтверждённость поведения. Проверять ссылки на symbol, requirement и test с явным состоянием неполного покрытия. |
| Skills и проверки | Четыре проектных навыка и отдельные prompts для типов и потоков. Тесты проверяют локальный CLI и часть контрактов навыков. | **P1.** Связать инструкцию с условиями загрузки и машиночитаемыми входами/результатами. Добавить проверки выбора навыка и наблюдаемых исходов задачи. Тесты закрытия, повторного запуска и форматов ошибок приоритетнее общего процента покрытия. |
| Установка и CI | Запуск из checkout, `requirements.txt`, shell-скрипт тестов. Скрипт пересобирает индекс перед проверкой свежести. | **P0.** CI сначала проверяет закоммиченный индекс без записи. Отдельная проверка воспроизводимости пересобирает его во временном дереве. Проверить установку версионированного пакета вне исходного checkout и согласовать версию CLI с метаданными пакета. [Тестовый скрипт](doc/tests/run.sh) |
| Независимая приёмка | Стадийные записи и поле `authority` фиксируют заявленные сведения. | **P1.** Разделить декларацию полномочий и фактический контроль. Связывать результат проверки с ревизией, версией критерия приёмки и исполнителем. Изменение diff инвалидирует применимость старого результата и одобрения. |

## 16. Архитектура документации и форматы

`doc/` и `doc/architecture/` в этом разделе обозначают текущие пути по умолчанию. Фактические корни определяет проектный YAML (§23).

Сохранить `doc/` как рабочую область. Улучшить границы источников внутри неё через три уровня контекста. Первый уровень — краткие инструкции и карта входов в README и применимых AGENTS.md. Второй — оглавление домена и краткие метаданные. Третий — точечная загрузка контракта, примера, исходника или доказательства. Для поиска по коду использовать граф и проверять найденное по исходнику. Для справочного поиска идти от [корневого MOC](data/README.md) к нужной энциклопедии. [Index-First](<data/machinedocs-encyclopedia/Архитектура/Index-First подход.md>) · [Codified Context](<data/machinedocs-encyclopedia/Архитектура/Codified Context (3 яруса).md>)

| Формат сегодня | Решение для следующего выпуска | Проверка |
|---|---|---|
| Markdown с YAML frontmatter для domain, entity, flow, capability, ADR и system views | Сохранить язык предметной области в Markdown. В метаданных использовать типизированные отношения только там, где они нужны для навигации или проверок. Уточнить отдельно статус принятия документа и состояние реализации capability. | Перенос страницы сохраняет ID и связи. Опечатка в обязательной метаданной или битая ссылка дают точную диагностику. |
| JSON Schema metadata и индекса, плюс JSON-описания формы Markdown-тела | Явно описать уровни проверки. Metadata schema проверяет поля, правила формы — наличие секций и таблиц, отдельные проверки — ссылки и инварианты. `additionalProperties: true`, нетипизированный `implemented` в document schema и пропуск типа без body rules снижают силу зелёного результата. Начать со строгих требований к новым/изменённым записям и задокументированных расширений. | Тесты на неверный тип метаданных, отсутствующий профиль и ложноположительное совпадение секции в примере. Указать coverage правил по типам. [Схема](doc/architecture/schemas/document.schema.json) · [Проверка тела](doc/tools/arch/body_validation.py#L63) |
| `index.json`, Markdown-ссылки, Mermaid, в справочнике — wiki-ссылки | Индекс — производная проекция. Оставить компактный поиск по ID, типу и домену, полные данные читать по запросу. Mermaid использовать для ориентации. Исполняемые переходы описывать в одном машинном источнике, диаграмму выводить из него при достаточной пользе. Wiki-ссылки оставить на стороне справочника. | В чистом checkout сборка индекса воспроизводима. Переходы, которые документирует диаграмма, доступны по ID. Старые пути в справочнике сверяются с checkout при обращении. |
| `task.json`, `stageN/plan.md`, `verification.json` | Сохранить legacy layout и единственный вход. Сначала версионировать JSON и описать владение полями, затем отделить снимок intent от состояния и доказательств. Markdown-план хранит порядок работы и ссылки на требования, а каталог стадий сохраняет привычную навигацию. | Старая задача читается до миграции, перенос с предпросмотром сохраняет исторические поля. Доказательство устаревает при изменении проверенной ревизии. |
| Capability specs, архитектурные delta, ADR | Capability фиксирует наблюдаемое поведение с ID требования и проверкой. Delta описывает запланированное изменение относительно базы. ADR фиксирует выбор, альтернативы, последствия и замену решения. EARS и Given/When/Then применять там, где они проясняют условие и исход. | Один пример проходит от requirement до теста и принятой delta. Две несовместимые delta на одну базу обнаруживаются перед применением. |
| YAML task-conf, `SKILL.md`, prompts | YAML определяет проверяемые ограничения и выбор артефактов. Skill задаёт семантические действия, короткое описание задаёт условия загрузки. Детальные примеры и исследования открываются по ссылке. | Несовместимые конфиги дают объяснимую ошибку. Положительные и отрицательные тесты проверяют выбор навыка. |

Для свежести хранить владельца, версию отправной точки и связь с проверяющим тестом там, где это влияет на решение. Дата последней проверки — сигнал для ревью. Изменение связанного интерфейса, схемы или команды в diff — более сильный сигнал. Для brownfield начать с предупреждений по унаследованному долгу и блокировать новые нарушения в критичных связях. [Актуальность и staleness](<data/machinedocs-encyclopedia/Практики/Актуальность и staleness.md>) · [Качество и трассируемость](data/sdd-research/06-качество-и-трассируемость.md)

## 17. Модульная CLI и экономия контекста

### 17.1 Что сохранить и что разнести

Сохранить тонкий entry point, `Command`, registry и единый envelope. Сейчас регистрация зависит от импортов, registry молча перезаписывает одноимённую команду, parser строит все ветки заранее, `ArchitectureStore` создаётся для любого вызова. В `builtin.py` 1380 строк с обработчиками документации, scan и lifecycle. Это оправдывает разбиение по зонам ответственности при сохранении прежних имён команд. [Сборка CLI](doc/tools/arch/cli/app.py) · [Реестр](doc/tools/arch/cli/commands/registry.py)

Предлагаемая структура — модули команд `docs`, `task`, `scan` и `index`, вызовы сценариев в прикладном слое и отдельные адаптеры файлов, Git и проверок. Правила закрытия, схем и миграций тестировать напрямую через прикладной интерфейс. Запретить дубли команд в registry. Зависимости создавать по потребности выбранного сценария. Ограничиться встроенными модулями до появления второго реального потребителя расширений. Смену фреймворка оценивать по времени старта, совместимости и объёму поддержки.

### 17.2 Контракт агентного вывода

- В машинном режиме одна компактная JSON-запись на stdout, диагностические сообщения в stderr, согласованные коды процесса и поля результата. Покрыть успех, неверные аргументы, отсутствие объекта, блокировку, временную ошибку и неполную проверку. Сейчас `task close --json` на одном из путей отказа выводит обычный текст, а флаги `scan` и `task` имеют разный охват.
- Зафиксировать публичные поля и версию схемы. Для ошибок выдавать код, существенную причину, путь или ID и подсказку. Вывод traceback включать по запросу. Сохранить совместимость существующих `--json` и текстовых вызовов при миграции.
- Для больших результатов ввести ограниченную выборку по типу, домену, стадии и уровню детализации. Показывать признак обрезки, следующий курсор или точную ссылку для догрузки. Эффект `--brief` проверять на blocker и ошибке так же, как на успехе.
- Вывести краткий результат `status` / `diagnose` с причинами блокировки и ссылками на нужный контракт. Полный prompt, Markdown и лог загружать отдельно. Предпросмотр мутаций должен сообщать область записи и исходную ревизию. Полные логи доступны по ссылкам на артефакт, а ошибки подсказывают точечный следующий запрос.
- Выводить компактное описание команды из той же декларации, что используется для help и тестов. Машинное описание достаточно для одного действия, типовых кодов и доступных полей. Расширенный help сохраняет примеры для человека.

### 17.3 Измерение выигрыша

Зафиксировать cold-start, байты stdout, токены системного контекста и инструментальных ответов, число вызовов и долю задач с правильно найденным контрактом. Текущие размеры README и полного индекса около 17 и 26 КБ в UTF-8. Это данные о размере файлов, токены измеряются отдельно на реальных трассах. Сравнить текущий путь `list → show → validate` с адресной выборкой и убедиться, что сокращение вывода сохраняет точность решений и полноту диагностики. Тесты CLI проверяют stdout/stderr, exit codes, отсутствие интерактивных ожиданий и совместимость старых сценариев. [Agent-Friendly CLI Design](<data/cli-skills-encyclopedia/Практики/Agent-Friendly CLI Design.md>) · [Токен-эффективность](<data/cli-skills-encyclopedia/Практики/Токен-эффективность.md>) · [Тестирование CLI](<data/cli-skills-encyclopedia/Практики/Тестирование CLI.md>)

## 18. Как превзойти сочетание OpenSpec и Spec Kit

OpenSpec уже предлагает проектный контекст, диагностику его состояния и машинные инструкции для артефактов. Spec Kit уже предлагает уточнение, проверку согласованности и цикл convergence, а также отдельный процесс для багфиксов. Сравнение начинается с рабочих сценариев этих инструментов, включая облегчённые профили. [OpenSpec CLI](https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md) · [OpenSpec Workflows](https://github.com/Fission-AI/OpenSpec/blob/main/docs/workflows.md) · [Spec Kit](https://github.com/github/spec-kit#spec-driven-development)

| Что соединяем | Что должно стать лучше в одной задаче | Как проверить |
|---|---|---|
| Уточнение и consistency review Spec Kit + живые спеки OpenSpec | Уточнённое требование, текущая capability, предлагаемая delta и проверка образуют одну цепочку ID. | После уточнения, смены базы и устаревания теста видны разные причины блокировки. |
| Быстрый OPSX-профиль + специализированные workflows Spec Kit | Малая задача проходит короткий путь с наблюдаемой приёмкой. Усложнение по риску сохраняет уже созданные артефакты. | Измерить время подготовки и объём прочитанного контекста при одинаковой полноте приёмки. |
| Agent-oriented CLI и интеграции обоих продуктов | Версионный контракт для одного следующего действия, объяснимый blocker и выборка контекста по домену. | Измерить успешность следующего действия, число повторных чтений, токены на принятую задачу и удобство восстановления. |
| Verify, converge и archive | Проверки привязаны к версии intent, delta и фактическому diff. Операция публикации видит, что изменилось после верификации. | Проверить конфликтующие изменения, возобновление прерванной задачи и устаревание результата. |

Сравнивать три рабочих варианта отдельно и четвёртым добавить комбинацию OpenSpec + Spec Kit с заранее зафиксированным распределением ответственности и общим handoff. Закрепить версии инструментов, профиль, модель, репозиторий, исходную ревизию, задачу, оборудование и лимиты. Сохранить штатные prompts каждого варианта. Один критерий приёмки и одинаковые полномочия применяются ко всем. Проводить повторные прогоны, включая ошибки и остановки, и публиковать размер выборки, разброс и стоимость настройки handoff.

Выигрыш подтверждён, если совместный baseline пройден по приёмке без ухудшения корректности и соблюдения полномочий, а заранее выбранная метрика показывает практически значимое улучшение. Порог и допустимые границы принять до прогона. При разнонаправленных результатах опубликовать преимущества по сценариям и компромиссы. Для пользователей обоих инструментов начать с импорта примеров с provenance и явным списком непереносимых полей.

## 19. Что выпускать и в каком порядке

| Выпуск | Объём | Условие готовности |
|---|---|---|
| **v0.1 — Task & Docs Kernel** | Устанавливаемая CLI, совместимый машинный вывод, CI без записи в checkout, устойчивые обновления задачи, согласованные `diagnose` / `close` и полный каталог текущих скиллов. | Установка из релизного артефакта, проверка старых fixtures, отказные сценарии, актуальный индекс и документация о границах поддержки. |
| **v0.2 — Living Specs** | Один сквозной сценарий `уточнение → изменение требования → delta → тест → evidence` плюс быстрый путь для документационной задачи. Адресная выборка контекста, структурная сверка дельты и доказательств, семантический `review-change`. Версионированные переходы, таблица выбора потока и зависимости подзадач для двух контрольных flow (§21). | Проверяемая трассировка, конфликт delta без записи, миграция с предпросмотром при изменении схемы, явная диагностика покрытия и пройденные сценарии §21.5. |
| **v0.3 — Assisted Pilot** | Один локальный репозиторий, ограниченный класс задач, оператор выбирает и подтверждает внешние действия. Независимая приёмка и восстановление. | Пройденные проверки изоляции и полномочий, повторяемый результат, тест восстановления и опубликованные измерения пилота. Пилот можно провести с ручным intake. |
| **v1.0 — Поддерживаемый контракт** | Версионированная совместимость CLI и схем, инструкция обновления и отката, поддерживаемые профили, релизный пакет. | Воспроизводимые установки и миграции, опубликованный сравнительный протокол и результаты по целевым сценариям. |

Начальный срез — тесты для закрытия и диагностики на временных задачах, единый расчёт блокировок, стабильный JSON-ответ и независимая проверка свежести в CI. После этого выделить lifecycle из `builtin.py` и пройти один вертикальный сценарий со спеками. Приоритет нового хранилища, общего runtime, автоматического аллокатора, интеграций и мультиагентности определить по результатам этих срезов. Смена корневой архитектуры оправдана, когда ADR показывает измеримый выигрыш в восстановлении, стоимости контекста или сопровождении и описывает совместимость и миграцию.

## 20. Что внедряем из OpenSpec и Spec Kit

Наши точки входа — `task_key`, назначенный flow и текущая стадия. OpenSpec даёт образец быстрого старта, выдачи следующего артефакта и переноса дельты в живую спецификацию. Spec Kit добавляет проверку качества требований до реализации и сверку результата после неё. Общая цепочка связывает требование, изменение и доказательство одним набором идентификаторов. [OpenSpec Commands](https://github.com/Fission-AI/OpenSpec/blob/main/docs/commands.md) · [OpenSpec CLI](https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md) · [Spec Kit SDD](https://github.github.com/spec-kit/reference/agentic-sdd.html)

### 20.1 Скиллы и профили

| Скилл или профиль | Что внедрить | Приёмка |
|---|---|---|
| `create-task` | Из `propose/new/ff` взять быстрый старт и подготовку только требуемых артефактов. Из `specify/clarify` взять наблюдаемое поведение, границы работы и вопросы, ответы на которые меняют scope или приёмку. | Малая понятная задача оформляется без пустых шаблонов. Блокирующая неоднозначность видна в плане, ответы связаны с версией входа. |
| `go-to-task` | Из `continue/apply/update` взять следующий доступный шаг и возобновление по текущим артефактам. Из `plan/tasks/implement` взять зависимости, проверяемые результаты шагов и фиксацию отклонений. | Новая сессия определяет стадию и блокировки по файлам задачи. Изменение scope требует пересмотра затронутого плана и применимости прежнего evidence. |
| `architecture-docs` | Из `sync` взять перенос принятой дельты в живую спецификацию. Использовать существующие stable IDs, capability docs и формат `architecture-delta`. Из `constitution` взять короткие проектные инварианты с проверками и ссылками на действующие контракты. | Дельта указывает базу, изменяемые требования, сценарии и тесты. Устаревшая база даёт конфликт до записи. |
| `document-session` | Из `archive` взять удобную историю завершённого изменения. Фиксировать принятые решения и ссылки на проверку в записи стадии. | По закрытой задаче можно найти принятую дельту, ревизию результата и evidence. |
| Новый `review-change` | До реализации объединить `checklist/analyze` в проверку качества и согласованности требований, плана и подзадач. После реализации объединить `verify/converge` в сверку требований, diff и результатов проверок. | Результат содержит ID требования, ссылку на основание, статус и оставшееся действие. Семантическое ревью и результат запуска тестов сохраняются как разные свидетельства. |
| `bugfix` | Перенести `assess/fix/test` в сценарий потока. Сначала подтвердить симптом, затем описать изменение, после него повторить исходную проверку. | Если исходный сценарий не был проверен, результат помечен как частичный. [Spec Kit Bug Fix](https://github.github.com/spec-kit/reference/agentic-bugfix.html) |
| `research-first` и `planning` | Перенести `explore` и `assess.intake/research/define/shape/decide` как выбираемые этапы. Зафиксировать проблему и критерий успеха, подобрать аргументы за и против, сравнить варианты и записать решение. | Исследование может закончиться передачей в реализацию, запросом уточнений или обоснованной остановкой. [Spec Kit Idea Assessment](https://github.github.com/spec-kit/reference/agentic-assessment.html) |
| Независимая верификация в пилоте | Выделить `verify-task`, когда появится отдельный исполнитель настроенных проверок и потребуется свой триггер для независимой приёмки. | Проверяющий получает критерии, diff и ссылку на проверяемую ревизию. Итог переиспользует машинное evidence проверки и показывает непокрытые требования. |

В `v0.1` добавить отсутствующую запись `architecture-docs` в индекс `doc/skills/README.md` и согласовать описания четырёх текущих скиллов с реальными командами. В `v0.2` добавить `review-change`, остальные практики встроить в существующие скиллы и prompts. Пример из `onboard` оформить как учебный сквозной сценарий с fixture. Отдельный скилл выделять при самостоятельном триггере, результате и повторном использовании. Для новых навыков проверить подходящие и неподходящие запросы. [Тестирование скиллов](<data/cli-skills-encyclopedia/Практики/Тестирование скиллов.md>)

### 20.2 CLI по выпускам

| Выпуск и операция | Что заимствуем | Контракт |
|---|---|---|
| **v0.1** · расширить `task diagnose --json` и `task close --dry-run --json` | OpenSpec `status/instructions` и предпросмотр завершения. | Один расчёт готовности. Код блокировки, ID или путь артефакта, следующий допустимый шаг. Предпросмотр показывает ожидаемое изменение. Фактическое закрытие повторно проверяет текущую ревизию. |
| **v0.1** · развить `scan`, `index check`, `list/show`, `--version` | OpenSpec `doctor/list/show/validate` и Spec Kit `check/version`. | Чёткие области проверки, стабильный результат для CI, версия из пакета, компактная выдача. Существующие способы вызова сохраняются. |
| **v0.2** · `task context <key> --stage N --json` | OpenSpec `context/instructions/templates` и Spec Kit `artifact list/info` и `preset resolve`. | Вернуть ревизию, активный flow и происхождение его выбора, ограниченный список контрактов и артефактов с причинами выбора. Полное тело читается отдельно. Недостающий источник виден в результате. |
| **v0.2** · `task delta check <key> --stage N --json` | Проверки OpenSpec перед `sync/archive`. | Проверить базу, операции, ID, ссылки и структурные конфликты. Начать с обычного review принятой дельты. Команду применения спроектировать отдельно после проверки конфликтов, конкурентной записи и восстановления. |
| **v0.2** · `task evidence check <key> --stage N --json` | Сверка реализации и артефактов из `verify/converge`. | Для каждого обязательного результата указать наличие, актуальность и ссылку на источник. Проверка структуры и ревизии дополняет семантическое ревью. |
| **v0.3** · `task verify <key> --stage N --json` | Явное состояние запуска подобно Spec Kit `workflow run/resume`. | Запустить заранее настроенные проверки в среде пилота, связать результат с ревизией и версией проверок. При прерывании восстановить фактическое состояние. Повтор завершённой проверки требует явного решения с учётом изменения входа. |

Названия новых команд рабочие. Закрепить их после прототипа сценария и тестов совместимости. Коды отказа, версия envelope и правила выборки общие для модулей. Команда показывает сведения, достаточные для решения, и ссылку для раскрытия деталей. Для агента измерять число вызовов, объём ответа и токены на принятую задачу. [Spec Kit Workflow CLI](https://github.github.com/spec-kit/workflows/cli.html) · [Spec Kit Artifacts](https://github.github.com/spec-kit/overview/artifacts.html) · [Токен-эффективность](<data/cli-skills-encyclopedia/Практики/Токен-эффективность.md>)

### 20.3 Первый сквозной сценарий и условия расширения

1. Взять одну небольшую задачу, которая меняет действующую capability. Зафиксировать исходный симптом или поведение, ID требования и проверяемую приёмку.
2. Пройти intake, уточнение, выбор контекста, подготовку дельты и ревью до реализации. Затем пройти локальное изменение, проверку результата и закрытие.
3. Повторить сценарий с изменившейся базой и устаревшим evidence. Диагностика должна различать причины и направлять агента к конкретному артефакту. Добавить docs-only fixture для быстрого пути.
4. Сравнить прогоны по протоколу §18. Результат использовать для выбора следующей возможности.

Пакетное архивирование из OpenSpec имеет смысл при параллельных дельтах. Внешние stores и worksets полезны при реальной работе с несколькими репозиториями. Spec Kit `integration/extension/preset/bundle` дают образцы версионирования и совместимости. Их отдельные команды и каталоги оправданы при появлении второго потребителя профилей или адаптеров. MCP нужен при запросе со стороны конкретного клиента и может использовать те же интерфейсы чтения, что и CLI. Автоматическое обновление, интерактивную панель и автодополнение можно оценить после первого поддерживаемого выпуска. [OpenSpec CLI](https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md) · [Spec Kit Integrations](https://github.github.com/spec-kit/integrations/cli.html) · [Spec Kit Bundles](https://github.github.com/spec-kit/bundles/cli.html)

## 21. Flow и подзадачи через CLI

При входе в задачу агент вызывает `task diagnose <key> --json`. CLI загружает задачу, версию flow, состояние подзадач и ссылки на доказательства. Ответ сообщает текущий шаг, доступные переходы, блокировки и ссылки на контекст, нужный именно сейчас. После работы агент передаёт один структурированный результат перехода и получает обновлённый краткий ответ. Так агенту не приходится вручную сводить список файлов, конфиги и историю.

### 21.1 Что вычисляет CLI

| Операция | Что делает CLI | Где нужно суждение |
|---|---|---|
| Выбор flow | Применяет таблицу решений к типизированным фактам. Возвращает ID правила и версии flow, варианты или недостающий факт. | Агент оценивает неоднозначный scope и предлагает тип задачи. Владелец уточняет цель, если от неё зависит выбор. Оценка поступает в CLI явным значением. |
| Переход | Находит переход по состоянию и событию, проверяет зарегистрированные условия, исходную ревизию и происхождение результата. | Агент формулирует план, меняет код или проводит семантическое ревью. Владелец даёт подтверждение там, где этого требует flow. |
| Подзадачи | Проверяет ссылки и циклы зависимостей, вычисляет `ready`, `blocked` и причины, сверяет записи с диском, сводит готовность родителя. | Агент определяет самостоятельные результаты, зависимости и критерии приёмки. CLI принимает готовый пакет декомпозиции. |
| Доказательства | Проверяет схему, обязательные ссылки, исход проверки и применимость к текущей ревизии. | Проверяющий оценивает полноту покрытия, если нужен экспертный вывод. Источник результата остаётся видимым. |

Тип задачи задаёт базовую политику. Flow уточняет её через явно разрешённые переопределения. Одна функция вычисляет итоговую политику для валидации, декомпозиции, диагностики и закрытия. Состояние ребёнка берётся из его записи. Родитель хранит ссылки, зависимости и обязательность результатов. На первом срезе проверяем зависимости между непосредственными детьми. Поддержку вложенных деревьев вводим после появления задачи, для которой этого недостаточно.

### 21.2 Минимальный интерфейс

- **`task diagnose <key> --json`** — точка входа и возобновления. По умолчанию выдаёт действующую версию flow, ревизию, шаг, доступные переходы, сводку подзадач и несколько блокировок. Для длинного списка возвращает общее количество и способ догрузки. Запрос полной истории остаётся отдельным.
- **`task decompose`** — сохранить совместимый вызов и добавить структурированный пакет, когда понадобятся зависимости. Проверить весь пакет до записи. Предпросмотр показывает, какие записи создаст CLI и какие связи изменятся. После записи вывести результат и готовые подзадачи.
- **`task advance`** — рабочее название общего перехода для контрольных `bugfix` и `docs-only` в `v0.2`. Вход содержит явное событие, ожидаемую ревизию и ссылки на результаты. CLI проверяет условия, фиксирует переход и возвращает ту же сводку, что `diagnose`. `task close` использует общий механизм проверки готовности и совместимый интерфейс.
- **`task context`** — догрузка, когда нужно прочитать контракт, prompt или evidence. Базовый ответ содержит ссылки и краткие причины выбора. Фильтр ограничивает выдачу текущим шагом, подзадачей или видом артефакта.

Например, после `checks.failed` CLI показывает состояние `fix`, ссылку на упавшую проверку и доступный переход `change.ready`. Если обязательная проверка отсутствует, `checks.passed` блокируется с указанием конкретного результата. При нескольких допустимых переходах CLI возвращает варианты и условия. Агент или оператор выбирает событие.

### 21.3 Как описывать и внедрять

Flow в YAML задаёт начальное состояние, состояния завершения, переходы по событиям и ID зарегистрированных проверок. Для шага указываются необходимые входы и ожидаемые результаты. Таблица выбора профиля хранится отдельно. Prompts объясняют методы исследования, реализации и ревью. Из YAML выводятся таблица переходов и схема для чтения человеком. `scan --scope task-conf` проверяет ссылки, неизвестные условия, недостижимые состояния и неоднозначные переходы. Цикл `verify → fix → verify` проверяется как штатный сценарий.

В `v0.1` начать с общего расчёта блокировок для `diagnose` и `close` и проверки пакета декомпозиции. В `v0.2` описать `bugfix/standard-implementation` и `docs/docs-only` в новом формате, добавить получение контекста шага и общий переход. Старые задачи читаются со своим форматом и продолжают работать до явной миграции.

Приёмка включает возобновление из чистой сессии, текущие и устаревшие доказательства, недостающую подзадачу, конфликт ревизий и короткий docs-only путь. Измерять число вызовов, объём загруженного контекста и токены на принятую задачу при той же полноте проверок. Целевой путь на границе шага — один вызов диагностики при входе, затем один вызов на запись результата и получение нового состояния. [Практики описания flow](<data/machinedocs-encyclopedia/Документация/Флоу.md>) · [Токен-эффективность](<data/cli-skills-encyclopedia/Практики/Токен-эффективность.md>)

### 21.4 Формат правил, переходов и подзадач

**Выбор flow.** Для каждого типа хранить отдельную таблицу решений с версией и стабильными ID правил. Строка содержит условия над типизированными входами, результат и основание. Например, `bugfix` с подтверждённым локальным симптомом и известным способом проверки может идти коротким путём, а задача с неясной причиной — через воспроизведение. Значения, требующие экспертной оценки, передаёт агент или владелец. Если конкурирующие правила совпали, CLI возвращает их ID. Если нужного факта нет, CLI указывает поле и допустимые значения. Безусловный маршрут применяется только при явно заданном fallback и известных фактах, достаточных для проверки остальных правил. [Стандарты описания flow](<data/sdd-encyclopedia/Флоу/Стандарты описания флоу.md>)

**Жизненный цикл.** Flow описывает начальное состояние, конечные состояния, доступные события и переходы. Каждая строка таблицы переходов соответствует одному YAML-описанию. Markdown и Mermaid генерируются из него. Для решений, которые требуют передачи работы, указать входы, ожидаемый результат и ссылку на проверку. В prompt остаются метод работы и примеры. В запущенной задаче сохранять разрешённый ID и версию flow, чтобы правка шаблона не меняла доступные переходы задним числом. [Контракт flow](doc/architecture/system/architecture-contract.md#L266) · [Контракт задачи и handoff](<data/machinedocs-encyclopedia/Практики/Контракт задачи для агента.md>)

| ID перехода | Из | Событие и источник | Условие и результат | В |
|---|---|---|---|---|
| `bug.recheck.failed` | `verify` | `checks.failed`, результат настроенной проверки | Проверка действительно выполнялась на текущей ревизии. Сохранить ссылку на отказ. | `fix` |
| `bug.recheck.passed` | `verify` | `checks.passed`, результат настроенной проверки | Повторно проверен исходный симптом. Обязательные проверки прошли на текущей ревизии. Сохранить ссылки на результаты. | `review` |

Если условия перехода не выполнены, CLI возвращает блокировку и сохраняет состояние. Например, устаревший результат при `checks.passed` требует повторной проверки. Реальная неудача при `checks.failed` ведёт по предусмотренной ветке. Условия ссылаются на зарегистрированные проверки. Произвольный код в YAML не требуется. Повтор того же события с тем же ключом и содержимым возвращает исходный результат. Повторное использование ключа с другим содержимым или новая запись поверх несовпадающей ревизии дают конфликт. [Отказоустойчивость flow](<data/machinedocs-encyclopedia/Практики/Исследование software factory — пробелы и готовые практики.md>)

**Подзадачи.** Заводить отдельную подзадачу для самостоятельного результата, который можно принять или передать. Модель содержит ID, ожидаемый результат, критерий приёмки, зависимости и признак обязательности. Обязательность декомпозиции проверяется к готовности плана. Каталог показывает принадлежность, граф показывает порядок готовности. Перед выдачей независимых работ для параллельного исполнения отдельно проверить пересечение областей изменения. При закрытии родителя CLI проверяет обязательные результаты детей и критерии самого родителя. [Параллельная работа агентов](<data/machinedocs-encyclopedia/Практики/Параллельная работа агентов.md>)

### 21.5 Проверка модели и порядок внедрения

1. **До изменений CLI** вручную пройти два контрольных flow по таблице переходов. Для значимых веток зафиксировать исходное состояние, событие, ожидаемые поля ответа и допустимую запись. Сценарии затем станут fixtures для автоматических проверок. [Исполняемые спецификации](data/sdd-research/09-bdd-исполняемые-спеки.md)
2. **В `v0.1`** сверить политику типа и flow, исправить расхождения между YAML и prompts, унифицировать расчёт готовности. В пакете декомпозиции конфликт выявляется до записи. Отдельно проверить восстановление после сбоя между записями.
3. **В `v0.2`** добавить схему нового YAML, контроль ссылок и достижимости, проверку неоднозначных правил, вычисление зависимостей и адресный контекст. Сценарий багфикса проверяет обратный переход. `docs-only` проверяет короткий путь с действующим минимумом артефактов.
4. **После двух контрольных flow** мигрировать оставшиеся в порядке общности. Сначала `feature` и `refactor`, затем исследовательские и плановые потоки. `jira-process` перевести после описания отображения входящей задачи на тип и flow. Совместимость уже запущенных задач проверяется отдельным fixture. Выбор внешнего workflow engine оценить после измерений восстановления и ожидания.

| Сценарий | Ожидаемый результат |
|---|---|
| Успешное завершение | CLI объясняет доступный шаг, принимает достаточные доказательства и связывает закрытие с проверенной ревизией. |
| Неизвестный факт или конфликт правил | CLI возвращает недостающие поля либо ID совпавших правил. Маршрут и состояние сохраняются до решения. |
| Проверка упала | Доступен предусмотренный возврат к исправлению со ссылкой на результат. |
| Доказательство устарело | Переход отклоняется, выдаётся причина и указание на требуемую проверку. |
| Обязательный ребёнок отсутствует или зависимость циклична | Видна конкретная подзадача или цепочка. Закрытие и некорректная декомпозиция блокируются. |
| Событие повторилось, ревизия изменилась или сессия прервалась | Повтор не создаёт второй записи. Конфликт виден по ревизии. После прерывания `diagnose` возвращает фактическое состояние и следующий шаг. |
| Простая документационная правка | Task record, нужная стадия и результат проверки достаточны для короткого пути. CLI не требует фиктивной декомпозиции. |

Проверку полноты переходов и тесты выходного контракта добавить в CI. Выигрыш оценивать по токенам на принятую задачу, числу вызовов и точности выбора шага на одинаковых сценариях до и после изменения. [Тестирование CLI](<data/cli-skills-encyclopedia/Практики/Тестирование CLI.md>)

## 22. Ручная доработка самой фабрики

Предлагается один общий flow `factory-change` для задач, которые меняют CLI, task-conf, скиллы, схемы или жизненный цикл самой фабрики. Ручная постановка использует действующий `source.type: ui` и ключ `UI-…`. Тип отражает результат задачи. Например, исправление ошибочного `task close` — `bugfix`, новая схема flow — `feature`, перенос обработчиков без смены контракта — `refactor`. Для исследования с итогом в виде рекомендации использовать `research/research-first`, для локальной правки текста — `docs/docs-only`. Выбор продолжения после исследования можно сохранить в той же задаче, если реализация входила в исходный scope. Расширение цели оформляется явным изменением scope или отдельной задачей. [Контракт задачи](<data/machinedocs-encyclopedia/Практики/Контракт задачи для агента.md>) · [Минимальный цикл](<data/machinedocs-encyclopedia/Практики/Код, контекст и минимальный harness.md>)

### 22.1 Как выбрать объём процесса

| Условия | Маршрут |
|---|---|
| Результат — ответ на вопрос, сравнение вариантов или решение о целесообразности | `research-first`. Итог — вывод, ссылки, ограничения и рекомендация. Реализация оформляется при появлении соответствующей задачи. |
| Правится описание, поведение и машинные контракты сохраняются | `docs-only`. Точечная правка и подходящие проверки ссылок, схем или индекса. |
| Поведение меняется, границы понятны и есть один проверяемый результат | `factory-change` по короткому пути. Снимок исходного поведения, короткий план, изменение, проверки, фиксация результата. |
| Неясен способ реализации, меняются схемы, flow, CLI-контракт или правила закрытия | `factory-change` с исследованием и review плана. Задача фиксирует затронутые потребители, совместимость старых записей и способ отката. |

Условия выбора выражаются фактами, которые агент или владелец передал явно. Отсутствие блокирующего факта ведёт к уточнению. Исследование в `data/` требуется, когда есть конкретный вопрос о выборе паттерна, формата или проверки. Для локального известного дефекта обычно достаточно контракта, кода и воспроизводящего теста.

### 22.2 Переходы и результаты

| Шаг | Что делаем | Результат и следующий шаг |
|---|---|---|
| **Intake** | Записать цель, текущее и ожидаемое поведение, границу изменений, критерии приёмки и полномочия. Привязать задачу к затронутому flow или CLI-команде. | Готовый `task.json`. Блокирующие вопросы переводят задачу в ожидание ответа. |
| **Baseline** | Найти действующий контракт, код и tests. Зафиксировать исходную ревизию и проверку, которая подтверждает текущее поведение. | Ссылки на исходные факты. При открытом вопросе о решении перейти в исследование. В остальных случаях перейти к плану. |
| **Research**, по условию | Задать вопрос, открыть корневой MOC и нужные разделы `data/`, сверить практику с текущим кодом и ограничениями. Для серьёзного выбора сопоставить варианты и зафиксировать причину решения. | Короткая запись «вопрос → evidence → варианты → решение». Недостаток сведений ведёт к уточнению либо к завершению исследования с обозначенным ограничением. |
| **Plan** | Выбрать минимальный сквозной срез, критерии, затронутые файлы, проверки и условия обновления документации. При изменении схемы или публичного поведения описать миграцию, совместимость и откат. | Краткий план в существующей стадии. Декомпозиция добавляется по §22.3. Согласование требуется по действующей политике задачи. |
| **Implement** | Подготовить проверку нового поведения перед правкой, где это практически возможно. Внести изменение и прогнать быстрые целевые проверки. Обновить затронутый контракт, CLI help, prompts или индекс. | Проверяемый diff и ссылки на результаты. При расширении scope вернуться к плану. |
| **Verify** | Запустить целевые проверки, затем проверки затронутых соседних контрактов. Для изменений самого flow проверить успешный путь, отказ с сохранением состояния и возобновление, где применимо. | `verification.json` с командами, ревизией, исходами и ссылками. Провал проверки возвращает в реализацию, неполное или устаревшее evidence оставляет шаг открытым. |
| **Review / close** | Сверить diff и результаты с критериями. Учесть обязательных детей, актуальность всех доказательств и требуемое подтверждение. | Закрытая задача со ссылками на решение, изменённый контракт и проверенный результат. Отдельное интеграционное или релизное действие выполняется по своей политике. |

Хранить артефакты в действующей структуре `doc/tasks/<key>/stageN/`. Для короткого пути baseline и план можно записать небольшими секциями в `plan.md`. Исследовательская записка, ADR и архитектурная дельта появляются при наличии собственного вопроса, существенного решения или изменения долговременного поведения соответственно. `data/` используется для чтения, ссылки и вывод остаются в задаче или принятом контракте. [Сквозной цикл разработки](<data/machinedocs-encyclopedia/Практики/Сквозной цикл разработки.md>) · [Формат flow](<data/machinedocs-encyclopedia/Документация/Флоу.md>)

### 22.3 Когда заводить дочерние задачи

Заводить ребёнка, если он даёт отдельно принимаемый результат, требует передачи другому исполнителю либо является явной зависимостью нескольких работ. Чтение конфигов, правку и запуск одного тестового набора обычно достаточно оставить шагами плана. Предлагаемая условная декомпозиция применяется после изменения действующей политики типа, которая сейчас требует детей для `feature`.

Пример для доработки переходов flow. Ребёнок `0001` фиксирует контракт переходов и контрольные fixtures. Ребёнок `0002` реализует диагностику по этому контракту, `0003` готовит миграцию одного flow. Оба зависят от `0001`. Если два ребёнка меняют общий файл, интеграцию выполнять последовательно либо назначить одного владельца. Родитель проверяет итоговый checkout и общий пользовательский сценарий. [Параллельная работа агентов](<data/machinedocs-encyclopedia/Практики/Параллельная работа агентов.md>)

### 22.4 Как запустить до появления нового CLI

Первую задачу поставить в саму фабрику через действующий `create-task` и тип по результату. Шаги §22.2 сохранить в её текущем плане. Для входной и структурной проверки применять действующие `task validate`, `task diagnose`, `scan --scope task-conf` и `index check`. Проверку приёмки выполнять существующим тестовым запуском и фиксировать в стадии. Решение о закрытии сверять с критериями и evidence вручную, пока `task close` проверяет только текущий ограниченный набор условий. Так первый прогон помогает внедрить новое поведение на реальной задаче без зависимости от ещё не выпущенной команды.

**Первый срез.** Поставить ручную задачу на согласование `task diagnose` и `task close` при отсутствующей обязательной подзадаче. Зафиксировать исходный результат. Добавить проверку, что обе команды называют один блокирующий ID, закрытие оставляет состояние прежним, а корректная совместимая задача проходит. Проверить CLI через обычную точку входа и сохранить результаты. Декомпозировать только при появлении отдельного результата, например миграции формата.

После этого добавить `factory-change` как общий шаблон для `bugfix`, `feature` и `refactor`. До поддержки общих шаблонов зарегистрировать его сначала в одном типе, затем распространить после проверки различий профилей. По мере реализации §21 CLI возьмёт вычисление readiness, проверку зависимостей, регистрацию событий и возврат компактного следующего шага. Приёмка flow включает короткий путь без детей, путь с исследованием и отдельным результатом, прерванный прогон и устаревшее доказательство. Сравнить число вызовов, объём прочитанного контекста и токены на задачу при равной полноте проверок.

## 23. Проектный YAML и размещение артефактов

**Проектный YAML — единый источник путей.** В текущей фабрике его роль выполняет `doc/config/paths.yaml`, а архитектура по умолчанию находится в `doc/architecture/`. Сейчас `ArchitectureStore` собирает часть путей напрямую. Задача внедрения — перевести CLI, индексатор, проверки, скрипты и агента на единый разрешённый набор путей. [Текущий YAML](doc/config/paths.yaml) · [Текущий store](doc/tools/arch/store.py#L57)

### 23.1 Контракт разрешения путей

- Загружать и валидировать один конфиг при входе в команду. Для перенесённого конфига предусмотреть явный `--config <path>`. Совместимый запуск находит текущий конфиг относительно выбранного корня проекта. Относительные пути разрешаются относительно этого корня, даже если сам YAML лежит в другом каталоге.
- Конфиг определяет корни архитектуры, задач, схем, task-conf, скиллов и справочного контекста, а также путь индекса и шаблоны артефактов. Старые значения `doc/architecture/`, `doc/tasks/` и остальные сохраняются как значения совместимого конфига. Для нестандартной раскладки используют декларации YAML. `allowed_paths` применяется к разрешённым корням. Шаблон пути задаётся один раз относительно своего корня.
- CLI передаёт разрешённые пути всем модулям. Скрипты и агент получают те же значения из машиночитаемого контекста команды. `diagnose` и `task context` выводят только применимые ссылки. Ошибки конфигурации называют ключ, выбранный корень и причину. При ошибке выбранного YAML команда сообщает о проблеме и сохраняет состояние.
- Всю документацию и папки задач можно хранить в Git проекта, в отдельном хранилище или локально, в том числе под `.gitignore`. Обход идёт по файловой системе в настроенных корнях. Git используется для сведений о коммите и diff там, где он доступен. Отдельный checkout архитектуры не является предварительным условием.
- У локального снимка документов без Git базовую версию дельты определяет типизированный идентификатор снимка с хешем содержимого. У версии из Git используют ссылку на коммит, если она соответствует проверенным файлам. При изменении файла проверка дельты сравнивает фактическую базу. Доказательство теста отдельно ссылается на снимок реализованного изменения.
- В ссылках и индексе сохранять ID и пути относительно соответствующих корней. Машинозависимые абсолютные пути нужны только для разрешения и диагностики. Политика разрешённых путей проверяет выход за назначенный корень, включая символические ссылки.

### 23.2 Папка задачи

| Артефакт | Путь относительно задачи | Что хранит |
|---|---|---|
| Вход задачи | `task.json` | Намерение, критерии приёмки и ссылки на относящиеся к задаче материалы. |
| Вложения | `attachments/<name>` | Входные скриншоты, примеры, документы и другие материалы. При импорте фиксировать происхождение, исходное имя и локальную ссылку. |
| Исследование | `research/<slug>.md` | Вопрос, источники, результаты и обоснование. Общие материалы остаются в справочном корне. |
| План | `stageN/plan.md` | Границы итерации, шаги и ссылки на контракты, вложения и исследование. |
| Diff изменения | `stageN/diff/<name>.patch` | Зафиксированный снимок правок стадии, когда нужна переносимая копия для передачи или проверки. Если достаточно неизменяемых ссылок на базу и результат, их указывать в записи проверки. Для локального прогона без коммита фиксировать проверенный снимок и его идентификатор. |
| Архитектурная дельта | `stageN/architecture-delta/<id>.md` | Предложение об изменении канонического документа с его ID, базой и ссылками на evidence. |
| Результат проверки | `stageN/verification.json` | Что запустили, на каком снимке, какие критерии покрыты, каков исход и где находятся подтверждающие артефакты. |
| Подзадача | `subtasks/<id>/` | Своя запись и необходимые артефакты самостоятельного результата. Общие вложения и исследования можно читать по ссылкам из родителя. |

Каталоги создаются по потребности. Входные материалы хранятся на уровне задачи, снимки изменения и доказательства относятся к стадии. Сохранение больших файлов и чувствительных материалов подчиняется политике проекта. Для операций с вложениями и diff нужна явная ссылка и компактные метаданные, чтобы `diagnose` мог указать материал без загрузки его содержимого.

### 23.3 Приёмка и порядок

В `v0.1` унифицировать разрешение путей и сохранить совместимость стандартной раскладки. Проверить `list/show`, проверку документации, сборку индекса, диагностику задачи и проверку путей на стандартном корне, перенесённом корне и локальной архитектуре под `.gitignore`. Добавить fixture с локальным хранилищем без собственного Git. Проверить выбор YAML из другой рабочей директории и диагностику неверного пути.

В `v0.2` включить в шаблоны пути для вложений, исследований, diff и архитектурных дельт. Проверить одну задачу со ссылками на все эти материалы. Отдельно прогнать проверку дельты на свежем и изменившемся локальном снимке, а также на Git-версии. Синхронизировать архитектурный контракт, схемы, правила путей и примеры в том же срезе.

## 24. Пакет постановки задач

Порядок реализации определяет таблица ниже. Пакеты P01–P15 зарегистрированы как UI-0011–UI-0025. Реальные зависимости хранятся в `task.json`. Для каждого пакета действует текущий тип и flow, а выполнение описано в `stage1/plan.md`. `stageN/` сохраняется как формат итераций.

| Пакет и выпуск | Тип / flow | Зависит от | Объём и проверяемая приёмка |
|---|---|---|---|
| **P01. Готовность закрытия**, v0.1 | `bugfix / standard-implementation` | — | Общая проверка для `diagnose` и `close`, стабильный JSON и предпросмотр. Один и тот же ID отсутствующего обязательного ребёнка в обоих ответах, отказ оставляет файлы неизменными, валидная совместимая задача закрывается. §15, §17, §21–22. |
| **P02. Проектный YAML и корни**, v0.1 | `feature / standard-implementation` | — | Дети: загрузчик и контракт конфигурации, перевод потребителей с интеграционными проверками. Стандартное, перенесённое и игнорируемое Git размещение проходит `list/show/index/validate/paths` и диагностику задач. Неверный конфиг даёт точную ошибку до записи. §23. |
| **P03. Устойчивые записи и модульность CLI**, v0.1 | `refactor / standard-implementation` | P01, P02 | Отделить сценарии lifecycle от CLI, проверить пакет декомпозиции целиком, обработать прерванную запись. Коллизии и некорректные связи не оставляют частично созданную задачу. Старые команды и выходные форматы сохраняют совместимость, согласованные изменения покрыты тестами. §15, §17, §21. |
| **P04. Установка и локальный gate**, v0.1 | `feature / standard-implementation` | P02 | Дети: упаковка и установка из артефакта, раздельные локальные проверки. Чистая установка запускает CLI, локальный gate выявляет устаревший индекс до сборки и проверяет воспроизводимость во временном дереве. CI/CD и Git-hosted workflow запрещены. Проверки запускаются через существующие интерфейсы. §7, §19. |
| **P05. Каталог навыков и базовый прогон**, v0.1 | `docs / docs-only` | P01 | Описать четыре текущих скилла, собрать учебный пример и критерии сравнения. Из чистой сессии можно найти нужную команду, пройти учебную задачу и воспроизвести baseline. §8, §18, §20. |
| **P06. Версионированный task record**, v0.2 | `feature / standard-implementation` | P03 | Дети: схемы и совместимое чтение, запись переходов и восстановление. Задача хранит версию flow, изменяемое состояние и ссылку на intent. Старые fixtures читаются, миграция повторяема, конфликт ревизии и повтор события не портят данные. §6–7, §21. |
| **P07. Два flow и зависимости**, v0.2 | `feature / standard-implementation` | P06 | Дети: формат и статические проверки, переходы и готовность детей. Прогнать `bugfix` с возвратом после проверки и короткий `docs-only`. Неизвестный вход, пересекающиеся правила, недействительные ссылки и циклы дают объяснимую диагностику. §21. |
| **P08. Живые спеки и артефакты задачи**, v0.2 | `feature / standard-implementation` | P02, P06 | Дети: схема и проверка дельты, пути и ссылки артефактов. Сценарий связывает требование, дельту, diff, вложение, исследование и проверку. Устаревшая база обнаруживается для Git и локального снимка. §16, §20, §23. |
| **P09. Контекст и ревью изменений**, v0.2 | `feature / standard-implementation` | P07, P08 | Дети: JSON-контекст шага, скилл `review-change` и примеры. Новый сеанс находит контракты и evidence точечно, неполные и устаревшие проверки видны отдельно. Замерить вызовы, объём контекста и токены. §17–21. |
| **P10. Factory-change**, v0.2 | `feature / standard-implementation` | P07, P09 | Дети: профиль и шаблон самодоработки, два контрольных прогона. Проверить короткую правку и путь с исследованием и дочерним результатом. Перенос остальных flow начинается после успешных контрольных сценариев. §22. |
| **P11. Исполнение и независимая проверка**, v0.3 | `feature / standard-implementation` | P04, P06, P09 | Дети: изоляция и управляемый жизненный цикл запуска, проверка и evidence. Один локальный прогон с установленными лимитами восстанавливается после прерывания. Результат связан с проверенной ревизией, ограничения доступа и защищённые проверки подтверждены тестами. §7, §9, §20. |
| **P12. Пилот и сравнение**, v0.3 | `audit / research-first` | P10, P11 | Определить критерий приёмки, бюджет, условия остановки и сценарий восстановления. Пройти ручной пилот и сравнить закреплённые версии нашей системы, OpenSpec, Spec Kit и их совместного сценария. Записать покрытие, разброс и ограничения вывода. §8, §18–19. |
| **P13. Адаптеры источников**, после пилота | `feature / standard-implementation` | P12 | Дети: контракт read-only снимков и обработка повторного входа, проектирование подтверждаемой записи при наличии потребителя. Пилот без write-back остаётся рабочим. Устаревшие снимки и дубликаты диагностируются. §7, §19. |
| **P14. Решение о расширениях**, после пилота | `planning / research-first` | P12 | Сопоставить измеренную пользу аллокатора, внешнего движка, интеграций, каталогов, model routing и расширения автономности. Для каждого зафиксировать предпосылку, метрику и решение об откладывании или отдельной постановке. §7–10, §20. |
| **P15. Приёмка поддерживаемого выпуска**, v1.0 | `audit / research-first` | P12, P14 | Пройти чистую установку, обновление старой задачи, откат, восстановление и проверки совместимости CLI и схем. Подготовить релизный пакет, changelog, инструкцию и результаты сравнительных прогонов. Публикация зависит от решения владельца. §7–8, §19. |

Для каждой задачи при регистрации подготовить `task.json`, краткий `stage1/plan.md` и `stage1/verification.json` со статусом `not_run`. Приёмка каждой задачи привязывается к своим AC-ID, командам или наблюдаемым результатам. Изменения следующего пакета стартуют после подтверждения соответствующей зависимости. Возможности из P13 и P14 включаются в релиз по результатам пилота.

- P01 — [UI-0011: Готовность закрытия](doc/tasks/UI-0011/task.json)
- P02 — [UI-0012: Проектный YAML и рабочие корни](doc/tasks/UI-0012/task.json)
- P03 — [UI-0013: Устойчивые записи и модульность CLI](doc/tasks/UI-0013/task.json)
- P04 — [UI-0014: Воспроизводимая установка и CI](doc/tasks/UI-0014/task.json)
- P05 — [UI-0015: Каталог скиллов и исходный прогон](doc/tasks/UI-0015/task.json)
- P06 — [UI-0016: Версионированная запись задачи](doc/tasks/UI-0016/task.json)
- P07 — [UI-0017: Два контрольных flow и зависимости детей](doc/tasks/UI-0017/task.json)
- P08 — [UI-0018: Живые спецификации и артефакты](doc/tasks/UI-0018/task.json)
- P09 — [UI-0019: Контекст стадии и review-change](doc/tasks/UI-0019/task.json)
- P10 — [UI-0020: Factory-change для доработки фабрики](doc/tasks/UI-0020/task.json)
- P11 — [UI-0021: Ограниченный локальный прогон и независимая приёмка](doc/tasks/UI-0021/task.json)
- P12 — [UI-0022: Ручной пилот и сравнительные прогоны](doc/tasks/UI-0022/task.json)
- P13 — [UI-0023: Адаптеры источников после пилота](doc/tasks/UI-0023/task.json)
- P14 — [UI-0024: Решение о расширениях после пилота](doc/tasks/UI-0024/task.json)
- P15 — [UI-0025: Приёмка поддерживаемого выпуска](doc/tasks/UI-0025/task.json)
