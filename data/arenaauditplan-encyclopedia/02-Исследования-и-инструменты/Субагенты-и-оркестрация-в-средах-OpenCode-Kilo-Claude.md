---
id: "AAP-RES-SUBAGENTS"
title: "Субагенты и оркестрация в OpenCode, Kilo Code, Claude Code, Hermes и Codex (конфиги, setup-script.ps1, P1–P12)"
description: "Загружайте для настройки ролевых субагентов sf без правки CLI: сравнение 6 сред, opencode.jsonc, kilo.jsonc (shared_agent_board: false), .kilo/setup-script.ps1, .claude/agents, правила ЗДАВХ и плейбуки A–D."
status: "canonical"
track: "track-a-env"
stage: "F00"
paths: ["worktree.md", "data/subagents-encyclopedia/", "data/cli-skills-encyclopedia/Практики/Предотвращение ошибок.md"]
tags: [субагенты, opencode, kilo-code, claude-code, hermes, codex, windows, setup-script-ps1, конфиги]
aliases: ["Субагенты и оркестрация в средах OpenCode Kilo Claude", "Конфиги субагентов sf"]
---

# Субагенты и оркестрация в средах `OpenCode`, `Kilo Code`, `Claude Code`, `Hermes` и `Codex`

> [!abstract] Кратко
> Синтез возможностей современных агентных сред (включая профильные статьи из [subagents-encyclopedia](<../../subagents-encyclopedia/Главная.md>) и правила предотвращения ошибок **ЗДАВХ** из [Предотвращение ошибок.md](<../../cli-skills-encyclopedia/Практики/Предотвращение ошибок.md>)) позволяет развернуть все 7 ролей фабрики `sf` **в первый же день без правки кода `arch` CLI (Трек А, этап `F00`)**, снизив расход на типовой багфикс Laravel с `~50–70k` до **`~9–10k` токенов**.

## 1. Сравнительная матрица субагентных сред (на `2026-11-23`)

