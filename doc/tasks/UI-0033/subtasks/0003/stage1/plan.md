<!-- plan-tier: micro -->
# UI-0033-0003: документы и правила

## Изменение

- `ENT-task-input`, `REG-cli-validation-rules`, `REG-cli-command-map`, `VIEW-cli-package`: новые поля и инвариант скаффолда.
- `create-task`, `go-to-task`, `arch-cli`, `doc/AGENTS.md`, prompt `feature`: запреты и обязательный полный gate.

## Приёмка

| CASE | AC | Дано | Действие | Ожидание |
|---|---|---|---|---|
| CASE-1 | AC-1 | обновлённые документы | index build; docs check-links; validate --brief | все exit 0 |

## Проверка

```bash
arch validate --brief && arch docs check-links
```
