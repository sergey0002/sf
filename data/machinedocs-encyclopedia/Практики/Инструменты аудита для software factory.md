---
title: "Инструменты аудита для software factory"
description: "Загружайте, когда задача касается: Инструмент должен закрывать конкретный вопрос о репозитории и давать машинно-читаемое evidence: SARIF, junit, trace, benchmark data, graph, report."
tags: [практика, инструменты, аудит, тестирование]
paths: []
aliases: []
---

# Инструменты аудита для software factory

> [!info] Принцип выбора
> Инструмент должен закрывать конкретный вопрос о репозитории и давать машинно-читаемое
> evidence: SARIF, junit, trace, benchmark data, graph, report. Не строить дорогой all-in-one
> stack до инвентаризации текущих CI/IDE/code search. См. [[Архитектура агентной software factory]].

## 1. Repo intelligence / architecture map

| Что нужно | Примеры | Выход |
|---|---|---|
| Symbols, definitions, references | LSP servers per language | Definition/reference/call hierarchy |
| Exact/semantic cross-repo search | ripgrep + Sourcegraph / GitHub code search | Search hits with paths/commits |
| Import/dependency graph | Nx graph, dependency-cruiser (JS/TS), Madge, deptry (Python), `go list`, cargo metadata | Edges, cycles, affected modules |
| Architecture rules | ArchUnit (JVM), NetArchTest (C#), dependency-cruiser/import-linter/deptry | CI assertions with violated edge list |
| API/schema diff | OpenAPI diff tools, Buf breaking checks (Protobuf), GraphQL schema checks | Compatibility and breaking changes |
| Ownership | CODEOWNERS + service catalog/catalog metadata | Responsible reviewer, service context |

**Rule:** use generated graph for what it can prove (nodes/edges); use concise owner-validated module
notes for why, risk, domain terminology. Update/invalidate indexes on the exact commit being audited.

## 2. Correctness, testing, and regression detection

| Layer | Tool families | Factory use |
|---|---|---|
| Build/type/lint | Compiler, TypeScript, mypy/pyright, clippy, golangci-lint, ESLint | Fast feedback after each patch |
| Unit/integration/e2e | Existing repo test framework; Playwright/Cypress for UI/API journeys | Exact reproduction and regression oracle |
| Property/fuzz | Hypothesis, jqwik, QuickCheck, libFuzzer, AFL++ | Inputs and invariants beyond hand-written examples |
| Mutation testing | Stryker, PIT, mutmut | Test sensitivity: can tests detect representative behavior changes? |
| Coverage | Native coverage/JaCoCo/coverage.py/nyc | Identify unexecuted paths, not proof of test quality |
| Differential testing | Compare old/new output on fixed corpus or shadow traffic | Safe refactors, parsers, compilers, query plans |
| Test impact selection | Bazel/Nx/Gradle affected targets, dependency graph | Fast changed-area checks; full required CI remains final authority |

**Caution:** mutation score, coverage and pass rate are diagnostic signals, not correctness guarantees.
Protect test/gate files from the patch under evaluation; verify assertions, not just test counts.

## 3. Security and supply-chain audit

| Risk | Tool options | Caveat / gate design |
|---|---|---|
| SAST / dataflow | CodeQL, Semgrep, language-native analyzers | Tune rules; triage reachability and source→sink evidence |
| Secrets | Gitleaks, detect-secrets, platform push protection | Scan working tree and history where appropriate; rotate exposed secrets |
| Dependency vulnerabilities | OSV-Scanner, Dependabot, Renovate + OSV/SCA platform | Lockfiles, reachability, exploitability, license/policy |
| Container/IaC | Trivy, Checkov, tfsec, kube-linter | Scan image/config manifests; don't execute untrusted plans with privileged tokens |
| DAST/API | OWASP ZAP, Schemathesis / RESTler (API fuzzing) | Passive scan on PR; active testing only in authorized test env |
| Provenance | SLSA/in-toto attestations, SBOM (CycloneDX/SPDX), cosign | Verify artifact/commit/builder identity; generate evidence in trusted CI |
| Threat modeling | OWASP Threat Dragon, IriusRisk or lightweight STRIDE data-flow template | Tools assist enumeration; security owner validates trust boundaries |

For alert triage, store `tool + version + rule_id + severity + location + fingerprint + baseline commit`.
Do not treat incomplete scanner run as clean; capture scanner diagnostics/coverage status.

## 4. Architecture and code-quality audit

- **Architecture tests:** ArchUnit can check package/class dependencies, layers, slices and cycles in JVM bytecode.
  Equivalent rule tools differ by language; select one supported in repo CI.
- **Static import rules:** dependency-cruiser (JS/TS), import-linter/deptry (Python), custom Roslyn analyzers/.NET tests, Go package policies.
- **Structural query:** tree-sitter/AST or CodeQL for usage patterns and source→sink/call graph.
- **Design contract:** module graph + interface/schema compatibility + CODEOWNERS.
- **Maintainability signals:** complexity/duplication/dead-code tools (SonarQube, Semgrep custom rules, language linters).
  Gate trends on changed code; avoid noisy global thresholds on legacy repos.

Start with a few high-value, objective rules, test them on known-good and intentionally-bad changes,
then gate. Warnings from architecture agents are not enforcement until backed by validated executable rules.

## 5. Performance audit and benchmarking

| Level | Tool examples | Appropriate question |
|---|---|---|
| Microbenchmark | Google Benchmark (C++), JMH (JVM), Criterion (Rust), pytest-benchmark/pyperf (Python) | Did this algorithm/function regress? |
| Service load | k6, Gatling, Locust, wrk | Latency/throughput/errors under representative traffic |
| Profiling | pprof, async-profiler, perf, py-spy, flamegraphs | Where is CPU/alloc/I/O time actually spent? |
| Production behavior | OpenTelemetry + existing APM (Prometheus/Grafana/Datadog/etc.) | Is the critical user journey / SLO affected? |

Reliable perf check:

1. Define workload/data size, warmup, environment, p50/p95/p99, throughput, errors, CPU/memory.
2. Run base and candidate under same controlled hardware and settings; store commit + raw data.
3. Repeat enough to estimate noise; use distributions/CI or a team-defined noise floor, not one run.
4. Keep absolute SLO and relative-to-baseline checks separate.
5. Rerun suspicious regressions; don't let an agent alter thresholds/baseline to make a patch green.
6. Use load generators only against authorized isolated staging/test services.

## 6. Result format for agent consumption

Normalize different analyzers into a finding record before orchestrating repair:

```json
{
  "tool": "codeql",
  "tool_version": "pinned-version",
  "rule_id": "js/sql-injection",
  "fingerprint": "stable-finding-fingerprint",
  "severity": "high",
  "confidence": "medium",
  "commit": "full-commit-sha",
  "locations": [{"path": "src/db/query.ts", "line": 31}],
  "evidence_kind": "taint-trace",
  "baseline_status": "new",
  "repro_or_trace": "artifact URI or test id",
  "proposed_action": "review | bounded-fix | suppress-with-owner"
}
```

Keep scanner-native results (e.g. SARIF/JUnit/raw benchmark output) as authoritative artifacts;
LLM summary is a derived view, not a replacement for raw evidence.

## 7. Minimal stack by maturity

| Maturity | Suggested bundle |
|---|---|
| First pilot | Repo-native tests + type/lint + one SAST/secrets tool + ephemeral environment + PR review |
| Architecture-aware | Add dependency graph + executable layer/cycle rules + test ownership/impact map |
| Security-ready | Add SCA/IaC/container scans + DAST in test env + SBOM/provenance + threat model review |
| Performance-aware | Add reproducible critical-path benchmarks + APM traces + canary thresholds |
| Factory scale | Normalized findings, dedupe, workflow orchestrator, reviewer queues, eval suite, model/tool version pinning |

Use existing toolchain first. More tools are not necessarily more coverage: deduplicate overlap, assign owners,
measure actionable precision and ensure each blocking signal has remediation guidance.

## Sources

- GitHub CodeQL CLI: https://docs.github.com/en/code-security/concepts/code-scanning/codeql/codeql-cli
- CodeQL custom queries: https://docs.github.com/en/code-security/concepts/code-scanning/codeql/custom-queries
- Semgrep CLI: https://semgrep.dev/docs/cli-reference/
- Semgrep Supply Chain: https://docs.semgrep.dev/semgrep-supply-chain/overview
- ArchUnit user guide: https://www.archunit.org/userguide/html/000_Index.html
- k6 thresholds: https://grafana.com/docs/k6/latest/using-k6/thresholds/
- Google Benchmark user guide: https://github.com/google/benchmark/blob/main/docs/user_guide.md
- Stryker mutation metrics: https://stryker-mutator.io/docs/mutation-testing-elements/mutant-states-and-metrics/
- OWASP ZAP Automation Framework (supports defined environments, passive/active scan jobs, and result-based exit status; only target explicitly authorized test systems): https://www.zaproxy.org/docs/automate/automation-framework/

## Связи

- [[Архитектура агентной software factory]] · [[Аудит кода]] · [[Аудит архитектуры]] · [[Безопасность]] · [[Тесты]] · [[Evals и метрики агентной разработки]] · [[Безопасный деплой агентами]]
