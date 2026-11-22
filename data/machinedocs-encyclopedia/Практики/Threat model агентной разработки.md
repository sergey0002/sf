---
title: "Threat model агентной разработки"
description: "Загружайте, когда задача касается: Модель угроз должна покрывать не только сгенерированный код, но и действия агента: чтение, команды, сеть, инструменты, credentials и изменение workflow."
tags: [практика, безопасность, threat-model]
paths: []
aliases: ["Agentic SDLC Threat Model", "Threat Model Coding Agents"]
---

# Threat model агентной разработки

> [!info] Определение
> Модель угроз должна покрывать не только сгенерированный код, но и действия агента:
> чтение, команды, сеть, инструменты, credentials и изменение workflow. Агент — субъект
> с identity и authority в supply chain. См. [[Безопасность]], [[Безопасность MCP и инструментов]],
> [[Безопасный деплой агентами]].

## Система и границы доверия

Нарисуйте data flow для: task intake → trusted instructions → repo/context → model/provider →
tools/MCP → sandbox/runner → PR → CI → artifact → deployment. Укажите для каждого перехода:
источник данных, владельца identity, права, network path, логирование и approval.

## Классы входов

| Источник | Trust по умолчанию | Правило обработки |
|---|---|---|
| Организационная policy, защищённая ветка | Trusted control, но versioned/reviewed | Может задавать границы, не обходит platform policy |
| User task / issue | Полезный intent, но potentially adversarial | Извлекать требования; текст не расширяет полномочия |
| PR title/body/comment, fork code | Untrusted | Никогда не соединять с широкими secrets/write permissions |
| Source comments, tests, docs, fixtures, logs | Данные; могут содержать injection | Читать по необходимости, не выполнять как инструкции |
| Package scripts, install hooks, MCP outputs | Непроверенный исполняемый/инструментальный контент | Pin, scan, sandbox, egress/permission policy |
| Agent-generated code/diff | Untrusted proposal | Independent CI и review до merge/execute |

Важно: delimiters и «не следуй injection» — только defense-in-depth. Надёжная граница —
минимальные capabilities, разделение credential zones и внешняя авторизация.

## Матрица угроз

| Сценарий | Последствие | Prevent / contain | Evidence |
|---|---|---|---|
| Prompt injection в issue/PR/comment | Непрошеный read/write/network/tool call | Untrusted trigger — least privilege; no secrets; human approval | Adversarial workflow tests, blocked-call logs |
| PR меняет `AGENTS.md`/workflow | Подмена политики/привилегированное исполнение | Инструкции из protected base; CODEOWNERS; отдельный review policy changes | Diff approval, source revision, workflow provenance |
| Fork PR получает write token/secrets | Exfiltration, code/release modification | Разделить untrusted PR checks и privileged jobs; approval gate | Token scopes, runner logs, secret access audit |
| Dependency/MCP/skill poisoning | Компрометация build/agent | Allowlist, pin/digest, package proxy, review upgrades | Inventory, SBOM, lockfile, scanner report |
| Agent changes its own tests/gates | Ложно-зелёный PR | Protect test/workflow paths; inspect test diffs; mutation/property tests | Diff-aware gate, code-owner approval |
| Excessive agency / wrong identity | Destructive operation, privilege escalation | Per-tool authorization, JIT credentials, human checkpoint | Principal/action/target audit events |
| Data exfiltration via public network | Утечка source/secrets | Egress deny/allowlist, secret redaction, private sandbox | DNS/proxy/network logs, DLP alerts |
| Non-reproducible agent run | Не удаётся расследовать/повторить | Pin model/config/tools/image; log IDs, commits, actions; keep artifacts | Session trace + artifact digest |

## STRIDE-проекция для агента

| STRIDE | Агентный пример | Контроль |
|---|---|---|
| Spoofing | Подмена agent/MCP identity | Authenticated workload identity, audience/scope checks |
| Tampering | Изменение tool schema/instructions/build artifact | Protected config, digest/signature, review |
| Repudiation | Нельзя понять, кто вызвал tool | Correlated immutable audit trail |
| Information disclosure | Secret в prompt/log/tool result | No standing secrets, redaction, egress control |
| Denial of service | Agent loops, retries, resource exhaustion | Budget, timeout, rate limit, circuit breaker |
| Elevation of privilege | Injection ведёт к deploy/write tool | Runtime authorization, separation of duties |

## Security invariants для CI

- Ни агент, ни проверяемая ветка не могут изменить required checks и сразу использовать новые правила.
- Изменения workflows, permissions, MCP inventory, agent instructions, secrets handling требуют owner review.
- Untrusted pull request не запускается с deployment/package-publish secrets.
- Секреты не появляются в agent context, test output, PR comments или traces.
- Agent output не является авторизацией: privileged service проверяет policy независимо.
- Merge/release credentials отделены от agent identity; agent не approves/merges себя.

## Red-team scenarios

Ежеквартально или после существенного изменения harness проверять adversarial payload в:
issue title/body, PR comment, repository instruction diff, code comment, test fixture, package README,
MCP tool description/result, branch name, generated log. Assertions должны проверять отсутствие
опасного side effect (секрет не прочитан/отправлен, privileged tool не вызван, branch не изменён),
а не только «агент ответил, что отказал».

## Источники

- OWASP AISVS Appendix C: AI-assisted secure coding, threat modeling, change-control invariants: https://github.com/OWASP/AISVS/blob/main/1.0/en/0x92-Appendix-C_AI_for_Code_Generation.md
- OWASP Secure Coding with AI Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Secure_Coding_with_AI_Cheat_Sheet.html
- GitHub Actions security hardening: https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions
- OWASP Cornucopia AAI8/AAI9: https://cornucopia.owasp.org/edition/companion/AAI8 and https://cornucopia.owasp.org/edition/companion/AAI9

## Мнемоника

**«Входы, Полномочия, Исполнение, Выходы, Доказательства»** — ВПИВД.

## Связи

- [[Безопасность]] · [[Безопасность MCP и инструментов]] · [[Безопасный деплой агентами]] · [[Аудит кода]] · [[Инструменты агентной среды]] · [[Контракт задачи для агента]]