| Возможность | **OpenCode** ([docs](https://opencode.ai/docs/agents/)) | **Kilo Code** ([docs](https://kilo.ai/docs/customize/custom-subagents)) | **Claude Code** ([docs](https://code.claude.com/docs/en/sub-agents)) | **Nous Hermes** ([Hermes.md](<../../subagents-encyclopedia/Среды/Hermes.md>)) | **OpenAI Codex / Roo / Kiro** |
|---|---|---|---|---|---|
| **Изоляция контекста** | Свежая `child-session` | Независимая сессия (**отключить `shared_agent_board: false` против anchoring ревьюера!**) | Изолированный контекст `Agent` tool (`v2.1.63+`) | Изолированный воркер `delegate_task` (`handle`) | Per-task sandbox / `new_task` |
| **Режим и глубина** | Всегда `background`, `sessionID`, **`depth = 1`** | Foreground или `background: true`, child **не интерактивен** | Поддержка дерева с лимитом глубины | Live `steer` на лету, `max_spawn_depth: 1`, `max_concurrent_children: 3..10` | В `Codex` субагенты ограничены — нужен graceful fallback |
| **Per-agent модель и лимиты** | `model: provider/model#variant`, `steps: N` *(наследует родителя при пропуске!)* | `model`, `subagent_model`, `temperature`, `steps: N` *(наследует при пропуске!)* | `model` во frontmatter (`haiku/sonnet/opus`) + hooks | Отдельные модели в профиле (`kimi` оркестратор → `glm` исполнитель), `max_iterations` | Профили режимов / `AGENTS.md` |
| **Права и MCP Scoping** | Ordered `allow/ask/deny` (**`last-match-wins`**) + `Code Mode execute` (JS без записи в окно) | `permission.task` allowlist + bash-globs + `/sandbox` | `Agent(type)` allowlist + **`inline mcpServers` (`0` ток. схем в главной сессии!)** | Approval wave `v0.21` (запрет агенту молча менять `AGENTS.md` и скиллы) | Конфликт `orchestrator ↔ todo` (`Roo #5518`) |
| **Worktree и волны** | `worktree_create/list/remove` *(риск `detached HEAD`!)* | **`Agent Manager`**: до **`20` worktrees**, **`multi-version` до `4` моделей**, Windows `.ps1/.cmd/.bat` | Ручные/скриптовые `git worktrees` + `PreToolUse/PostToolUse` | `Worktree Mode` + `Kanban` + `three-strike circuit breaker` | `Kiro Waves` |
| **Главные грабли** | [`#6396`](https://github.com/sst/opencode/issues/6396): `deny` игнорировались через `task` | [`#13827`](https://github.com/Kilo-Org/kilocode/issues/13827); **закрытие worktree в UI удаляет ветку!** `Orchestrator` устарел; `` !`cmd` `` не работает в `.kilo/skills/` | Нужен `trust` папки для inline MCP; `disallowedTools: mcp__x` гасит весь сервер | Шум при `>15–20` скиллов в одном профиле | Обязателен односессионный fallback по шагам |

---

## 2. Семь канонических ролей `sf` и правила безошибочных скиллов (`ЗДАВХ`)

По таксономии [Предотвращение ошибок.md](<../../cli-skills-encyclopedia/Практики/Предотвращение ошибок.md>) каждый агентный файл и скилл строится по формуле **ЗДАВХ**: *(1) каждый запрет — с явной альтернативой («НЕ читай файл целиком → вызови `codegraph_explore`»), (2) `always / never` вместо мягких `should` + негативный триггер `Do NOT trigger on...` в `description`, (3) решение записывается в артефакт на диске, а не в пересказ чата (`Artifact-first`), (4) жёсткие инварианты выносятся в права и hooks, а не в прозу*.

| Роль `sf` | Субагент | Класс модели | Права доступа и границы доверия | Инструменты |
|---|---|---|---|---|
| `intake` и координация | `orchestrator` (`primary`) | средняя / сильная | `task`-allowlist субагентов, диалог с владельцем, `arch` CLI | `arch task / diagnose` |
| локализация контекста | `locator` | **дешёвая** | `read-only`, `shell: deny`, `edit: deny` | `codegraph / cbmemory` |
| планирование и дельты | `planner` | **сильная** | `read` + запись `stageN/workpack.json` и `flow-delta.json` | граф + `Graphify` / `arch docs` |
| тесты-оракулы (`Red`) | `oracle-keeper` | средняя | `edit tests/**` allow; `edit src/**` **deny**; тест-раннер | `codegraph affected` |
| узкая правка кода | `implementer` | **слабая / дешёвая** (`temp: 0.1`, `steps: 12`) | `edit` строго `allowed_paths` (**`tests/**` deny!**); `git push` deny | точечный `read` (**`0` графовых MCP!**) |
| независимая проверка | `verifier` | **другая модель** (`shared_agent_board: false`!) | `edit: deny`; только `git diff` и тест-раннер (без чата автора!) | граф + `diff` |
| учёт и закрытие | `docs-keeper` | дешёвая | только `arch` CLI + `doc/tasks/**` | `arch migrate / event / evidence / close` |

---

## 3. Полные готовые конфигурационные файлы и Windows `setup-script.ps1`

### 3.1. `OpenCode`: `.opencode/agents/locator.md`, `.opencode/agents/verifier.md`, `opencode.jsonc`

```markdown
---
description: Locates code context via graph tools BEFORE any file reading. Returns <=2000 token envelope. Do NOT trigger for code editing.
mode: subagent
model: openai/gpt-5-mini#low
steps: 6
permissions:
  - { action: edit, resource: "*", effect: deny }
  - { action: shell, resource: "*", effect: deny }
  - { action: read, resource: "src/**", effect: allow }
  - { action: read, resource: "app/**", effect: allow }
---
Ты — locator. Отвечай ТОЛЬКО через codegraph_explore / search_graph / trace_path.
Формат отчёта (envelope, <=2000 токенов):
{ "files": [...], "symbols": [...], "call_paths": [...], "tests_affected": [...], "open_questions": [...] }
Never read whole files. Never propose fixes or edit files.
```

```markdown
---
description: Independent per-function verifier on a different model. Reviews git diff against AC and invariants. Never sees implementer chat.
mode: subagent
model: anthropic/claude-sonnet-5-5#high
steps: 10
permissions:
  - { action: edit, resource: "*", effect: deny }
  - { action: shell, resource: "*", effect: deny }
  - { action: shell, resource: "git diff*", effect: allow }
  - { action: shell, resource: "php artisan test*", effect: allow }
  - { action: shell, resource: "vendor/bin/pest*", effect: allow }
---
Проверяй каждую изменённую функцию отдельно по 4 вопросам Winninger:
(1) тело соответствует имени/докблоку; (2) соблюдён I/O-контракт и граничные значения;
(3) нет необъявленных side-effects; (4) выдержаны инварианты модуля и unchanged_behavior из task.json.
Выдай JSON findings (severity + file:line). Never edit files.
```

```jsonc
// opencode.jsonc — ordered permissions (last-match-wins!)
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "codegraph": { "type": "local", "command": ["codegraph", "mcp"], "enabled": true },
    "cbmemory":  { "type": "local", "command": ["codebase-memory-mcp", "serve"], "enabled": true }
  },
  "agents": {
    "orchestrator": {
      "mode": "primary",
      "permissions": [
        { "action": "subagent", "resource": "*", "effect": "deny" },
        { "action": "subagent", "resource": "locator", "effect": "allow" },
        { "action": "subagent", "resource": "planner", "effect": "allow" },
        { "action": "subagent", "resource": "oracle-keeper", "effect": "allow" },
        { "action": "subagent", "resource": "implementer", "effect": "allow" },
        { "action": "subagent", "resource": "verifier", "effect": "allow" },
        { "action": "subagent", "resource": "docs-keeper", "effect": "allow" },
        { "action": "shell", "resource": "git push*", "effect": "deny" },
        { "action": "shell", "resource": "python3 doc/tools/arch/*", "effect": "allow" },
        { "action": "shell", "resource": "wsl python3 doc/tools/arch/*", "effect": "allow" }
      ]
    }
  }
}
```

### 3.2. `Kilo Code`: `kilo.jsonc` (с защитой от anchoring `shared_agent_board: false`), скилл `sf-go` и Windows `.kilo/setup-script.ps1`

```jsonc
{
  "$schema": "https://app.kilo.ai/config.json",
  "shared_agent_board": false,
  "agent": {
    "orchestrator": {
      "mode": "primary",
      "permission": {
        "task": { "*": "deny", "locator": "allow", "planner": "allow", "oracle-keeper": "allow", "implementer": "allow", "verifier": "allow", "docs-keeper": "allow" },
        "bash": { "*": "ask", "git diff*": "allow", "git status*": "allow", "php artisan test*": "allow", "vendor/bin/pest*": "allow", "python3 doc/tools/arch/*": "allow", "wsl python3 doc/tools/arch/*": "allow", "git push*": "deny" }
      }
    },
    "implementer": {
      "description": "Makes narrow code edits strictly inside allowed_edit_spans. Never edits tests/**.",
      "mode": "subagent",
      "model": "openai/gpt-5-mini",
      "temperature": 0.1,
      "steps": 12,
      "permission": { "edit": "allow", "bash": { "*": "deny", "php artisan test*": "allow", "vendor/bin/pest*": "allow", "git diff*": "allow" } }
    },
    "verifier": {
      "description": "Independent per-function review of diff vs AC on a different model.",
      "mode": "subagent",
      "model": "anthropic/claude-sonnet-4-20250514",
      "permission": { "edit": "deny", "bash": { "*": "deny", "git diff*": "allow", "php artisan test*": "allow", "vendor/bin/pest*": "allow" } }
    }
  }
}
```

```powershell
# .kilo/setup-script.ps1 — нативная подготовка изолированного worktree в Kilo Agent Manager на Windows
$ErrorActionPreference = "Stop"
$wt = if ($env:WORKTREE_PATH) { $env:WORKTREE_PATH } else { (Get-Location).Path }
$repo = if ($env:REPO_PATH) { $env:REPO_PATH } else { Split-Path $wt -Parent }

# 1. Детерминированное разведение портов и тестовой БД по хешу пути worktree (против гонок волн!)
$bytes = [System.Text.Encoding]::UTF8.GetBytes($wt)
$hash = [System.BitConverter]::ToUInt32(([System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)), 0)
$portOffset = [int]($hash % 900) + 100
$appPort = 8000 + $portOffset
$dbName  = "sf_wt_$portOffset.sqlite"

# 2. Копирование корневого и вложенных .env из базового репо с подстановкой изолированного PORT и DB
Get-ChildItem -Path $repo -Filter ".env" -Recurse -File -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -notmatch "\\(\.git|vendor|node_modules|\.kilo)\\" } |
  ForEach-Object {
    $rel = $_.FullName.Substring($repo.Length).TrimStart('\','/')
    $dst = Join-Path $wt $rel
    Copy-Item $_.FullName $dst -Force
  }
if (Test-Path (Join-Path $wt ".env")) {
  (Get-Content (Join-Path $wt ".env")) `
    -replace '^APP_PORT=.*$', "APP_PORT=$appPort" `
    -replace '^DB_DATABASE=.*$', "DB_DATABASE=$dbName" |
    Set-Content (Join-Path $wt ".env") -Encoding UTF8
}

# 3. Мгновенная распаковка предсобранного графа кода без повторного индексирования 3500+ файлов
$graphArchive = Join-Path $repo ".codebase-memory\graph.db.zst"
if ((Test-Path $graphArchive) -and (Get-Command zstd -ErrorAction SilentlyContinue)) {
  New-Item -ItemType Directory -Force -Path (Join-Path $wt ".codebase-memory") | Out-Null
  zstd -d -f $graphArchive -o (Join-Path $wt ".codebase-memory\graph.db") | Out-Null
}
Write-Host "Worktree ready at $wt (APP_PORT=$appPort, DB=$dbName). Commit/merge branch BEFORE closing worktree in Kilo UI!"
```

### 3.3. `Claude Code`: `.claude/agents/locator.md` и `.claude/agents/coordinator.md` (`Scoped MCP`)

```markdown
---
name: locator
description: Graph-first code localization. Use before any file reading. Do NOT use for editing.
tools: Read, mcp__codegraph__codegraph_explore, mcp__cbmemory__search_graph
model: haiku
mcpServers:
  - codegraph: { type: stdio, command: codegraph, args: ["mcp"] }
  - cbmemory:  { type: stdio, command: codebase-memory-mcp, args: ["serve"] }
---
Возвращай envelope <=2000 токенов: files/symbols/call_paths/tests_affected.
```

```markdown
---
name: coordinator
description: Coordinates sf task execution across bounded subagents
tools: Agent(locator, planner, oracle-keeper, implementer, verifier, docs-keeper), Read, Bash
---
Вход задачи: arch task diagnose (+ arch task migrate для новых задач в 0-diff режиме). Контекст — строго через locator.
```

*(Graceful fallback для сред без субагентов, таких как базовый `Codex`: тот же конвейер выполняется последовательными фазами с записью промежуточных артефактов `envelope.json → red-test → patch → verifier-checklist` на диск).*

---

## 4. Сводка 12 приёмов оркестрации (`P1..P12`) и 4 операционных плейбуков (`A–D`)

- **`P1..P12`:** `P1` `Graph-first envelope ≤2k`; `P2` `OpenCode Code Mode execute` (JS-батчи без засорения контекста); `P3` `Scoped MCP` (`inline mcpServers` у `locator/verifier`, `0` у `implementer`); `P4` параллельный фоновый старт `locator + oracle-keeper`; `P5` волны `Kilo Agent Manager` (до 20 worktrees + `multi-version` турнир слабой и средней модели на одном промпте!); `P6` явный `model`, `steps: 12`, `temperature: 0.1`; `P7` bash/task allowlists и эскалация вопросов владельцу через `orchestrator`; `P8` `.kilo/setup-script.ps1` + запрет общего `git stash` + мерж ветки до закрытия worktree; `P9` `metadata-only` скилл `sf-go` (без `` !`cmd` `` в проектном `.kilo/skills/`); `P10` независимый `verifier` по Winninger при `shared_agent_board: false`; `P11` `Cold Resume` (`passes: false` + входной smoke); `P12` `PreToolUse / PostToolUse` хуки графа.
- **Плейбуки `A–D`:** **A** — микро-багфикс Laravel за `6` шагов и **`~9 100` ток.** (`orchestrator ~800 → locator ~1 200 → oracle-keeper ~1 500 → implementer ~3 000 → verifier ~2 000 → docs-keeper ~600`); **B** — фича на 3 непересекающихся `worktree`-волнах в `Kilo Agent Manager`; **C** — ночной автономный цикл внутри `/sandbox` + контейнерного `egress allowlist` со стопом при `gate red 2×` (или `three-strike` по Hermes); **D** — периодический аудит репо `CodePrizm + Graphify` с конвертацией в карточки `audit`.

## Связи

- [[Главная]] · [[02-Исследования-и-инструменты/Подключаемые-графы-кода-аудит-и-компрессоры]] · [[03-Архитектура-и-контракты/Двухтрековая-архитектура-sf-v3-и-граница-ядра]] · [[04-Реестр-проблем-и-требований/Мастер-реестр-проблем-PROB-01-PROB-38]] · [[05-Этапы-внедрения/F00-Среда-и-субагенты-без-правки-CLI]]
