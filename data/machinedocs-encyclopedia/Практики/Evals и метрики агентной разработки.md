---
title: "Evals и метрики агентной разработки"
description: "Загружайте, когда задача касается: Измерение качества не только финального текста, но и выполнения задачи агентом: правильный результат, безопасная траектория, проверяемые побочные действия, затраты и влияние на delivery system."
tags: [практика, evals, метрики]
paths: []
aliases: []
---

# Evals и метрики агентной разработки

> [!info] Определение
> Измерение качества не только финального текста, но и выполнения задачи агентом:
> правильный результат, безопасная траектория, проверяемые побочные действия,
> затраты и влияние на delivery system. См. [[Harness-инжиниринг]], [[Тесты]], [[Агентский CI-CD]].

## Три контура evals

| Контур | Когда | Что проверять |
|---|---|---|
| Task benchmark | При выборе модели/harness/prompt | Решает ли репрезентативные задачи в sandbox с hidden oracle? |
| Regression eval | До merge prompt/tool/model/config changes | Не деградировали ли прежние случаи и безопасность? |
| Production monitoring | После rollout | Реальные failures, policy denials, cost, quality, escalations |

Для каждого benchmark: фиксированный task set, репозиторий/commit, sandbox image, timeout,
разрешённые tools/network, model/prompt version, число повторов и scorer. Публиковать pass rate
с размером выборки и confidence interval; nondeterministic agents требуют repeated runs.

## Task eval schema

```json
{
  "case_id": "bugfix-authz-014",
  "repo": "org/service",
  "base_commit": "<sha>",
  "task": "...",
  "acceptance": ["hidden_test:authz-denied", "existing_tests:pass"],
  "constraints": ["no_schema_change", "no_network_except_registry"],
  "timeout_seconds": 1800,
  "max_tool_calls": 80,
  "grader": {"type": "test_and_policy", "version": "3"}
}
```

Идентификаторы должны быть реальными commit SHA; пример выше — форма схемы, не конкретный репозиторий.

## Layered scoring

| Слой | Пример измерения | Не путать с |
|---|---|---|
| Outcome correctness | Hidden tests, contract tests, exact state diff | Красивым объяснением агента |
| Regression | Существующие tests + mutation/property tests | Лишь line coverage |
| Security/policy | Запрещённые действия = 0; authorization tests | Агентским self-report |
| Trajectory | Лишние/опасные tool calls, scope violations, retries | Любым конкретным reasoning trace как «истиной» |
| Evidence | Команды/артефакты/exit codes подтверждены | Утверждением «всё прошло» |
| Efficiency | Cost/time per accepted change; human review time | Tokens или PR count сами по себе |
| Reliability | Repeated-run pass rate, flaky variance, rollback/error rate | Одна удачная демо-сессия |

Использовать deterministic graders там, где возможно; LLM-as-judge — как дополнительный сигнал,
с калибровкой на человеческой разметке и проверкой межсудейского согласия.

## Измерять эффект на системе, не объём генерации

Базовый набор — DORA delivery outcomes (deployment frequency, lead time, change failure rate,
failed deployment recovery time; учитывать актуальные определения DORA). Дополнить:

- review latency и время человека на исправление/проверку;
- PR batch size (files/lines) и доля PR, разбитых/переделанных;
- first-pass acceptance и rework/churn через 7/30 дней;
- escaped defects/incidents и их связь с конкретным commit/artifact;
- стоимость на **принятое и выпущенное** изменение, не на токен/сгенерированную строку;
- adoption/provenance cohorts: human-authored, AI-assisted, agent-authored — аккуратно и с едиными правилами атрибуции;
- developer experience, interruption load, review burden — опросом, не только логами.

Не использовать индивидуальные activity counts как KPI и не заключать причинность из простой корреляции.
Сравнивать baseline и период внедрения, учитывать изменение сложности задач, состава команды,
качества CI и при возможности делать контролируемый rollout.

## Guard against metric gaming

| Vanity target | Как ломают | Лучше измерять |
|---|---|---|
| PR count | Много мелких/тривиальных PR | Accepted outcomes + review/merge/rework |
| Green CI | Удалить/skips тесты, ослабить assertions | Test diff review, mutation/property checks, hidden tests |
| Coverage % | Покрыть строки без assert смысла | Mutation score, behavior assertions, risk-weighted cases |
| Auto-fix rate | Лечить symptom/скрывать gate | Confirmed fix rate + recurrence + escaped failure |
| Tokens per task | Урезать важные проверки | Cost per accepted change + defect/rework |
| LLM review findings | Много ложных комментариев | Precision on adjudicated findings, confirmed severity |

## Production telemetry

Связать `task_id → agent/session → model/prompt/tool versions → PR/commit → CI run → artifact digest → deployment → incident`.
Стандартизовать GenAI spans/events через OpenTelemetry, но контролировать data capture: redaction,
PII/secrets policy, retention и доступ. GenAI conventions в источнике имеют статус Development;
фиксировать версию schema, не объявлять её стабильной без проверки.

## Rollout eval gate

1. Заморозить baseline task set и критичные policy tests.
2. Изменять один фактор за раз (model, prompt, tool permissions, sandbox image).
3. Повторять nondeterministic tasks; сохранять traces и точные среды.
4. Блокировать rollout при критичном policy violation, ухудшении task success или росте cost выше лимита.
5. Canary на низкорисковых задачах; ручной sampling результатов и adverse cases.
6. Rollback к предыдущей версионированной конфигурации.

## Связи

- [[Harness-инжиниринг]] · [[Тесты]] · [[Агентский CI-CD]] · [[Аудит кода]] · [[Инструменты агентной среды]] · [[Безопасность MCP и инструментов]]

## Источники

- OpenAI Evals: https://platform.openai.com/docs/guides/evals
- OpenHands paper (benchmark integration and sandbox evaluation): https://arxiv.org/html/2407.16741v3
- OpenTelemetry GenAI conventions: https://github.com/open-telemetry/semantic-conventions-genai
- DORA State of AI-assisted Software Development: https://dora.dev/research/2025/dora-report/
