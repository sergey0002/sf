---
title: "llms.txt"
description: "Загружайте, когда задача касается: Курируемый Markdown-индекс в корне сайта: что это за проект и какие страницы читать первыми."
tags: [формат, llms]
paths: []
aliases: []
---

# llms.txt

> [!info] Определение
> Курируемый Markdown-индекс в корне сайта: что это за проект и какие страницы
> читать первыми. Не перечисляет всё (как sitemap), а отбирает важное.
> См. [[Index-First подход]], [[AGENTS.md Index]].

## Стандарт / источник

- Предложение Jeremy Howard (fast.ai), сентябрь 2024; llmstxt.org, v2.
- Принят: Anthropic, Stripe, Vercel, Cloudflare, Mastercard, ElevenLabs.
- Читают: Cursor, Continue, Cline, MCP-интеграции; Chrome Lighthouse — аудит llms.txt.
- Не официальный стандарт (нет RFC), но де-факто конвенция.

## Формат

| Элемент | Обязательность | Назначение |
|---|---|---|
| H1 | Обязателен | Имя проекта |
| Blockquote | Рекомендуется | Краткое резюме для LLM |
| ## Docs | Опционально | Основные документационные URL |
| ## Examples | Опционально | Примеры кода и туториалы |
| ## Optional | Опционально | Дополнительные ресурсы |

## Пример

```markdown
# MyProject

> API для управления заказами: REST, webhooks, SDK для Python и TypeScript.

## Docs

- [Getting Started](https://example.com/docs/getting-started.md): установка и первый вызов
- [API Reference](https://example.com/docs/api.md): все эндпоинты и параметры
- [Webhooks](https://example.com/docs/webhooks.md): события и ретраи

## Examples

- [Create Order](https://example.com/docs/examples/create-order.md): полный пример на Python

## Optional

- [Changelog](https://example.com/changelog.md): история изменений
```

## llms-full.txt

Полная текстовая версия: весь контент страниц из llms.txt, без навигации и маркетинга.
Vercel: llms.txt — селективный навигационный слой, llms-full.txt — полный контекст.

## Диаграмма

```mermaid
flowchart LR
    AGENT[Агент] -->|читает| LLMS[[llms.txt]]
    LLMS -->|выбирает| DOCS[Страницы .md]
    AGENT -->|при полном контексте| FULL[[llms.txt|llms-full.txt]]
```

## Мнемоника

**«Заголовок, Резюме, Доки, Примеры, Опционально»** — ЗРДПО.

## Связи

- [[Index-First подход]] · [[AGENTS.md Index]] · [[Структурированный Markdown]] · [[AI-Native Documentation]]

## Типичные ошибки

> [!warning]
> llms.txt как sitemap (все страницы): курируйте, а не перечисляйте. Ссылки на HTML
> вместо Markdown-версий: агент парсит HTML. Устаревший llms.txt: хуже, чем отсутствие.
