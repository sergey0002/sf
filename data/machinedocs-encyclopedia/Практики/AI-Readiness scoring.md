---
title: "AI-Readiness scoring"
description: "Загружайте, когда задача касается: Оценка 0–100: насколько легко LLM-агент извлекает точные ответы из документации."
tags: [практика, scoring]
paths: []
aliases: []
---

# AI-Readiness scoring

> [!info] Определение
> Оценка 0–100: насколько легко LLM-агент извлекает точные ответы из документации.
> Инструмент измерения качества машиночитаемости. См. [[AI-Native Documentation]],
> [[Семантический чанкинг]].

## Стандарт / источник

- AI-native documentation MVP: AI-readiness scoring (Day 2–3).
- AgentSpeed: 10 проверок в двух тирах, взвешенный score 0–100.
- Chrome Lighthouse: аудит llms.txt в agentic browsing checks.

## Что измеряется

| Измерение | Вопрос |
|---|---|
| Структура | Парсится ли иерархия предсказуемо? |
| Метаданные | Есть ли explicit metadata (frontmatter, схемы)? |
| Атомарность | Извлекаются ли факты без контекста? |
| Индекс | Есть ли точка входа (llms.txt, AGENTS.md)? |
| Актуальность | Документация свежая (staleness)? |
| Связи | Явные ли связи между компонентами? |

## Пример отчёта

```
AI-Readiness: 72/100
✓ llms.txt present and valid
✓ AGENTS.md index generated
✗ 3 docs stale (maxAgeDays exceeded)
✗ No frontmatter on docs/billing.md
✓ OpenAPI schema versioned
→ Fix: refresh billing docs, add frontmatter
```

## Диаграмма

```mermaid
flowchart LR
    DOCS[Документация] --> SCORE[AI-Readiness score]
    SCORE -->|проверки| FIX[Список исправлений]
    FIX --> DOCS
```

## Мнемоника

**«Структура, Метаданные, Атомарность, Индекс, Свежесть»** — СМАИС.

## Связи

- [[AI-Native Documentation]] · [[Актуальность и staleness]] · [[Структурированный Markdown]] · [[Чек-листы]]

## Типичные ошибки

> [!warning]
> Score без списка исправлений: не actionable. Оценка разово: дрейф не ловится.
> Высокий score при устаревшем контенте: свежесть — отдельный гейт.
