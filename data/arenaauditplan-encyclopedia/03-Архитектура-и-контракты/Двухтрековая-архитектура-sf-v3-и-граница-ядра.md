---
id: "AAP-ARCH-V3"
title: "Двухтрековая целевая архитектура sf v3.0, SQLite-кэш связок, капсула <3.2k и разрешение противоречий"
description: "Загружайте при проектировании sf v3.0: разделение Среда vs Ядро, DDL .sf/intent.sqlite, анатомия капсулы <3200 токенов, 10 слоёв контекста, ТРИЗ-разделение противоречий, workpack.json и .sf/providers.yaml."
status: "canonical"
track: "both"
stage: "all"
paths: ["doc/tools/arch/", "doc/config/", "taskcontrol.md"]
tags: [архитектура, sf-v3, двухтрековая-модель, providers-yaml, workpack, sqlite-cache, triz, handoff]
aliases: ["Двухтрековая архитектура sf v3 и граница ядра", "Двухтрековая архитектура sf v3.0"]
---

# Двухтрековая целевая архитектура `sf v3.0`, SQLite-кэш связок, капсула `<3.2k` и разрешение противоречий

> [!abstract] Кратко
> Целевая архитектура `sf v3.0` снимает противоречия между скоростью, ценой, масштабом кодовой базы и строгостью приёмки ([[06-Консилиум-и-конфликты/Реестр-конфликтов-и-решений|CONF-02]]) за счёт ортогонального разделения труда между **Треком А (Слой агентной среды — `0` кода в `arch` CLI)** и **Треком Б (Тонкое ядро контрактов `arch` — `0` самописных MCP и `0` серверных СУБД)**.

## 1. Разрешение 6 физических противоречий агентной фабрики (по методологии ТРИЗ / SEI из `data/`)

Опираясь на [ТРИЗ и аналоги: карта методов для агентной разработки.md](<../../machinedocs-encyclopedia/Практики/ТРИЗ и аналоги_ карта методов для агентной разработки.md>), ключевые конфликты `sf` разрешаются физическим разделением в пространстве, во времени, по условию риска и по системному уровню:

| Физическое противоречие | Принцип разделения | Исполняемый механизм в `sf v3.0` |
|---|---|---|
| Контекст должен быть **широким** (ничего не упустить в `450K LOC`) и **узким** (точность малых LLM и цена) | По актору и фазе | `locator` видит граф кода и строит `envelope ≤2k`; `implementer` получает только капсулу `<3.2k` без MCP-схем |
| Агент должен **автономно менять файлы**, но **не мочь ослабить тесты/политики** | По пространству ФС | RW в `allowed_edit_spans` `worktree`, физический `RO Trust Zone` на `tests/**`, `*.flow.json` и конфиги гейтов |
| Глубокие контракты нужны на сложных фичах, но убивают скорость мелкого багфикса | По условию риска (`risk × complexity`) | Детерминированный `Ceremony Scaling`: профиль `quick` (`task.json ≤1 КБ`, `≤6` шагов) vs `standard` vs `full` |
| Состояние задачи должно быть **общим** для координации волн, но **изолированным** от гонок | Целое / части | Иммутабельный `task.json` (`intent_digest`) + предсобранный `graph.db.zst` в корне; приватные `worktree` и порты у воркеров |
| Модель предлагает решение, но границе доверия нельзя верить на слово | По системному уровню | Паттерн `Agent Proposes → Deterministic Gate & Verifier Validate → Human Owner Approves` |
| Полная архитектура нужна при смене правил, но вредна при постоянной загрузке | По времени (On-Demand) | `Index-First` + двухкольцевой радар `context pack` (кодеру грузятся только `implemented: true`) |

---

## 2. Федеративная склейка `Intent Canon (JSON в Git) ⋈ External Code Graph` (DDL `.sf/intent.sqlite`)

В согласии с [taskcontrol.md](<../../../taskcontrol.md>) §10.1 каноном истины всегда остаются плоские файлы в Git (`task.json`, `state.json`, `events.jsonl`, `*.flow.json`, `verification.json`). Однофайловый gitignored-кэш `.sf/intent.sqlite` (`WAL + FTS5`) пересобирается из них за миллисекунды и хранит только нормативные узлы `To-Be` и якорные связки с символами внешнего графа кода `As-Is`:

```sql
CREATE TABLE intent_nodes (
  id TEXT PRIMARY KEY,               -- 'FLOW-refund#insufficient-balance', 'ENT-order', 'TERM-hold', 'TASK:UI-0029'
  kind TEXT NOT NULL,                -- 'flow' | 'branch' | 'entity' | 'capability' | 'adr' | 'term' | 'task'
  domain TEXT NOT NULL,
  spec_sha256 TEXT NOT NULL,
  contract_json TEXT NOT NULL        -- условия DMN, инварианты атомарности и идемпотентности
);

CREATE TABLE symbol_bindings (
  intent_id TEXT NOT NULL REFERENCES intent_nodes(id),
  symbol_uri TEXT NOT NULL,          -- квалифицированный символ/роут в CBM / CodeGraph ('app/Services/Vat.php::calc')
  role TEXT NOT NULL,                -- 'entrypoint' | 'handler' | 'validator' | 'test_oracle'
  confidence TEXT NOT NULL,          -- 'spec_declared' | 'hybrid_lsp_exact' | 'ast_inferred'
  last_verified_commit TEXT,
  PRIMARY KEY (intent_id, symbol_uri, role)
);

CREATE TABLE task_leases (
  task_key TEXT NOT NULL,
  target_uri TEXT NOT NULL,          -- intent_id или symbol_uri из графа кода
  lease_mode TEXT NOT NULL,          -- 'read_input' | 'write_exclusive'
  base_sha256 TEXT NOT NULL,
  PRIMARY KEY (task_key, target_uri)
);
```

