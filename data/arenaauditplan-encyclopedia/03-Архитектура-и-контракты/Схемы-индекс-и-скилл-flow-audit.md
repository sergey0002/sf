---
id: "AAP-ARCH-FLOWSCHEMA"
title: "JSON Schema arch-flow.schema.json, матрица 32 модулей CLI, контракт flows.index.json и скилл flow-audit"
description: "Загружайте при кодинге валидатора и билдера *.flow.json (UI-0029): содержит полную Draft 2020-12 JSON Schema, матрицу покрытия всех 32 модулей arch CLI, 20 CLI-команд и шаблон скилла flow-audit."
status: "canonical"
track: "track-b-core"
stage: "F2"
paths: ["doc/tools/arch/", "doc/architecture/schemas/", "doc/config/paths.yaml", "doc/skills/"]
tags: [arch-flow-schema, json-schema, flows-index, flow-audit, flow-delta, cli-commands, ui-0029]
aliases: ["JSON Schema arch-flow, 32 модуля и скилл flow-audit", "Схемы индекс и скилл flow-audit"]
---

# JSON Schema `arch-flow.schema.json`, матрица 32 модулей CLI, контракт `flows.index.json` и скилл `flow-audit`

> [!abstract] Кратко
> Полный нормативно-технический пакет реализации архитектурных флоу (в пару к концептуальной заметке [[03-Архитектура-и-контракты/Спецификация-архитектурных-флоу-flow-json]]): эталонная схема `doc/architecture/schemas/arch-flow.schema.json` (не затирающая `schemas/flow.schema.json` от `task-conf`), 100%-я матрица покрытия всех 32 Python-модулей `doc/tools/arch/`, контракт индекса `flows.index.json`, полный справочник 20 CLI-команд и готовый макет навыка `doc/skills/flow-audit/SKILL.md`.

## 1. Полная матрица покрытия всех 32 модулей `doc/tools/arch/` и 5 доменов `sf`

Каждый файл в [doc/tools/arch/](<../../../doc/tools/arch/>) либо привязан к целевому `*.flow.json`, либо явно занесён в `flow_coverage.exempt_globs` как чистая инфраструктурная прослойка без доменных развилок:

| Домен / класс | Целевой `*.flow.json` | Покрываемые модули `doc/tools/arch/` и команды CLI | Связанные `ENT-* / CAP-* / REG-*` |
|---|---|---|---|
| **`task-intake`** | `FLOW-create-task` (`implemented: true`) | `task_ops.py` (`new`, `init`), `task_registry.py` (`init/add/check/sync`), `identity.py`, `validation.py#parse_task_key`, `cli/commands/task_key.py` | `CAP-task-intake`, `REG-task-number-registry`, `ENT-task-input`, `ENT-task-record` |
| **`task-lifecycle`** | `FLOW-task-lifecycle` (`implemented: true`) | `task_ops.py` (`validate/workspace/status/diagnose/doctor/close/migrate/baseline`), `task_record.py`, `plan_policy.py`, `cli/commands/task.py` | `ENT-task-record`, `ENT-stage-artifact`, `REG-cli-validation-rules` |
| **`task-lifecycle`** | `FLOW-task-flow-execution` (`implemented: true`, заменяет `FLOW-execute-task`) | `flows.py` (`types/flows/select-flow/flow-steps/advance/event/replay`) | `ENT-flow-definition`, `CAP-single-agent-execution` |
| **`task-lifecycle`** | `FLOW-subtask-lifecycle` (`implemented: true`) | `subtask.py`, `task_ops.py` (`decompose`, `subtask init/validate/status`) | `ENT-task-record`, `UI-0030` |
| **`execution-verification`** | `FLOW-verify-task` (`implemented: true`) | `evidence.py`, `acceptance.py`, `task_ops.py` (`evidence`, SHA-256 снимка и `case-coverage-v1`) | `ENT-verification-evidence`, `ENT-stage-artifact` |
| **`execution-verification`** | `FLOW-document-session` (`implemented: true`) | Оркестрация скилла `document-session` поверх `validate`, `index check`, `docs check-links` | `CAP-doc-integrity`, `ARCH-contract` |
| **`execution-verification`** | `FLOW-kilo-session-audit` (`implemented: true`) | `session_audit.py` (1222 строки), `cli/commands/session.py` (`find/digest/events`) | Выделяемый `SPEC-kilo-session-audit` |
| **`project-knowledge`** | `FLOW-docs-validation-and-indexing` (**новый**, `implemented: true`) | `store.py`, `body_validation.py`, `sections.py`, `validation.py`, `cli/commands/builtin.py` (`index/validate/paths/check-links/scan`), `arch_flows.py` | `CAP-project-knowledge`, `CAP-doc-integrity`, `ARCH-contract` |
| **`project-knowledge`** | `FLOW-docs-retrieval-and-impact` (**новый**, `implemented: true`) | `doc_ops.py` (1322 строки: `search/read/toc/tree/related/context/impact`), двухкольцевой радар `arch_flows.py` | `CAP-addressable-contracts`, `GLO-system` |
| **`model-routing`** | `FLOW-role-model-routing` (`implemented: false`, `draft`) | Плановый домен (`CAP-role-model-routing`, реализуется на этапе [[05-Этапы-внедрения/F3-Песочница-волны-роутинг-и-Cold-Resume\|F3]]) | `CAP-role-model-routing` |
| **`exempt_infrastructure`** | `flow_coverage.exempt_globs` в `paths.yaml` | `__init__.py`, `__main__.py`, `constants.py`, `fs_atomic.py`, `project_config.py`, `schema.py`, `cli/{__init__,app,errors,output}.py`, `cli/commands/{__init__,base,registry}.py` | Утилиты I/O, констант и обёрток CLI без собственного бизнес-процесса |

