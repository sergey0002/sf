---
tags: [формат, cli]
aliases: [Man Pages, Страницы руководства]
---

# Man Pages

> [!info] Определение
> Страницы руководства Unix (troff): полное описание команды для человека.
> Для агента — вторичный источник после [[Help-текст CLI]] и [[JSON Schema и Self-Description]].
> См. [[Agent-Friendly CLI Design]].

## Стандарт / источник

- Unix-традиция: секции NAME, SYNOPSIS, DESCRIPTION, OPTIONS, EXIT STATUS, EXAMPLES, SEE ALSO.
- Формат: troff/groff; современно — Markdown-генераторы (pandoc, help2man).

## Формат

| Секция | Содержимое |
|---|---|
| NAME | Имя и краткое описание |
| SYNOPSIS | Синтаксис вызова |
| DESCRIPTION | Подробное описание |
| OPTIONS | Все флаги с описанием |
| EXIT STATUS | Коды возврата |
| EXAMPLES | Примеры использования |
| SEE ALSO | Связанные команды |

## Пример

```text
MYCTL(1)                     User Commands                    MYCTL(1)

NAME
       myctl - deploy services

SYNOPSIS
       myctl deploy SERVICE --env ENV [--json] [--dry-run]

DESCRIPTION
       Deploy a service to the target environment...

EXIT STATUS
       0  success
       2  argument error
       5  conflict
```

## Диаграмма

```mermaid
flowchart LR
    MAN[[Man Pages]] -->|человек| H[Оператор]
    MAN -->|агент (редко)| A[Агент]
    HELP[[Help-текст CLI]] -->|первичный источник| A
```

## Мнемоника

**«Имя, Синтаксис, Описание, Опции, Коды, Примеры»** — ИСОПКП.

## Связи

- [[Help-текст CLI]] · [[Agent-Friendly CLI Design]] · [[Shell Completions]]

## Типичные ошибки

> [!warning]
> Man page как единственный источник для агента: агент не читает troff по умолчанию.
> Для агентов первичен --help и JSON-схема.
