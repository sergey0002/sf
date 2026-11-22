---
tags: [инструмент, sdd]
aliases: [Spec Kit, specify-cli]
---

# GitHub Spec Kit

> [!info] Определение
> Open-source toolkit (MIT) от GitHub (сентябрь 2025): slash-команды SDD в 30–40+
> AI-агентах. Не агент, а конвейер. См. [[Workflow SDD]].

## Команды и артефакты

| Команда | Артефакт |
|---|---|
| `/speckit.constitution` | `.specify/memory/constitution.md` |
| `/speckit.specify` | `specs/NNN-name/spec.md` |
| `/speckit.clarify` | Дополнения в spec.md |
| `/speckit.plan` | `plan.md`, `data-model.md`, `contracts/`, `research.md`, `quickstart.md` |
| `/speckit.checklist` | Чек-листы |
| `/speckit.tasks` | `tasks.md` |
| `/speckit.analyze` | Отчёт (read-only) |
| `/speckit.implement` | Код, тесты |
| `/speckit.converge` | Дополнения (append-only) |

## Структура репозитория

```
project/
├── .specify/
│   ├── memory/constitution.md
│   ├── templates/
│   └── scripts/
├── specs/001-feature-name/
│   ├── spec.md, plan.md, tasks.md
│   ├── data-model.md, research.md, quickstart.md
│   ├── contracts/
│   └── checklists/
└── .github/prompts/
```

## Диаграмма

```mermaid
flowchart LR
    C[/constitution/] --> S[/specify/] --> CL[/clarify/] --> P[/plan/]
    P --> CH[/checklist/] --> T[/tasks/] --> A[/analyze/] --> I[/implement/] --> CV[/converge/]
```

## Мнемоника

**КСУПЧДАРС** — «Конституция Специфицирует, Уточняет, Планирует, Проверяет (чек-лист),
Декомпозирует (задачи), Анализирует, Реализует, Сверяет (converge)».

## Связи

- [[Конституция]] · [[Спецификация]] · [[План]] · [[Задачи]] · [[Workflow SDD]]

## Сильные/слабые стороны

Плюс: портативность, полный набор команд, конституция.
Минус: много Markdown для ревью; коллизии нумерации спек при параллельной работе.
