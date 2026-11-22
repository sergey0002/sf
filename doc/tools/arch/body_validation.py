"""Валидация тел архитектурных документов по JSON Schema для каждого типа.

Проверяет наличие обязательных разделов, таблиц и других структурных элементов
в теле Markdown документа, соответствующего своему `type` из frontmatter.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Mapping from document type to body schema file name
BODY_SCHEMA_BY_TYPE: dict[str, str] = {
    "decision": "decision.json",
    "flow": "flow.json",
    "entity": "entity.json",
    "component-view": "component-view.json",
    "rule-set": "rule-set.json",
    "glossary": "glossary.json",
    "domain": "domain.json",
    "system": "system.json",
    "capability": "capability.json",
    "capability-spec": "capability-spec.json",
    "data-view": "data-view.json",
    "quality-attributes": "quality-attributes.json",
    "security-view": "security-view.json",
    "system-context": "system-context.json",
    "constraints-risks": "constraints-risks.json",
}


def _load_body_schema(schemas_dir: Path, doc_type: str) -> dict[str, Any] | None:
    """Загрузить JSON Schema тела для заданного типа документа."""
    schema_name = BODY_SCHEMA_BY_TYPE.get(doc_type)
    if not schema_name:
        return None
    schema_path = schemas_dir / "bodies" / schema_name
    if not schema_path.exists():
        return None
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _extract_sections(body: str) -> list[str]:
    """Извлечь заголовки разделов уровня 2 из тела Markdown."""
    return re.findall(r"^##\s+(.+)$", body, flags=re.MULTILINE)


def _has_table(body: str) -> bool:
    """Проверить наличие Markdown-таблицы в теле."""
    return bool(re.search(r"^\s*\|.*\|\s*$", body, flags=re.MULTILINE))


def _has_term_format(body: str) -> bool:
    """Проверить наличие терминов в формате ### Термин — `TERM-...`."""
    return bool(re.search(r"^###\s+.+ — `TERM-[A-Za-z0-9_-]+`$", body, flags=re.MULTILINE))


def validate_document_body(
    body: str, doc_type: str, schemas_dir: Path
) -> list[str]:
    """Валидировать тело документа по схеме для его типа.

    Возвращает список сообщений об ошибках (пустой, если валидно).
    """
    errors: list[str] = []
    schema = _load_body_schema(schemas_dir, doc_type)
    if schema is None:
        # Нет схемы для этого типа — не валидируем тело
        return errors

    sections = _extract_sections(body)

    # Проверка обязательных секций
    required_sections = schema.get("required_sections", [])
    if required_sections:
        missing = [s for s in required_sections if s not in sections]
        if missing:
            errors.append(
                f"document body: missing required sections: {', '.join(missing)}"
            )

    # Проверка таблицы
    if schema.get("has_table") and not _has_table(body):
        errors.append("document body: expected a Markdown table")

    # Проверка терминов глоссария
    if schema.get("has_terms") and not _has_term_format(body):
        errors.append("document body: expected glossary terms in format ### Term — `TERM-...`")

    # Проверка колонок таблицы
    table_columns = schema.get("table_columns")
    if table_columns and _has_table(body):
        # Извлечь первую строку таблицы (заголовок)
        table_match = re.search(
            r"^\s*\|.*\|\s*$\n^\s*\|(?:\s*:?-+?:?\s*\|)+\s*$",
            body,
            flags=re.MULTILINE,
        )
        if table_match:
            header_line = table_match.group(0).split("\n")[0]
            header_cells = [c.strip() for c in header_line.strip("|").split("|")]
            for required_col in table_columns:
                if required_col not in header_cells:
                    errors.append(
                        f"document body: table missing column {required_col!r}"
                    )

    # Проверка раздела последствий (для decision)
    if doc_type == "decision" and schema.get("has_consequences"):
        if "## Последствия" not in sections:
            errors.append("document body: decision must have '## Последствия' section")

    # Проверка раздела ссылок (для decision)
    if doc_type == "decision" and schema.get("has_links"):
        if "## Ссылки" not in sections:
            errors.append("document body: decision must have '## Ссылки' section")

    # Проверка шагов (для flow)
    if doc_type == "flow" and schema.get("has_steps_table_or_list"):
        if "## Шаги" not in sections:
            errors.append("document body: flow must have '## Шаги' section")

    # Проверка инвариантов (для entity)
    if doc_type == "entity" and schema.get("has_invariants"):
        if "## Инварианты" not in sections:
            errors.append("document body: entity must have '## Инварианты' section")

    # Проверка требований (для capability-spec)
    if doc_type == "capability-spec" and schema.get("has_requirements"):
        if "## Требования" not in sections:
            errors.append("document body: capability-spec must have '## Требования' section")

    # Проверка политики формата (для data-view)
    if doc_type == "data-view" and schema.get("has_format_policy"):
        if "## Политика формата" not in sections:
            errors.append("document body: data-view must have '## Политика формата' section")

    # Проверка информационного потока (для system-context)
    if doc_type == "system-context" and schema.get("has_information_flow"):
        if "## Основной поток информации" not in sections:
            errors.append(
                "document body: system-context must have '## Основной поток информации' section"
            )

    # Проверка границы доверия (для system-context)
    if doc_type == "system-context" and schema.get("has_trust_boundary"):
        if "## Граница доверия" not in sections:
            errors.append(
                "document body: system-context must have '## Граница доверия' section"
            )

    # Проверка правила остановки (для constraints-risks)
    if doc_type == "constraints-risks" and schema.get("has_stop_rule"):
        if "## Правило остановки" not in sections:
            errors.append(
                "document body: constraints-risks must have '## Правило остановки' section"
            )

    return errors


def get_supported_body_types() -> list[str]:
    """Вернуть список типов документов, для которых есть схема тела."""
    return sorted(BODY_SCHEMA_BY_TYPE.keys())