---

## 2. Полная JSON Schema `doc/architecture/schemas/arch-flow.schema.json` (Draft 2020-12)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sf.local/schemas/arch-flow.schema.json",
  "title": "Architectural System Flow (Decision Tree + Process Lifecycle)",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version", "id", "type", "domain", "title", "summary",
    "status", "implemented", "actors", "invariants", "not_included",
    "lifecycle", "factors", "decisions"
  ],
  "properties": {
    "schema_version": { "const": 1 },
    "id": { "type": "string", "pattern": "^FLOW-[a-z0-9][a-z0-9-]*$", "minLength": 7, "maxLength": 96 },
    "type": { "const": "flow" },
    "domain": { "type": "string", "pattern": "^[a-z][a-z0-9-]*$" },
    "title": { "type": "string", "minLength": 3 },
    "summary": { "type": "string", "minLength": 10 },
    "status": { "enum": ["draft", "current", "accepted", "deprecated", "superseded"] },
    "superseded_by": { "type": ["string", "null"], "pattern": "^FLOW-[a-z0-9][a-z0-9-]*$" },
    "owner": { "type": ["string", "null"] },
    "implemented": { "type": "boolean" },
    "applicability": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "cli_version": { "type": "string" },
        "task_schema": { "type": "string" },
        "scope_note": { "type": "string" }
      }
    },
    "provenance": { "type": "string", "minLength": 1 },
    "actors": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "kind", "role"],
        "properties": {
          "id": { "type": "string", "pattern": "^[a-z][a-z0-9_-]*$" },
          "kind": { "enum": ["human", "agent", "system", "external"] },
          "title": { "type": "string" },
          "role": { "type": "string", "minLength": 3 }
        }
      }
    },
    "preconditions": { "type": "array", "items": { "type": "string", "minLength": 1 } },
    "invariants": { "type": "array", "minItems": 1, "items": { "type": "string", "minLength": 3 } },
    "not_included": { "type": "array", "minItems": 1, "items": { "type": "string", "minLength": 3 } },
    "lifecycle": {
      "type": "object",
      "additionalProperties": false,
      "required": ["mode", "target_entities", "states", "idempotency", "concurrency_guard"],
      "properties": {
        "mode": { "enum": ["stateful", "stateless"] },
        "target_entities": { "type": "array", "items": { "type": "string", "pattern": "^ENT-[a-z0-9][a-z0-9-]*$" } },
        "initial_states": { "type": "array", "items": { "type": "string", "pattern": "^[a-z][a-z0-9_-]*$" } },
        "states": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["id", "kind", "description"],
            "properties": {
              "id": { "type": "string", "pattern": "^[a-z][a-z0-9_-]*$" },
              "kind": { "enum": ["initial", "intermediate", "terminal"] },
              "description": { "type": "string", "minLength": 3 }
            }
          }
        },
        "idempotency": {
          "type": "object",
          "additionalProperties": false,
          "required": ["strategy", "on_duplicate"],
          "properties": {
            "strategy": { "enum": ["none", "keyed", "content_hash", "state_guard", "read_only"] },
            "key": { "type": ["string", "null"] },
            "on_duplicate": { "type": "string", "minLength": 3 }
          }
        },
        "concurrency_guard": { "type": "string", "minLength": 3 }
      }
    },
    "factors": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "title", "type", "allowed_values"],
        "properties": {
          "id": { "type": "string", "pattern": "^[a-z][a-z0-9_]*$" },
          "title": { "type": "string", "minLength": 2 },
          "type": { "enum": ["enum", "boolean"] },
          "allowed_values": { "type": "array", "minItems": 2, "uniqueItems": true, "items": { "type": ["string", "boolean"] } },
          "description": { "type": "string" }
        }
      }
    },
    "decisions": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "title", "evaluated_factors", "hit_policy", "branches"],
        "properties": {
          "id": { "type": "string", "pattern": "^[a-z][a-z0-9-]*$" },
          "title": { "type": "string", "minLength": 3 },
          "entry_states": { "type": "array", "items": { "type": "string" } },
          "evaluated_factors": { "type": "array", "minItems": 1, "uniqueItems": true, "items": { "type": "string" } },
          "hit_policy": { "enum": ["UNIQUE", "ANY", "PRIORITY", "FIRST", "COLLECT"] },
          "output_priority": { "type": "array", "items": { "type": "string" } },
          "branches": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/branch" } }
        }
      }
    },
    "superseded_branches": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "superseded_by", "reason"],
        "properties": {
          "id": { "type": "string", "pattern": "^[a-z][a-z0-9-]*$" },
          "superseded_by": { "type": "string", "pattern": "^FLOW-[a-z0-9][a-z0-9-]*#[a-z][a-z0-9-]*$" },
          "reason": { "type": "string", "minLength": 3 }
        }
      }
    }
  },
  "allOf": [
    {
      "if": { "properties": { "status": { "const": "superseded" } } },
      "then": { "required": ["superseded_by"], "properties": { "superseded_by": { "type": "string" } } }
    }
  ],
  "$defs": {
    "branch": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "title", "decision_maker", "when", "effects", "outcome", "oracle_status", "refs"],
      "properties": {
        "id": { "type": "string", "pattern": "^[a-z][a-z0-9-]*$" },
        "title": { "type": "string", "minLength": 3 },
        "decision_maker": { "enum": ["deterministic", "agent_judgment", "human_approval"] },
        "when": {
          "type": "object",
          "minProperties": 1,
          "additionalProperties": {
            "oneOf": [
              { "type": ["string", "boolean"] },
              { "type": "array", "minItems": 1, "uniqueItems": true, "items": { "type": ["string", "boolean"] } }
            ]
          }
        },
        "steps": { "type": "array", "items": { "type": "string", "minLength": 3 } },
        "transition": {
          "type": "object",
          "additionalProperties": false,
          "required": ["from", "to"],
          "properties": {
            "from": { "oneOf": [{ "type": "string" }, { "type": "array", "minItems": 1, "items": { "type": "string" } }] },
            "to": { "type": "string" },
            "state_unchanged_on_disk": { "type": "boolean" }
          }
        },
        "effects": {
          "type": "object",
          "additionalProperties": false,
          "required": ["mutates", "atomicity"],
          "properties": {
            "mutates": { "type": "array", "items": { "type": "string", "minLength": 1 } },
            "mutates_db": { "type": "array", "items": { "type": "string", "minLength": 1 } },
            "emits_events": { "type": "array", "items": { "type": "string", "minLength": 1 } },
            "external_calls": { "type": "array", "items": { "type": "string", "minLength": 1 } },
            "idempotency_key": { "type": "string", "minLength": 1 },
            "atomicity": { "enum": ["read_only", "atomic", "compensated", "best_effort"] },
            "rollback": { "type": "string" }
          }
        },
        "retry_policy": {
          "type": "object",
          "additionalProperties": false,
          "required": ["retry_when", "on_exhausted"],
          "properties": {
            "retry_when": { "type": "string" },
            "max_attempts": { "type": "integer", "minimum": 1 },
            "timeout": { "type": "string" },
            "on_exhausted": { "type": "string" }
          }
        },
        "outcome": {
          "type": "object",
          "additionalProperties": false,
          "required": ["kind", "summary", "postconditions"],
          "properties": {
            "kind": { "enum": ["ok", "blocked", "error", "retry", "finding"] },
            "exit_code": { "type": ["integer", "null"] },
            "http_status": { "type": ["integer", "null"], "minimum": 100, "maximum": 599 },
            "error_code": { "type": ["string", "null"] },
            "summary": { "type": "string", "minLength": 3 },
            "postconditions": { "type": "array", "minItems": 1, "items": { "type": "string", "minLength": 3 } }
          }
        },
        "next": {
          "type": "object",
          "additionalProperties": false,
          "required": ["kind"],
          "properties": {
            "kind": { "enum": ["end", "decision", "flow"] },
            "target": { "type": "string" }
          }
        },
        "oracle_status": { "enum": ["verified", "missing_oracle", "manual_only"] },
        "refs": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "rules": { "type": "array", "items": { "type": "string" } },
            "contracts": { "type": "array", "items": { "type": "string" } },
            "entities": { "type": "array", "items": { "type": "string" } },
            "flows": { "type": "array", "items": { "type": "string" } },
            "skills": { "type": "array", "items": { "type": "string" } },
            "terms": { "type": "array", "items": { "type": "string" } },
            "code": { "type": "array", "items": { "type": "string" } },
            "tests": { "type": "array", "items": { "type": "string" } },
            "tasks": { "type": "array", "items": { "type": "string" } }
          }
        }
      }
    }
  }
}
```

---

## 3. Контракт графового индекса `flows.index.json` и полный справочник 20 CLI-команд

В `doc/architecture/flows.index.json` генерируются 3 корневых ключа: `flows[]`, `branches[]` и обратный граф `referenced_by` по **8 осям** (`by_entity`, `by_contract`, `by_term`, `by_code`, `by_test`, `by_mutated_path`, `by_flow`, `by_task`). В карточке `task.json` для привязки к веткам флоу вводится типизированное поле **`"flow_refs": ["FLOW-...", "FLOW-...#branch-id"]`** (так как `related_docs` в `validation.py` занято под `TASK_KEY_RE`).

| Команда CLI | Назначение и возвращаемый срез | Коды выхода |
|---|---|---:|
| `arch docs flow list [--domain <d>] [--status <s>] [--implemented true\|false] [--json]` | Компактный список флоу с числом узлов/веток и `oracle_counts` (~100 Б/флоу) | `0, 2` |
| `arch docs flow show <FLOW-ID> --view summary\|decisions\|transitions\|mermaid\|refs\|gaps [--json]` | Выдача ровно одной проекции выбранного флоу | `0, 2, 20` |
| `arch docs read <FLOW-ID>[#<branch-id>] [--max-bytes N] [--json]` | Карточка **одной ветки** + её `evaluated_factors`, `invariants` и `refs` (`0.5–1.5 КБ`) | `0, 2, 20` |
| `arch docs flow refs <TARGET> [--kind entity\|contract\|term\|code\|test\|path\|flow\|task] [--json]` | Мгновенная обратная выборка из `flows.index.json#referenced_by` | `0, 2, 20` |
| `arch docs search "<query>" [--flows] [--domain <d>] [--path <p>] [--symbol <s>] [--json]` | Поиск с расширением синонимов через `glossary.index.json` (`UI-0028`) | `0, 2` |
| `arch docs context --task <KEY> [--flows] [--max-bytes N] [--json]` | **Двухкольцевой радар задачи** (`participating` + 1-hop `impacted` + `unmapped_paths` + `missing_oracles`) | `0, 2, 20` |
| `arch docs impact [--since <rev> \| --paths <p...>] --flows [--json]` | Сверка планируемых путей или `git diff` с графом флоу (`unmapped_code_changes`) | `0, 1, 2` |
| `arch docs flow validate [--id <FLOW-ID>] [--json]` | JSON Schema + DMN (`0 gaps / 0 overlaps / no masked`) + автомат `lifecycle` + `refs` | `0, 1, 2, 20` |
| `arch docs flow build [--id <FLOW-ID>] [--json]` | Побайтно идемпотентная генерация `<slug>.md` и `flows.index.json` | `0, 1, 10` |
| `arch docs flow check [--json]` | Проверка отсутствия ручных правок в generated `<slug>.md` и `flows.index.json` | `0, 1` |
| `arch docs flow coverage [--domain <d>] [--ratchet --since <rev>] [--strict] [--json]` | Отчёт полноты (с `--ratchet` проверяет только затронутые в diff модули brownfield-базы!) | `0, 1` |
| `arch docs flow correlate (--task <KEY> \| --entity <ENT-*> \| --term <TERM-*> \| --path <p>) [--json]` | Граф всех прямых (`distance: 0`) и сцепленных (`distance: 1..2`) флоу вокруг сущности/модуля | `0, 2, 20` |
| `arch docs flow inspect <FLOW-ID \| path[#symbol]> [--json]` | Сверка символов/AST и сигналов графа кода с ветками флоу (`undocumented_error_signals`, `mutation_signals`, `lines`) | `0, 1, 2, 20` |
| `arch docs flow capsule (--task <KEY> \| --branch <FLOW-ID#b>) [--budget-tokens <N>] [--json]` | **Одновызовная капсула слабой модели** (`1.5K–4.5K` ток.): только целевая ветка + AST-строки + `refs.tests` + `RO Trust Zone` | `0, 2, 20` |
| `arch docs flow verify (<FLOW-ID>[#<b>] \| --changed \| --task <KEY>) [--assert-guard] [--atomicity-check]` | Прогон узловых тестов с защитой от удаления `assert*` и проверкой `state_unchanged_on_disk` | `0, 1, 2, 10, 20` |
| `arch docs flow delta validate <path/to/flow-delta.json> [--json]` | Валидация схемы дельты и результирующей DMN-таблицы в памяти без записи на диск | `0, 1, 2, 5, 20` |
| `arch docs flow delta apply <path/to/flow-delta.json> [--dry-run] [--json]` | Проверка `base_sha256` (`5` при конфликте) + атомарное применение `add/modify/remove/supersede_branch/remap_code` | `0, 1, 2, 5, 10, 20` |
| `arch scan --scope flows [--json]` | Поиск `stale_provenance`, зависших `missing_oracle` и `unmapped_domain_code` | `0, 1` |
| `arch task decompose <KEY> --spec <file> [--json]` | Блокировка конфликтующих правок одной ветки `FLOW-ID#branch-id` между параллельными подзадачами | `0, 1, 5` |
| `arch task diagnose <KEY>` / `arch task close <KEY> [--dry-run] [--json]` | Проверка применения `flow-delta.json`, зелёного `flow check` и покрытия `verified`-веток в `verification.json` | `0, 1` |

---

## 4. Готовый эталонный макет скилла `doc/skills/flow-audit/SKILL.md` (5 шагов и 4 корзины триажа)

Оформлен строго по стандартам [Agent Skills (SKILL.md).md](<../../cli-skills-encyclopedia/Форматы/Agent Skills (SKILL.md).md>) и [Предотвращение ошибок.md](<../../cli-skills-encyclopedia/Практики/Предотвращение ошибок.md>):

```markdown
---
name: flow-audit
description: Find all architectural flows correlated with a task, entity, term, or module, audit their completeness against actual code/graph inspection, and complete or split *.flow.json models. Do NOT trigger for simple read-only contract lookup (use architecture-read).
---
# Skill: flow-audit
1. Корреляционный контур (без слепого чтения репо):
   `arch docs flow correlate (--task <KEY> | --entity <ENT-*> | --term <TERM-*> | --path <p>) --include-unmapped --json`
2. Инспекция кода и графа:
   `arch docs flow inspect <FLOW-ID | path[#symbol]> --json`
3. Адресное чтение ТОЛЬКО указанных `lines` и разбор на 4 корзины триажа:
   - `missing_branch_in_flow`: законное доменное правило кода не отражено во флоу -> добавить ветку в `*.flow.json`;
   - `implementation_bug_or_gap`: контракт `CAP-*/REG-*` верен, код ошибается -> НЕ подгонять флоу под баг! Оформить `finding` / фикс;
   - `incidental_plumbing`: чисто техническая обёртка без доменного исхода -> оставить в коде / `exempt_globs`;
   - `ambiguous_intent`: неясно, задумка или баг -> вынести `NEEDS CLARIFICATION` владельцу.
4. Проверка 6 границ нарезки (`<=4` узлов `decisions[]`, `<=15` веток); при превышении — отщепить через `next: {"kind": "flow"}` и `superseded_branches`.
5. Детерминированное замыкание: `flow validate` -> `flow build` -> `flow inspect` -> `flow check` -> `docs check-links`.
```

## Связи

- [[Главная]] · [[Справочник артефактов, команд и схем]] · [[03-Архитектура-и-контракты/Спецификация-архитектурных-флоу-flow-json]] · [[05-Этапы-внедрения/F2-Флоу-контракты-Validity-L1-и-Verifier]]
