---
tags: [среда, opencode, субагенты]
aliases: [OpenCode, opencode]
---

# OpenCode

> [!info] Определение
> Открытая агентная среда (ядро Kilo Code). Два режима агентов: primary (прямое
> взаимодействие, Tab) и subagent (вызов агентом или @mention). Конфиг — JSON или Markdown.
> См. [[Паттерны оркестрации]], [[Назначение скиллов субагентам]].

## Режимы агентов

| Режим | Использование | Вызов |
|---|---|---|
| primary | Главный ассистент | Tab (переключение) |
| subagent | Специалист | Агент делегирует или @mention |
| all | Оба (default) | — |

**Встроенные субагенты**: `@general` (полные инструменты, read/write), `@explore`
(read-only, быстрое исследование).

## Конфигурация

Три способа: `opencode agent create` (интерактивно), `.opencode/agents/*.md`,
`opencode.json` → `agent.{name}`.

| Поле | Назначение |
|---|---|
| description | Что делает и когда использовать (триггер делегации) |
| mode | primary / subagent / all |
| model | Модель агента (разные модели на разных агентов) |
| temperature | 0.1–0.3 для кода/ревью; выше — для креатива |
| tools | Включение/отключение инструментов per agent |
| permission | ask / allow / deny per tool |
| task | Включение оркестрации (агент может спавнить субагентов) |

## Назначение скиллов субагентам

- Скиллы: `.opencode/skills/` (SKILL.md стандарт).
- Субагент получает только нужные инструменты: read-only ревьюеру — read/grep/glob без bash.
- Принцип: «Don't give bash unless agent needs CLI execution».

## Оркестрация

- Task tool: агент с включённым `task` спавнит субагентов.
- Глубина: максимум 2 уровня (не глубже).
- Batch size: 5–8 элементов на агента; параллельно 2–4 агента.
- Permission на task: allowlist, какие субагенты разрешено вызывать.

## Пример: release-orchestrator

```json
{
  "agent": {
    "release-orchestrator": {
      "description": "Coordinates release preparation. Use before releases.",
      "mode": "subagent",
      "tools": { "read": true, "grep": true, "glob": true, "task": true },
      "permission": {
        "task": {
          "code-reviewer": "allow",
          "test-runner": "allow",
          "doc-validator": "allow",
          "*": "deny"
        }
      }
    }
  }
}
```

## Диаграмма

```mermaid
flowchart TB
    PRIMARY[Primary агент] -->|task tool| SUB1[Субагент: code-reviewer]
    PRIMARY -->|task tool| SUB2[Субагент: test-runner]
    PRIMARY -->|@mention| SUB3[Субагент: explore]
    SUB1 -->|результат| PRIMARY
    SUB2 -->|результат| PRIMARY
```

## Мнемоника

**«Primary — общается, Subagent — исполняет, Task — делегирует»** — ПСТ.

## Связи

- [[Kilo Code]] · [[Паттерны оркестрации]] · [[Назначение скиллов субагентам]] · [[Модели и стоимость]] · [[Справочник сред]]

## Типичные ошибки

> [!warning]
> Субагент без keyword-rich description: агент не делегирует. Bash всем субагентам:
> нарушение least privilege. Глубина >2: сложность отладки. Fast-tier модель для контента:
> заметная потеря качества.