---

## 3. Когнитивная эргономика под слабые модели: капсула `<3 200` ток. и типизированный `Handoff`

По модели 10 слоёв памяти из [Управление контекстом многоагентных систем.md](<../../machinedocs-encyclopedia/Практики/Управление контекстом многоагентных систем.md>) субагенты никогда не пересылают друг другу сырой `chain-of-thought` или простыни логов:
1. **Фиксированная 4-слотовая капсула `implementer` (`<3 200` входных токенов, `0` схем графовых MCP):**
   - Слот 1 (`~350` ток.): контракт ровно 1 целевой ветки `*.flow.json` + инвариант `unchanged_behavior`;
   - Слот 2 (`~300–900` ток.): гибридный срез — сигнатуры `1-hop` соседей из графа + точный диапазон строк тела целевой функции;
   - Слот 3 (`~250` ток.): типы данных и ограничения `allowed_edit_spans` / `RO Trust Zone`;
   - Слот 4 (`~250–400` ток.): сжатый через `RTK / Headroom` вывод падающего `Red`-теста или выжившего мутанта.
2. **Краткий межагентный `handoff`-контракт (`locator → orchestrator → implementer`):**
   ```yaml
   run_id: UI-0041-stage1
   commit: f8cb406
   objective: Исправить округление НДС для дробного количества в PDF без изменения целых количеств
   allowed_edit_spans: ["app/Services/VatCalculator.php#L42-L78"]
   protected_ro_paths: ["tests/**", "doc/architecture/**"]
   known_facts:
     - claim: PDF-экспорт вызывает VatCalculator::calculateLine
       source: app/Services/PdfInvoiceExporter.php#L114@f8cb406
   verify: ["vendor/bin/pest --filter VatPdfTest"]
   stop_if: ["public signature must change", "same test error 2x"]
   ```
3. **Машинный `stageN/workpack.json` и 4 конвейера вместо 13 типов `task-conf`:**
   - Конвейеры: `observe` (`0` записи в код), `specify` (`*.flow.json / ADR / ENT`), `change` (`feature / bugfix / refactor / migration` с флагом `contract_delta: required | forbidden | optional`), `release` (интеграция волны).
   - Формат правок: точечные блоки `SEARCH/REPLACE` для логики + `ast-grep` для массовых структурных переименований.

---

## 4. Декларативный манифест внешних инструментов `.sf/providers.yaml`

```yaml
code_intelligence:
  weak_model_navigator: { driver: colbymchenry-codegraph, binary: codegraph }
  deep_polyglot_graph:  { driver: codebase-memory-mcp, binary: codebase-memory-mcp, shared_artifact: .codebase-memory/graph.db.zst }
  docs_and_canon_graph: { driver: graphify, package: graphifyy, artifact: graphify-out/graph.json }
  semantic_lsp_refactor: { driver: serena, optional: true }
  validated_batch_audit: { driver: greenolive-codeprizm, mode: periodic-report-import }

execution_hygiene:
  local_gate: "python -m arch gate"
  sandbox_5_boundaries: { driver: container-or-bwrap, egress_policy: allowlist-only }
  output_compressors: [rtk, headroom] # pip install "headroom-ai[all]" (CacheAligner + reversible CCR)
  structural_codemod: ast-grep

verification_gates:
  pre_write_security: [gitleaks, semgrep]
  diff_mutation:
    php: "vendor/bin/infection --git-diff-lines --git-diff-base=main --min-msi=80 --min-covered-msi=90 --threads=4"
    python: "mutmut run --paths-to-mutate {changed_files}"
    typescript: "npx stryker run --incremental --mutate {changed_line_spans}"
    csharp: "dotnet stryker --since:{base_sha}"
    rust: "cargo mutants --no-times --in-diff {diff_file}"
    jvm: "mvn test-compile org.pitest:pitest-maven:mutationCoverage -DwithHistory"
```

## Связи

- [[Главная]] · [[Справочник артефактов, команд и схем]] · [[02-Исследования-и-инструменты/Подключаемые-графы-кода-аудит-и-компрессоры]] · [[02-Исследования-и-инструменты/Субагенты-и-оркестрация-в-средах-OpenCode-Kilo-Claude]] · [[03-Архитектура-и-контракты/Спецификация-архитектурных-флоу-flow-json]] · [[03-Архитектура-и-контракты/Конвейер-верификации-оракулы-и-песочница]]
