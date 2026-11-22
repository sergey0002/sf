"""Resolve task-type plan policy and evaluate its structural acceptance rules."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

RULE_KINDS = {"section_present", "section_min_items", "link_min", "table_column", "case_min", "command"}
LINK = re.compile(r"https?://\S+|`[^`]+`|\[[^\]]+\]\([^)]+\)")


def _read(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        return None, f"{path.as_posix()}: {exc}"
    if not isinstance(data, dict):
        return None, f"{path.as_posix()}: YAML root must be a mapping"
    return data, None


def _schema_errors(schema_path: Path, data: dict[str, Any]) -> list[str]:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errors = []
        for error in sorted(Draft202012Validator(schema).iter_errors(data), key=lambda item: list(item.path)):
            location = "/".join(str(part) for part in error.path) or "<root>"
            errors.append(f"{schema_path.name}: {location}: {error.message}")
        return errors
    except (OSError, ValueError, Exception) as exc:
        return [f"{schema_path.name}: {exc}"]


def _merge_tier(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for field, item in override.items():
        if field == "required_sections" and isinstance(item, list):
            result[field] = list(dict.fromkeys([*(result.get(field) or []), *item]))
        else:
            result[field] = item
    return result


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    if override.get("plan_policy") == "replace":
        result = dict(override)
        tiers = {}
        for name, tier in (override.get("tiers") or {}).items():
            tiers[name] = _merge_tier((base.get("tiers") or {}).get(name) or {}, tier if isinstance(tier, dict) else {})
        result["tiers"] = tiers
        return result
    result = dict(base)
    for key, value in override.items():
        if key == "tiers" and isinstance(value, dict) and isinstance(result.get(key), dict):
            tiers = dict(result[key])
            for name, tier in value.items():
                tiers[name] = _merge_tier(tiers.get(name) or {}, tier if isinstance(tier, dict) else {})
            result[key] = tiers
        elif key == "acceptance" and isinstance(value, dict) and isinstance(result.get(key), dict):
            acceptance = dict(result[key])
            acceptance.update(value)
            result[key] = acceptance
        else:
            result[key] = value
    return result


def _headings(text: str) -> list[str]:
    return [line.lstrip("#").strip() for line in text.splitlines() if line.startswith("#")]


def _section(text: str, name: str) -> str:
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if line.startswith("#") and name.casefold() in line.lstrip("#").casefold()), None)
    if start is None:
        return ""
    end = next((index for index in range(start + 1, len(lines)) if lines[index].startswith("#")), len(lines))
    return "\n".join(lines[start + 1:end])


def _when_matches(when: Any, task: dict[str, Any]) -> bool:
    """A conditional rule applies when any named task flag is truthy."""
    keys = [when] if isinstance(when, str) else when if isinstance(when, list) else []
    return any(bool(task.get(key)) for key in keys if isinstance(key, str))


def evaluate_rules(
    plan_text: str, policy: dict[str, Any], *, case_count: int = 0, task: dict[str, Any] | None = None,
) -> list[str]:
    """Return structural rule failures. Semantic oracle quality is intentionally not judged.

    A rule with ``when`` applies only if the named task flag (or any flag in the list)
    is truthy, e.g. ``when: [contract_change, storage_change]``.
    """
    rules = ((policy.get("acceptance") or {}).get("rules") or [])
    problems = []
    for rule in rules:
        if not isinstance(rule, dict) or rule.get("kind") not in RULE_KINDS:
            problems.append(f"unknown acceptance rule {rule!r}")
            continue
        if rule.get("when") is not None and not _when_matches(rule["when"], task or {}):
            continue
        kind, section = rule["kind"], str(rule.get("section") or "")
        if kind == "section_present" and not any(section.casefold() in heading.casefold() for heading in _headings(plan_text)):
            problems.append(f"plan.md: section {section!r} required by rule section_present")
        elif kind == "section_min_items":
            body = _section(plan_text, section)
            items = [line for line in body.splitlines() if re.match(r"\s*(?:[-*]|\|)\s+\S", line)]
            if len(items) < int(rule.get("min") or 1):
                problems.append(f"plan.md: section {section!r} has {len(items)} items; rule section_min_items requires {rule['min']}")
        elif kind == "link_min":
            found = len(LINK.findall(_section(plan_text, section)))
            if found < int(rule.get("min") or 1):
                problems.append(f"plan.md: section {section!r} has {found} links; rule link_min requires {rule['min']}")
        elif kind == "table_column":
            column = str(rule.get("column") or "")
            if column.casefold() not in _section(plan_text, section).casefold():
                problems.append(f"plan.md: section {section!r} lacks column {column!r} required by rule table_column")
        elif kind == "case_min" and case_count < int(rule.get("min") or 1):
            problems.append(f"verification.json: {case_count} planned cases; rule case_min requires {rule['min']}")
        elif kind == "command" and str(rule.get("command")) not in plan_text:
            problems.append(f"plan.md: command {rule['command']!r} required by rule command")
    return problems


def resolve_plan_policy(config: Any, type_id: str) -> tuple[dict[str, Any] | None, list[str]]:
    """Resolve ``type -> defaults``. A flow-level plan block is intentionally ignored."""
    defaults_path = config.task_conf_root / "plan-defaults.yaml"
    schema_path = config.schemas_root / "task-conf.schema.json"
    defaults, error = _read(defaults_path)
    if error:
        return None, [error]
    problems = _schema_errors(schema_path, defaults or {})
    type_path = config.task_conf_root / "types" / type_id / "config.yaml"
    type_data, error = _read(type_path)
    if error:
        return None, problems + [error]
    problems.extend(_schema_errors(schema_path, type_data or {}))
    policy = _merge(defaults or {}, (type_data or {}).get("plan") or {})
    policy["source"] = {"type": type_id, "defaults": defaults_path.as_posix(), "flow_ignored": True}
    policy["selectable"] = (type_data or {}).get("selectable", True)
    return policy, problems


def task_conf_integrity(config: Any, declared_types: list[str]) -> list[str]:
    """Check local task-conf consistency without scanning task cards."""
    root = config.task_conf_root / "types"
    schema = config.schemas_root / "task-conf.schema.json"
    problems = []
    selectable = []
    if not root.is_dir():
        return [f"task-conf: types directory is missing: {root.relative_to(config.root).as_posix()}"]
    for directory in sorted(path for path in root.iterdir() if path.is_dir()):
        config_path = directory / "config.yaml"
        if not config_path.is_file():
            problems.append(f"task-conf: {directory.name} has no config.yaml")
            continue
        data, error = _read(config_path)
        if error or not data or not data.get("id"):
            problems.append(error or f"task-conf: {directory.name} config has no id")
            continue
        if data["id"] != directory.name:
            problems.append(f"task-conf: id {data['id']!r} does not match directory {directory.name}")
        problems.extend(_schema_errors(schema, data))
        plan = data.get("plan") or {}
        if data.get("selectable", True):
            selectable.append(data["id"])
        for name, tier in (plan.get("tiers") or {}).items():
            if not isinstance(tier, dict):
                continue
            template = config.task_conf_root / "types" / data["id"] / str(tier.get("template") or "")
            if not template.is_file():
                problems.append(f"task-conf: {data['id']} tier {name} template is missing: {tier.get('template')}")
            allowed = set(data.get("complexity_allowed") or [])
            if allowed and not allowed <= set(tier.get("complexity") or []):
                missing = sorted(allowed - set(tier.get("complexity") or []))
                if missing and name == next(iter(plan.get("tiers") or {})):
                    pass
        covered = {item for tier in (plan.get("tiers") or {}).values() if isinstance(tier, dict) for item in tier.get("complexity") or []}
        missing = [item for item in data.get("complexity_allowed") or [] if item not in covered]
        if missing:
            problems.append(f"task-conf: {data['id']} complexity not covered by a tier: {', '.join(missing)}")
    declared = set(declared_types)
    if extra := sorted(set(selectable) - declared):
        problems.append("task-conf: selectable types missing from paths.yaml task_types: " + ", ".join(extra))
    if missing := sorted(declared - set(selectable)):
        problems.append("task-conf: paths.yaml task_types without a selectable config: " + ", ".join(missing))
    return problems
